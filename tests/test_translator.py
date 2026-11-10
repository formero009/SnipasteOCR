import json
import unittest
from threading import Event
from unittest.mock import MagicMock, call, patch

from src.utils.translator import TencentTranslator, TranslationError


def mock_connection(result=None, *, status=200, body=None):
    connection = MagicMock()
    response = connection.getresponse.return_value.__enter__.return_value
    response.status = status
    response.read.return_value = body if body is not None else json.dumps({"Response": result}).encode()
    return connection, response


def request_payload(connection):
    return json.loads(connection.request.call_args.args[2])


def request_action(connection):
    return connection.request.call_args.args[3]["X-TC-Action"]


class TencentTranslatorTests(unittest.TestCase):
    def setUp(self):
        self.translator = TencentTranslator("mock-id", "mock-key")
        connection_patch = patch("src.utils.translator.HTTPSConnection")
        self.connect = connection_patch.start()
        self.addCleanup(connection_patch.stop)
        self.now = 100
        clock_patch = patch("src.utils.translator.time.monotonic", side_effect=lambda: self.now)
        clock_patch.start()
        self.addCleanup(clock_patch.stop)
        sleep_patch = patch("src.utils.translator.time.sleep", side_effect=self.advance_clock)
        self.sleep = sleep_patch.start()
        self.addCleanup(sleep_patch.stop)

    def advance_clock(self, seconds):
        self.now += seconds

    def test_single_english_and_japanese_keep_tencent_language_codes(self):
        for source, text, translated in (("en", "Hello", "你好"), ("ja", "おはよう", "早上好")):
            with self.subTest(source=source):
                connection, _ = mock_connection({"TargetText": translated})
                self.connect.return_value = connection
                self.assertEqual(self.translator.translate(text, source, "zh"), translated)
                self.connect.assert_called_with("tmt.tencentcloudapi.com", timeout=3)
                self.assertEqual(request_action(connection), "TextTranslate")
                self.assertEqual(request_payload(connection), {
                    "SourceText": text, "Source": source, "Target": "zh", "ProjectId": 0,
                })
                self.assertEqual(connection.mock_calls, [
                    call.connect(),
                    call.request("POST", "/", *connection.request.call_args.args[2:]),
                    call.sock.settimeout(8),
                    call.getresponse(),
                    call.getresponse().__enter__(),
                    call.getresponse().__enter__().read(),
                    call.getresponse().__exit__(None, None, None),
                    call.close(),
                ])

    def test_japanese_target_language(self):
        connection, _ = mock_connection({"TargetText": "こんにちは"})
        self.connect.return_value = connection
        self.assertEqual(self.translator.translate("Hello", "en", "ja"), "こんにちは")
        self.assertEqual(request_payload(connection)["Target"], "ja")

    def test_six_unique_ocr_blocks_use_one_batch_and_keep_box_alignment(self):
        unique = [f"Block {n}" for n in range(6)]
        translations = [f"文本块 {n}" for n in range(6)]
        connection, _ = mock_connection({"TargetTextList": translations})
        self.connect.return_value = connection
        texts = [unique[0], " ", *unique[1:], unique[0]]
        self.assertEqual(self.translator.translate_texts(texts, "en", "zh"),
                         [translations[0], " ", *translations[1:], translations[0]])
        self.connect.assert_called_once()
        self.assertEqual(request_action(connection), "TextTranslateBatch")
        self.assertEqual(request_payload(connection)["SourceTextList"], unique)

    def test_japanese_batches_split_at_character_limit(self):
        texts = ["あ" * 1100, "い" * 899, "う" * 900, "え" * 500]
        first, _ = mock_connection({"TargetTextList": ["甲", "乙"]})
        second, _ = mock_connection({"TargetTextList": ["丙", "丁"]})
        self.connect.side_effect = [first, second]
        self.assertEqual(self.translator.translate_texts(texts, "ja"), ["甲", "乙", "丙", "丁"])
        self.assertEqual(request_payload(first)["SourceTextList"], texts[:2])
        self.assertEqual(request_payload(second)["SourceTextList"], texts[2:])
        self.assertEqual(request_payload(second)["Source"], "ja")

    def test_auto_preserves_per_block_detection_with_deduplication_and_pacing(self):
        first, _ = mock_connection({"TargetText": "你好"})
        second, _ = mock_connection({"TargetText": "早上好"})
        self.connect.side_effect = [first, second]
        texts = ["Hello", "おはよう", "Hello", ""]
        self.assertEqual(self.translator.translate_texts(texts, "auto"), ["你好", "早上好", "你好", ""])
        self.assertEqual([request_action(conn) for conn in (first, second)], ["TextTranslate"] * 2)
        self.assertEqual([request_payload(conn)["Source"] for conn in (first, second)], ["auto"] * 2)
        self.sleep.assert_called_once_with(0.25)

    def test_six_auto_blocks_do_not_trigger_the_reported_five_per_second_limit(self):
        request_times = []

        def api_connection(*args, **kwargs):
            connection, response = mock_connection()

            def read():
                request_times.append(self.now)
                recent_calls = sum(self.now - sent_at < 1 for sent_at in request_times)
                if recent_calls > 5:
                    payload = {"Error": {"Code": "RequestLimitExceeded"}, "RequestId": "rate-limit"}
                else:
                    payload = {"TargetText": f"翻译 {len(request_times)}"}
                return json.dumps({"Response": payload}).encode()

            response.read.side_effect = read
            return connection

        self.connect.side_effect = api_connection
        self.assertEqual(
            self.translator.translate_texts([f"Block {n}" for n in range(6)], "auto"),
            [f"翻译 {n}" for n in range(1, 7)],
        )
        self.assertEqual(request_times, [100, 100.25, 100.5, 100.75, 101, 101.25])

    def test_blank_blocks_need_no_network(self):
        self.assertEqual(self.translator.translate_texts(["", " \t"]), ["", " \t"])
        self.connect.assert_not_called()

    def test_missing_batch_action_falls_back_to_single_requests(self):
        unavailable, _ = mock_connection({"Error": {"Code": "InvalidAction"}})
        first, _ = mock_connection({"TargetText": "你好"})
        second, _ = mock_connection({"TargetText": "再见"})
        self.connect.side_effect = [unavailable, first, second]
        self.assertEqual(self.translator.translate_texts(["Hello", "Bye"], "en"), ["你好", "再见"])
        self.assertEqual([request_action(conn) for conn in (unavailable, first, second)],
                         ["TextTranslateBatch", "TextTranslate", "TextTranslate"])

    def test_connect_timeout_can_recover_after_one_retry(self):
        first, _ = mock_connection()
        first.connect.side_effect = TimeoutError
        second, _ = mock_connection({"TargetText": "你好"})
        self.connect.side_effect = [first, second]
        self.assertEqual(self.translator.translate("Hello"), "你好")
        self.assertEqual(self.connect.call_count, 2)
        first.request.assert_not_called()
        first.close.assert_called_once()
        second.close.assert_called_once()
        self.sleep.assert_called_once_with(0.3)

    def test_persistent_network_timeout_reports_phase_and_stops_after_two_attempts(self):
        for phase in ("连接", "读取响应"):
            with self.subTest(phase=phase):
                self.connect.reset_mock()
                first, first_response = mock_connection()
                second, second_response = mock_connection()
                if phase == "连接":
                    first.connect.side_effect = second.connect.side_effect = TimeoutError
                else:
                    first_response.read.side_effect = second_response.read.side_effect = TimeoutError
                self.connect.side_effect = [first, second]
                with self.assertRaisesRegex(TranslationError, phase + "超时"):
                    self.translator.translate("Hello")
                self.assertEqual(self.connect.call_count, 2)
                first.close.assert_called_once()
                second.close.assert_called_once()

    def test_rate_limit_error_retries_once_and_keeps_final_request_id(self):
        first, _ = mock_connection({"Error": {"Code": "RequestLimitExceeded"}, "RequestId": "request-1"})
        second, _ = mock_connection({
            "Error": {"Code": "RequestLimitExceeded.UinLimitExceeded"}, "RequestId": "request-2",
        })
        self.connect.side_effect = [first, second]
        with self.assertRaisesRegex(TranslationError, r"请求过于频繁.*RequestLimitExceeded.*request-2"):
            self.translator.translate("Hello")
        self.assertEqual(self.connect.call_count, 2)
        self.assertIn(call(1.1), self.sleep.call_args_list)

    def test_permanent_api_errors_are_not_retried_and_expose_code_and_request_id(self):
        for code in ("AuthFailure.SignatureFailure", "FailedOperation.NoFreeAmount",
                     "UnsupportedOperation.UnsupportedSourceLanguage"):
            with self.subTest(code=code):
                self.connect.reset_mock()
                connection, _ = mock_connection({
                    "Error": {"Code": code, "Message": "mock-key Hello"}, "RequestId": "trace-1",
                })
                self.connect.return_value = connection
                with self.assertRaisesRegex(TranslationError, code + ".*trace-1") as raised:
                    self.translator.translate_texts(["Hello", "Bye"], "en")
                self.assertNotIn("mock-key", str(raised.exception))
                self.assertNotIn("Hello", str(raised.exception))
                self.connect.assert_called_once()

    def test_http_503_retries_even_with_non_json_body(self):
        first, _ = mock_connection(status=503, body=b"service unavailable")
        second, _ = mock_connection({"TargetText": "你好"})
        self.connect.side_effect = [first, second]
        self.assertEqual(self.translator.translate("Hello"), "你好")
        self.assertEqual(self.connect.call_count, 2)
        self.assertIn(call(0.3), self.sleep.call_args_list)

    def test_invalid_json_and_misaligned_batch_are_not_retried(self):
        for response, message in ((mock_connection(body=b"bad json"), "响应格式无效"),
                                  (mock_connection({"TargetTextList": ["只有一条"]}), "文本块不匹配")):
            with self.subTest(message=message):
                self.connect.reset_mock()
                self.connect.return_value = response[0]
                with self.assertRaisesRegex(TranslationError, message):
                    self.translator.translate_texts(["Hello", "Bye"], "en")
                self.connect.assert_called_once()

    def test_cancellation_after_network_failure_prevents_retry(self):
        cancelled = Event()
        connection, _ = mock_connection()

        def fail():
            cancelled.set()
            raise TimeoutError

        connection.connect.side_effect = fail
        self.connect.return_value = connection
        with self.assertRaisesRegex(TranslationError, "已取消"):
            self.translator.translate_texts(["Hello", "Bye"], "en", cancel_event=cancelled)
        self.connect.assert_called_once()
        connection.close.assert_called_once()
