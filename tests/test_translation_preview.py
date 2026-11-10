import os
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

from test_translator import mock_connection, request_action

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import cv2
    import numpy as np
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication, QWidget
except ImportError:
    QApplication = None
else:
    from src.ui.preview_window import PreviewWindow


@unittest.skipIf(QApplication is None, "PyQt6 and OpenCV are required for preview tests")
class TranslationPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        image_path = str(Path(directory.name) / "preview.png")
        self.assertTrue(cv2.imwrite(image_path, np.zeros((120, 280, 3), dtype=np.uint8)))
        self.parent = QWidget()
        self.parent.get_translation_settings = lambda: {
            "secret_id": "mock-id", "secret_key": "mock-key", "from_lang": "en", "to_lang": "zh",
        }
        result = SimpleNamespace(text=["Hello", "Bye"], boxes=[[20, 60], [20, 90]])
        self.preview = PreviewWindow(self.parent, image_path, result)
        self.preview.show()
        self.addCleanup(self.preview.close)

    def wait_until(self, condition):
        deadline = time.monotonic() + 3
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(5)
        self.assertTrue(condition(), "Timed out waiting for the translation worker")

    @patch("src.ui.preview_window.QMessageBox.warning")
    @patch("src.utils.translator.HTTPSConnection")
    def test_preview_displays_batched_results_and_can_toggle_to_original(self, connect, warning):
        connection, _ = mock_connection({"TargetTextList": ["你好", "再见"]})
        connect.return_value = connection
        self.preview.translate_btn.click()
        self.assertFalse(self.preview.translate_btn.isEnabled())
        self.wait_until(lambda: self.preview.translation_thread is None)
        self.assertEqual(request_action(connection), "TextTranslateBatch")
        self.assertEqual(self.preview.translated_text, ["你好", "再见"])
        self.assertTrue(self.preview.is_translated)
        self.assertTrue(self.preview.loading_label.isHidden())
        self.preview.translate_btn.click()
        self.assertFalse(self.preview.is_translated)
        warning.assert_not_called()

    @patch("src.ui.preview_window.QMessageBox.warning")
    @patch("src.utils.translator.HTTPSConnection")
    def test_api_error_restores_preview_for_retry(self, connect, warning):
        error, _ = mock_connection({"Error": {"Code": "AuthFailure.SignatureFailure"}, "RequestId": "trace"})
        success, _ = mock_connection({"TargetTextList": ["你好", "再见"]})
        connect.side_effect = [error, success]
        self.preview.translate_btn.click()
        self.wait_until(lambda: self.preview.translation_thread is None)
        self.assertTrue(self.preview.translate_btn.isEnabled())
        self.assertTrue(self.preview.loading_label.isHidden())
        self.assertIn("trace", warning.call_args.args[2])
        self.preview.translate_btn.click()
        self.wait_until(lambda: self.preview.translation_thread is None)
        self.assertEqual(self.preview.translated_text, ["你好", "再见"])

    @patch("src.ui.preview_window.QMessageBox.warning")
    @patch("src.utils.translator.HTTPSConnection")
    def test_close_returns_while_response_is_pending_and_suppresses_late_error(self, connect, warning):
        connection, response = mock_connection()
        connect.return_value = connection
        reading = Event()
        release = Event()

        def read():
            reading.set()
            release.wait(2)
            raise TimeoutError

        response.read.side_effect = read
        self.preview.translate_btn.click()
        try:
            self.wait_until(reading.is_set)
            thread = self.preview.translation_thread
            self.assertTrue(self.preview.close())
            self.assertTrue(thread.isRunning())
            self.assertTrue(thread.cancelled.is_set())
        finally:
            release.set()
        self.wait_until(lambda: self.preview.translation_thread is None)
        connect.assert_called_once()
        warning.assert_not_called()
