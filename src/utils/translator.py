# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from http.client import HTTPException, HTTPSConnection
from socket import EAI_AGAIN, gaierror
from ssl import SSLError


class TranslationError(RuntimeError):
    def __init__(self, message, *, retry_delay=None, api_code=None):
        super().__init__(message)
        self.retry_delay = retry_delay
        self.api_code = api_code


class TencentTranslator:
    CONNECT_TIMEOUT = 3
    READ_TIMEOUT = 8
    REQUEST_INTERVAL = 0.25
    RETRY_DELAY = 0.3
    RATE_LIMIT_DELAY = 1.1
    BATCH_CHAR_LIMIT = 1999  # 保守控制每批的源文本总字符数

    def __init__(self, secret_id, secret_key):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.service = "tmt"
        self.host = "tmt.tencentcloudapi.com"
        self.version = "2018-03-21"
        self.region = "ap-beijing"
        self.algorithm = "TC3-HMAC-SHA256"
        self._next_request_at = 0
        self._batch_available = True

    def _sign(self, key, msg):
        return hmac.new(key.encode("utf-8") if isinstance(key, str) else key,
                       msg.encode("utf-8"), hashlib.sha256).digest()

    def translate(self, text, source_lang='en', target_lang='zh'):
        return self._translate_one(text, source_lang, target_lang, None)

    def _translate_one(self, text, source_lang, target_lang, cancel_event):
        result = self._request(
            "TextTranslate", {"SourceText": text},
            source_lang, target_lang, cancel_event,
        )
        translated = result.get("TargetText")
        if not isinstance(translated, str):
            raise TranslationError("腾讯云响应缺少有效的 TargetText")
        return translated

    def translate_texts(self, texts, source_lang='en', target_lang='zh', *, cancel_event=None):
        texts = list(texts)
        unique_texts = [text for text in dict.fromkeys(texts) if text.strip()]
        translated = {}
        batch = []
        size = 0

        # 自动识别逐块进行，保留一张截图中混合语种的行为。
        limit = 0 if source_lang == 'auto' else self.BATCH_CHAR_LIMIT
        for text in unique_texts:
            if batch and size + len(text) > limit:
                translated.update(self._translate_batch(batch, source_lang, target_lang, cancel_event))
                batch = []
                size = 0
            batch.append(text)
            size += len(text)

        if batch:
            translated.update(self._translate_batch(batch, source_lang, target_lang, cancel_event))
        return [translated.get(text, text) for text in texts]

    def _translate_batch(self, batch, source_lang, target_lang, cancel_event):
        if len(batch) == 1 or not self._batch_available:
            return self._translate_individually(batch, source_lang, target_lang, cancel_event)

        try:
            result = self._request(
                "TextTranslateBatch", {"SourceTextList": batch},
                source_lang, target_lang, cancel_event,
            )
        except TranslationError as error:
            if error.api_code not in ("ActionOffline", "InvalidAction", "UnauthorizedOperation.ActionNotFound"):
                raise
            self._batch_available = False
            return self._translate_individually(batch, source_lang, target_lang, cancel_event)

        translated = result.get("TargetTextList")
        if (not isinstance(translated, list) or len(translated) != len(batch)
                or not all(isinstance(text, str) for text in translated)):
            raise TranslationError("腾讯云批量翻译响应与输入文本块不匹配")
        return dict(zip(batch, translated))

    def _translate_individually(self, texts, source_lang, target_lang, cancel_event):
        return {
            text: self._translate_one(text, source_lang, target_lang, cancel_event)
            for text in texts
        }

    @staticmethod
    def _wait(seconds, cancel_event):
        if cancel_event is not None:
            if cancel_event.wait(seconds):
                raise TranslationError("翻译已取消")
        elif seconds > 0:
            time.sleep(seconds)

    def _request(self, action, source, source_lang, target_lang, cancel_event):
        payload = json.dumps({
            **source,
            "Source": source_lang,
            "Target": target_lang,
            "ProjectId": 0,
        })
        for attempt in range(2):
            self._wait(max(0, self._next_request_at - time.monotonic()), cancel_event)
            try:
                status, body = self._post(action, payload, cancel_event)
                return self._parse_response(status, body)
            except TranslationError as error:
                if attempt or error.retry_delay is None:
                    raise
                self._wait(error.retry_delay, cancel_event)

    def _post(self, action, payload, cancel_event):
        timestamp = int(time.time())
        date = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")

        # 构建签名所需信息
        canonical_headers = (
            f"content-type:application/json; charset=utf-8\n"
            f"host:{self.host}\n"
            f"x-tc-action:{action.lower()}\n"
        )
        signed_headers = "content-type;host;x-tc-action"

        # 构建规范请求串
        canonical_request = (
            "POST\n/\n\n" +
            canonical_headers + "\n" +
            signed_headers + "\n" +
            hashlib.sha256(payload.encode("utf-8")).hexdigest()
        )

        # 构建待签名字符串
        credential_scope = f"{date}/{self.service}/tc3_request"
        string_to_sign = (
            f"{self.algorithm}\n{timestamp}\n{credential_scope}\n" +
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        )

        # 计算签名
        secret_date = self._sign(f"TC3{self.secret_key}", date)
        secret_service = self._sign(secret_date, self.service)
        secret_signing = self._sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing,
                           string_to_sign.encode("utf-8"),
                           hashlib.sha256).hexdigest()

        # 构建授权信息
        authorization = (
            f"{self.algorithm} Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        # 发送请求
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": self.host,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": self.version,
            "X-TC-Region": self.region
        }

        conn = HTTPSConnection(self.host, timeout=self.CONNECT_TIMEOUT)
        phase = "连接"
        try:
            conn.connect()
            self._wait(0, cancel_event)
            phase = "发送"
            self._next_request_at = time.monotonic() + self.REQUEST_INTERVAL
            conn.request("POST", "/", payload, headers)
            phase = "读取响应"
            conn.sock.settimeout(self.READ_TIMEOUT)
            with conn.getresponse() as response:
                return response.status, response.read()
        except TimeoutError as error:
            raise TranslationError(f"翻译服务{phase}超时", retry_delay=self.RETRY_DELAY) from error
        except gaierror as error:
            delay = self.RETRY_DELAY if error.errno == EAI_AGAIN else None
            raise TranslationError("翻译服务 DNS 解析失败", retry_delay=delay) from error
        except SSLError as error:
            raise TranslationError("翻译服务 TLS 连接失败") from error
        except ConnectionError as error:
            raise TranslationError(f"翻译服务{phase}时连接中断", retry_delay=self.RETRY_DELAY) from error
        except (OSError, HTTPException) as error:
            raise TranslationError(f"翻译服务{phase}失败（{type(error).__name__}）") from error
        finally:
            conn.close()

    def _parse_response(self, status, body):
        try:
            result = json.loads(body)
        except ValueError:
            result = None
        response = result.get("Response") if isinstance(result, dict) else None
        error = response.get("Error") if isinstance(response, dict) else None
        if isinstance(error, dict):
            code = error.get("Code", "UnknownError")
            request_id = response.get("RequestId", "未知")
            http_status = "" if 200 <= status < 300 else f"HTTP {status}，"
            rate_limited = isinstance(code, str) and code.split(".", 1)[0] == "RequestLimitExceeded"
            if rate_limited or status == 429:
                raise TranslationError(
                    f"腾讯云翻译请求过于频繁（{http_status}{code}，RequestId: {request_id}）",
                    retry_delay=self.RATE_LIMIT_DELAY,
                )
            delay = self.RETRY_DELAY if code in ("InternalError.BackendTimeout", "ServiceUnavailable") else None
            raise TranslationError(
                f"腾讯云翻译失败（{http_status}{code}，RequestId: {request_id}）",
                retry_delay=delay,
                api_code=code,
            )

        if not 200 <= status < 300:
            delay = None
            if status == 429:
                delay = self.RATE_LIMIT_DELAY
            elif status in (408, 500, 502, 503, 504):
                delay = self.RETRY_DELAY
            raise TranslationError(f"翻译服务 HTTP {status}", retry_delay=delay)
        if not isinstance(response, dict) or "Error" in response:
            raise TranslationError("腾讯云翻译响应格式无效")
        return response
