import cv2
from PyQt6.QtCore import Qt, QRect, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QPixmap, QImage, QColor
from PyQt6.QtWidgets import QWidget, QApplication, QPushButton, QMessageBox, QLabel
from src.utils.translator import TencentTranslator

class TranslationThread(QThread):
    finished = pyqtSignal(list)  # 翻译完成信号
    error = pyqtSignal(str)      # 错误信号
    
    def __init__(self, translator, texts, source_lang, target_lang):
        super().__init__()
        self.translator = translator
        self.texts = texts
        self.source_lang = source_lang
        self.target_lang = target_lang
        
    def run(self):
        try:
            translated_texts = []
            for text in self.texts:
                translated = self.translator.translate(
                    text,
                    source_lang=self.source_lang,
                    target_lang=self.target_lang
                )
                translated_texts.append(translated)
            self.finished.emit(translated_texts)
        except Exception as e:
            self.error.emit(str(e))

class PreviewWindow(QWidget):
    def __init__(self, parent, image_path, ocr_result):
        super().__init__(parent, Qt.WindowType.Window)
        self.parent = parent
        self.image_path = image_path
        self.ocr_result = ocr_result
        self.translated_text = []  # 存储翻译后的文本
        self.is_translated = False  # 是否显示翻译
        self.translation_thread = None  # 翻译线程
        self.initUI()
        
    def initUI(self):
        # 读取图片并获取尺寸
        image = cv2.imread(self.image_path)
        height, width = image.shape[:2]
        
        # 设置窗口大小和位置
        self.setGeometry(0, 0, width, height)
        screen = QApplication.primaryScreen().geometry()
        self.move(int((screen.width() - width) / 2), int((screen.height() - height) / 2))
        
        # 转换图片为QPixmap
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, ch = image_rgb.shape
        bytes_per_line = ch * w
        image_qt = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.pixmap = QPixmap.fromImage(image_qt)
        
        # 添加翻译按钮
        self.translate_btn = QPushButton('翻译', self)
        self.translate_btn.setGeometry(10, 10, 60, 30)
        self.translate_btn.clicked.connect(self.toggle_translation)
        self.translate_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(46, 204, 113, 200);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(46, 204, 113, 255);
            }
        """)
        
        # 添加加载提示标签
        self.loading_label = QLabel('正在翻译...', self)
        self.loading_label.setGeometry(80, 10, 100, 30)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 160);
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.loading_label.hide()
        
        self.setWindowTitle('OCR预览')
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        
    def toggle_translation(self):
        if not self.translated_text and not self.translation_thread:
            self.translate_text()
        elif not self.translation_thread:  # 只在没有正在进行的翻译时切换
            self.is_translated = not self.is_translated
            self.translate_btn.setText('原文' if self.is_translated else '翻译')
            self.update()
        
    def translate_text(self):
        # 从主窗口获取翻译设置
        settings = self.parent.get_translation_settings()
        if not settings or not settings.get('secret_id') or not settings.get('secret_key'):
            QMessageBox.warning(self, '错误', '请先在设置中配置腾讯云SecretId和SecretKey')
            return
            
        # 准备待翻译的文本
        texts = self.ocr_result.text
        
        try:
            # 创建翻译器实例
            translator = TencentTranslator(settings['secret_id'], settings['secret_key'])
            
            # 创建并启动翻译线程
            self.translation_thread = TranslationThread(
                translator,
                texts,
                settings.get('from_lang', 'auto'),
                settings.get('to_lang', 'zh')
            )
            
            # 连接信号
            self.translation_thread.finished.connect(self.on_translation_finished)
            self.translation_thread.error.connect(self.on_translation_error)
            self.translation_thread.finished.connect(self.translation_thread.deleteLater)
            
            # 显示加载提示
            self.translate_btn.setEnabled(False)
            self.loading_label.show()
            
            # 启动线程
            self.translation_thread.start()
            
        except Exception as e:
            QMessageBox.warning(self, '错误', f'翻译出错: {str(e)}')
            self.translation_thread = None
            self.translate_btn.setEnabled(True)
            self.loading_label.hide()
            
    def on_translation_finished(self, translated_texts):
        self.translated_text = translated_texts
        self.is_translated = True
        self.translate_btn.setText('原文')
        self.translate_btn.setEnabled(True)
        self.loading_label.hide()
        self.translation_thread = None
        self.update()
        
    def on_translation_error(self, error_msg):
        QMessageBox.warning(self, '错误', f'翻译出错: {error_msg}')
        self.translate_btn.setEnabled(True)
        self.loading_label.hide()
        self.translation_thread = None
        
    def closeEvent(self, event):
        if self.translation_thread and self.translation_thread.isRunning():
            self.translation_thread.terminate()
            self.translation_thread.wait()
        event.accept()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # 启用抗锯齿
        painter.drawPixmap(0, 0, self.pixmap)
        
        # 设置字体
        font = QFont('Microsoft YaHei', 11)  # 使用微软雅黑字体
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        
        texts = self.translated_text if self.is_translated and self.translated_text else self.ocr_result.text
        
        for box, text in zip(self.ocr_result.boxes, texts):
            x, y = int(box[0]), int(box[1])
            
            # 计算文本区域
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(text)
            text_height = fm.height()
            padding = 4
            vertical_offset = 2  # 向下偏移量
            
            # 绘制半透明背景
            bg_rect = QRect(x - padding, y - text_height + vertical_offset,
                          text_width + padding * 2, text_height + padding * 2)
            bg_color = QColor(0, 0, 0, 160)  # 黑色背景，透明度为160
            painter.fillRect(bg_rect, bg_color)
            
            # 绘制文本边框
            border_color = QColor(46, 204, 113, 200)  # 绿色边框
            painter.setPen(border_color)
            painter.drawRect(bg_rect)
            
            # 绘制文本
            text_color = QColor(255, 255, 255)  # 白色文本
            painter.setPen(text_color)
            painter.drawText(x, y + vertical_offset * 2, text)
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close() 