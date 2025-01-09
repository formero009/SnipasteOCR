# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import time
from datetime import datetime
from http.client import HTTPSConnection

class TencentTranslator:
    def __init__(self, secret_id, secret_key):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.service = "tmt"
        self.host = "tmt.tencentcloudapi.com"
        self.version = "2018-03-21"
        self.region = "ap-beijing"
        self.action = "TextTranslate"
        self.algorithm = "TC3-HMAC-SHA256"

    def _sign(self, key, msg):
        return hmac.new(key.encode("utf-8") if isinstance(key, str) else key,
                       msg.encode("utf-8"), hashlib.sha256).digest()

    def translate(self, text, source_lang='en', target_lang='zh'):
        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

        # 准备请求体
        payload = json.dumps({
            "SourceText": text,
            "Source": source_lang,
            "Target": target_lang,
            "ProjectId": 0
        })

        # 构建签名所需信息
        canonical_headers = (
            f"content-type:application/json; charset=utf-8\n"
            f"host:{self.host}\n"
            f"x-tc-action:{self.action.lower()}\n"
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
            "X-TC-Action": self.action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": self.version,
            "X-TC-Region": self.region
        }

        try:
            conn = HTTPSConnection(self.host)
            conn.request("POST", "/", payload, headers)
            response = conn.getresponse()
            result = json.loads(response.read().decode())
            
            if "Response" in result and "TargetText" in result["Response"]:
                return result["Response"]["TargetText"]
            else:
                raise Exception(f"Translation failed: {result}")
        except Exception as e:
            raise Exception(f"Translation request failed: {str(e)}")
        finally:
            conn.close() 