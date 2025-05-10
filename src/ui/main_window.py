import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QCursor, QAction, QPalette
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QLabel, QWidget, 
                          QMenu, QSystemTrayIcon, QFrame, QMessageBox, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QDialog, QFormLayout, QDialogButtonBox, QComboBox, QApplication)
import logging
import yaml
import sys
import platform
import pathlib

from src.core.ocr_thread import OCRThread
from src.ui.preview_window import PreviewWindow
from src.utils.logging_config import setup_logging
from ..core.resource_path import get_resource_path

# Initialize logger for this module
logger = logging.getLogger(__name__)

APP_NAME = "SnipasteOCR"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize logging
        setup_logging()
        
        # 创建中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.ocrThread = None
        self.preview_window = None
        self.preview_enabled = True
        
        # 添加翻译设置
        self.translation_settings = {
            'secret_id': '',
            'secret_key': '',
            'from_lang': 'auto',
            'to_lang': 'zh'
        }
        
        # 检测系统是否为暗色模式
        self.is_dark_mode = self.check_dark_mode()
        
        self.initUI()
        self.initData()
        self.initStyle()
        self.initLayout()
        
        # 创建翻译设置菜单
        self.create_translation_settings_menu()
        
    def initUI(self):
        self.setObjectName("MainWindow")
        self.setGeometry(0, 0, 450, 300)
        self.setFixedSize(self.size())
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        # 设置窗口图标
        icon_path = get_resource_path('assets/icon.png')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle('SnipasteOCR')
        
        # 初始化到屏幕中间
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(int((screen.width() - size.width()) / 2), int((screen.height() - size.height()) / 2))
        
        self.setupMainWindow()
        self.setupTrayIcon()
        
    def create_translation_settings_menu(self):
        # 创建设置菜单
        menubar = self.menuBar()
        settings_menu = menubar.addMenu('设置')
        
        # 添加翻译设置选项
        translation_action = QAction('翻译设置', self)
        translation_action.triggered.connect(self.show_translation_settings)
        settings_menu.addAction(translation_action)

    def setupMainWindow(self):
        pass

    def setupTrayIcon(self):
        # 系统托盘
        self.trayIconMenu = QMenu(self)
        self.trayIconMenu.setObjectName("trayMenu")
        
        # 添加程序标题（不可点击）
        titleAction = QAction(APP_NAME, self)
        titleAction.setIcon(QIcon(get_resource_path('assets/icon.png')))
        titleAction.setEnabled(False)
        self.trayIconMenu.addAction(titleAction)
        
        self.trayIconMenu.addSeparator()
        
        # 显示/隐藏主窗口
        self.toggleWindowAction = QAction("显示主窗口", self)
        self.toggleWindowAction.setIcon(QIcon(get_resource_path('assets/icon.png')))
        self.toggleWindowAction.triggered.connect(self.toggleWindow)
        self.trayIconMenu.addAction(self.toggleWindowAction)
        
        # 重启选项
        restartAction = QAction("重启程序", self)
        restartAction.setIcon(QIcon(get_resource_path('assets/icon.png')))
        restartAction.triggered.connect(self.restart)
        self.trayIconMenu.addAction(restartAction)
        
        self.trayIconMenu.addSeparator()
        
        # 添加帮助菜单
        helpMenu = QMenu("帮助", self)
        helpMenu.setIcon(QIcon(get_resource_path('assets/icon.png')))
        
        aboutAction = QAction("关于", self)
        aboutAction.triggered.connect(self.showAbout)
        helpMenu.addAction(aboutAction)
        
        usageAction = QAction("使用说明", self)
        usageAction.triggered.connect(self.showUsage)
        helpMenu.addAction(usageAction)
        
        self.trayIconMenu.addMenu(helpMenu)
        
        self.trayIconMenu.addSeparator()
        
        # 退出选项
        self.quitAction = QAction("退出", self)
        self.quitAction.setIcon(QIcon(get_resource_path('assets/icon.png')))
        self.quitAction.triggered.connect(self.quit)
        self.trayIconMenu.addAction(self.quitAction)

        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setContextMenu(self.trayIconMenu)
        self.trayIcon.setIcon(QIcon(get_resource_path('assets/icon.png')))
        self.trayIcon.activated.connect(self.iconActivated)
        self.trayIcon.setToolTip(f"{APP_NAME} - 截图自动识别")
        self.trayIcon.show()

    def initData(self):
        if self.ocrThread is None or not self.ocrThread.isRunning():
            try:
                self.ocrThread = OCRThread()
                self.ocrThread.preview_signal.connect(self.show_preview)
                self.ocrThread.error_signal.connect(self.show_ocr_error)
                self.ocrThread.start()
                if hasattr(self, 'preview_button'):
                    self.preview_button.setEnabled(True)
                    self.preview_button.setToolTip('')
            except Exception as e:
                 logger.error(f"Failed to initialize or start OCR thread: {str(e)}")
                 self.show_ocr_error(f"启动OCR服务时出错: {str(e)}\n请检查配置文件和模型路径。")
                 if hasattr(self, 'preview_button'):
                     self.preview_button.setEnabled(False)
                     self.preview_button.setToolTip('OCR服务启动失败')

    def initStyle(self):
        if self.is_dark_mode:
            # 暗色模式样式
            dark_stylesheet = """
                QWidget#MainWindow {
                    background-color: #1e1e1e;
                }
                QFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                }
                QLabel {
                    background: transparent;
                    border: none;
                    color: #e0e0e0;
                    font-size: 13px;
                }
                #titleLabel {
                    color: #ffffff;
                    font-size: 20px;
                    font-weight: bold;
                    padding: 5px;
                }
                #authorLabel {
                    color: #b0b0b0;
                    font-size: 12px;
                }
                #descLabel {
                    color: #b0b0b0;
                    font-size: 12px;
                    padding: 5px;
                    line-height: 1.3;
                }
                #githubLink {
                    color: #5f85f0;
                    font-size: 12px;
                }
                #starLabel {
                    color: #ff8080;
                    font-size: 12px;
                }
                QPushButton {
                    background-color: #2d5af7;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                    min-width: 60px;
                }
                QPushButton:hover {
                    background-color: #1e4aef;
                }
                QPushButton:pressed {
                    background-color: #1a42d8;
                }
                QPushButton#previewButton {
                    background-color: #00a67d;
                }
                QPushButton#previewButton:hover {
                    background-color: #008f6c;
                }
                QPushButton#previewButton:pressed {
                    background-color: #007d5e;
                }
                QPushButton#previewButton[preview_off="true"] {
                    background-color: #666666;
                }
                QPushButton#previewButton[preview_off="true"]:hover {
                    background-color: #555555;
                }
                QPushButton#autostartButton {
                    background-color: #00a67d;
                }
                QPushButton#autostartButton:hover {
                    background-color: #008f6c;
                }
                QPushButton#autostartButton:pressed {
                    background-color: #007d5e;
                }
                QPushButton#autostartButton[autostart_off="true"] {
                    background-color: #666666;
                }
                QPushButton#autostartButton[autostart_off="true"]:hover {
                    background-color: #555555;
                }
                QLineEdit {
                    padding: 5px;
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    selection-background-color: #2d5af7;
                }
                QLineEdit:focus {
                    border: 1px solid #2d5af7;
                    background-color: #454545;
                    color: #ffffff;
                }
                QLineEdit:disabled {
                    background-color: #383838;
                    color: #a0a0a0;
                }
                QMenu {
                    background-color: #2d2d2d;
                    border: 1px solid #3a3a3a;
                    padding: 5px;
                }
                QMenu::item {
                    padding: 5px 25px 5px 20px;
                    border-radius: 3px;
                    color: #e0e0e0;
                }
                QMenu::item:selected {
                    background-color: #3a3a3a;
                    color: #5f85f0;
                }
                QMenuBar {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 4px 10px;
                }
                QMenuBar::item:selected {
                    background-color: #3a3a3a;
                    color: #5f85f0;
                }
                QComboBox {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                    padding: 5px;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 15px;
                    border-left-width: 1px;
                    border-left-color: #3a3a3a;
                    border-left-style: solid;
                }
                QComboBox QAbstractItemView {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                    selection-background-color: #3a3a3a;
                    selection-color: #5f85f0;
                }

                /* Style for QMessageBox */
                QMessageBox {
                    background-color: #2d2d2d;
                }
                QMessageBox QLabel {
                    color: #e0e0e0;
                    background-color: transparent; /* Ensure label background is transparent */
                }
                QMessageBox QPushButton {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    border: 1px solid #555555;
                    padding: 5px 15px;
                    border-radius: 4px;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #4a4a4a;
                    border: 1px solid #777777;
                }
                QMessageBox QPushButton:pressed {
                    background-color: #5a5a5a;
                }

                /* Style for QDialog */
                QDialog {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                }
                QDialog QLabel {
                    color: #e0e0e0;
                    background-color: transparent;
                }
                QDialog QLineEdit {
                    padding: 5px;
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    selection-background-color: #2d5af7;
                }
                QDialog QLineEdit:focus {
                    border: 1px solid #2d5af7;
                    background-color: #454545;
                    color: #ffffff;
                }
                QDialog QComboBox {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                    padding: 5px;
                    min-width: 6em;
                }
                QDialog QComboBox:hover {
                    border: 1px solid #2d5af7;
                }
                QDialog QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QDialog QComboBox::down-arrow {
                    width: 12px;
                    height: 12px;
                }
                QDialog QComboBox QAbstractItemView {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                    selection-background-color: #3a3a3a;
                    selection-color: #5f85f0;
                    border: 1px solid #3a3a3a;
                }
                QDialog QPushButton {
                    background-color: #2d5af7;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 4px;
                    min-width: 60px;
                }
                QDialog QPushButton:hover {
                    background-color: #1e4aef;
                }
                QDialog QPushButton:pressed {
                    background-color: #1a42d8;
                }
                QDialogButtonBox {
                    background-color: transparent;
                }
            """
            self.setStyleSheet(dark_stylesheet)
        else:
            # 亮色模式样式（原始样式）
            light_stylesheet = """
                QWidget#MainWindow {
                    background-color: #f5f5f5;
                }
                QFrame {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                }
                QLabel {
                    background: transparent;
                    border: none;
                    color: #333333;
                    font-size: 13px;
                }
                #titleLabel {
                    color: #1a1a1a;
                    font-size: 20px;
                    font-weight: bold;
                    padding: 5px;
                }
                #authorLabel {
                    color: #666666;
                    font-size: 12px;
                }
                #descLabel {
                    color: #666666;
                    font-size: 12px;
                    padding: 5px;
                    line-height: 1.3;
                }
                #githubLink {
                    color: #2d5af7;
                    font-size: 12px;
                }
                #starLabel {
                    color: #ff6b6b;
                    font-size: 12px;
                }
                QPushButton {
                    background-color: #2d5af7;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                    min-width: 60px;
                }
                QPushButton:hover {
                    background-color: #1e4aef;
                }
                QPushButton:pressed {
                    background-color: #1a42d8;
                }
                QPushButton#previewButton {
                    background-color: #00a67d;
                }
                QPushButton#previewButton:hover {
                    background-color: #008f6c;
                }
                QPushButton#previewButton:pressed {
                    background-color: #007d5e;
                }
                QPushButton#previewButton[preview_off="true"] {
                    background-color: #666666;
                }
                QPushButton#previewButton[preview_off="true"]:hover {
                    background-color: #555555;
                }
                QPushButton#autostartButton {
                    background-color: #00a67d;
                }
                QPushButton#autostartButton:hover {
                    background-color: #008f6c;
                }
                QPushButton#autostartButton:pressed {
                    background-color: #007d5e;
                }
                QPushButton#autostartButton[autostart_off="true"] {
                    background-color: #666666;
                }
                QPushButton#autostartButton[autostart_off="true"]:hover {
                    background-color: #555555;
                }
                QLineEdit {
                    padding: 5px;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    background-color: #f5f5f5;
                    color: #666666;
                    selection-background-color: #2d5af7;
                }
                QLineEdit:focus {
                    border: 1px solid #2d5af7;
                    background-color: white;
                    color: #333333;
                }
                QLineEdit:disabled {
                    background-color: #f5f5f5;
                    color: #666666;
                }
                QMenu {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    padding: 5px;
                }
                QMenu::item {
                    padding: 5px 25px 5px 20px;
                    border-radius: 3px;
                }
                QMenu::item:selected {
                    background-color: #f0f2f5;
                    color: #2d5af7;
                }
            """
            self.setStyleSheet(light_stylesheet)

    def initLayout(self):
        # 主布局
        mainLayout = QVBoxLayout(self.central_widget)
        mainLayout.setContentsMargins(10, 10, 10, 10)
        mainLayout.setSpacing(10)
        
        # 标题部分
        headerFrame = QFrame(self.central_widget)
        headerLayout = QVBoxLayout(headerFrame)
        headerLayout.setContentsMargins(10, 10, 10, 10)
        headerLayout.setSpacing(5)
        
        # Logo和标题行
        titleLayout = QHBoxLayout()
        logoLabel = QLabel()
        logoLabel.setPixmap(QIcon(get_resource_path('assets/icon.png')).pixmap(32, 32))
        titleLabel = QLabel("基于Snipaste的OCR工具")
        titleLabel.setObjectName("titleLabel")
        titleLayout.addWidget(logoLabel)
        titleLayout.addWidget(titleLabel)
        titleLayout.addStretch()
        
        # 作者和GitHub链接行
        infoLayout = QHBoxLayout()
        authorLabel = QLabel("作者: formero009")
        authorLabel.setObjectName("authorLabel")
        githubLabel = QLabel("<a href='https://github.com/formero009/SnipasteOCR' style='color: #2d5af7;'>GitHub</a>")
        githubLabel.setOpenExternalLinks(True)
        githubLabel.setObjectName("githubLink")
        starLabel = QLabel("⭐ 如果觉得有用，欢迎点个Star支持一下~")
        starLabel.setObjectName("starLabel")
        infoLayout.addWidget(authorLabel)
        infoLayout.addWidget(githubLabel)
        infoLayout.addWidget(starLabel)
        infoLayout.addStretch()
        
        # 说明文字
        descLabel = QLabel("这是一个基于Snipaste的OCR工具，可以自动识别截图中的文字。使用Snipaste截图后，程序会自动进行文字识别并复制到剪贴板。")
        descLabel.setObjectName("descLabel")
        descLabel.setWordWrap(True)
        
        headerLayout.addLayout(titleLayout)
        headerLayout.addLayout(infoLayout)
        headerLayout.addWidget(descLabel)
        
        mainLayout.addWidget(headerFrame)
        
        # 路径设置布局
        pathFrame = QFrame(self.central_widget)
        pathLayout = QVBoxLayout(pathFrame)
        pathLayout.setContentsMargins(10, 10, 10, 10)
        pathLayout.setSpacing(10)
        
        # Snipaste路径
        snipaste_layout = QHBoxLayout()
        snipaste_layout.setSpacing(5)
        snipaste_label = QLabel('截图保存路径:')
        self.snipaste_path = QLineEdit()
        self.snipaste_path.setReadOnly(True)
        self.snipaste_path.setToolTip(self.snipaste_path.text())
        snipaste_button = QPushButton('浏览')
        snipaste_button.setFixedWidth(60)
        snipaste_button.clicked.connect(lambda: self.browse_folder(self.snipaste_path))
        snipaste_layout.addWidget(snipaste_label)
        snipaste_layout.addWidget(self.snipaste_path)
        snipaste_layout.addWidget(snipaste_button)
        
        # 模型路径
        model_layout = QHBoxLayout()
        model_layout.setSpacing(5)
        model_label = QLabel('模型路径:')
        self.model_path = QLineEdit()
        self.model_path.setReadOnly(True)
        self.model_path.setToolTip(self.model_path.text())
        model_button = QPushButton('浏览')
        model_button.setFixedWidth(60)
        model_button.clicked.connect(lambda: self.browse_folder(self.model_path))
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_path)
        model_layout.addWidget(model_button)
        
        pathLayout.addLayout(snipaste_layout)
        pathLayout.addLayout(model_layout)
        
        # 按钮布局
        buttonLayout = QHBoxLayout()
        
        # 预览开关按钮
        self.preview_button = QPushButton('预览窗口：开启')
        self.preview_button.setObjectName("previewButton")
        self.preview_button.clicked.connect(self.toggle_preview)
        self.preview_button.setProperty("preview_off", not self.preview_enabled)
        buttonLayout.addWidget(self.preview_button)
        
        # 自启动开关按钮
        self.autostart_button = QPushButton('开机自启：关闭')
        self.autostart_button.setObjectName("autostartButton")
        self.autostart_button.clicked.connect(self.toggle_autostart)
        buttonLayout.addWidget(self.autostart_button)
        
        buttonLayout.addStretch()
        
        # 保存按钮
        save_button = QPushButton('保存设置')
        save_button.clicked.connect(self.saveConfig)
        buttonLayout.addWidget(save_button)
        
        pathLayout.addLayout(buttonLayout)
        mainLayout.addWidget(pathFrame)
        self.central_widget.setLayout(mainLayout)
        
        # 加载配置
        self.loadConfig()

    def closeEvent(self, event):
        if self.preview_window is not None:
            self.preview_window.close()
            self.preview_window = None
        event.ignore()
        self.hide()

    def quit(self):
        try:
            logger.info("Quitting application")
            if self.preview_window is not None:
                self.preview_window.close()
                self.preview_window = None

            if self.ocrThread is not None and self.ocrThread.isRunning():
                self.ocrThread.stop()
                self.ocrThread.quit()
                if not self.ocrThread.wait(1000):
                    logger.warning("OCR thread did not exit in time, forcing termination")
                    self.ocrThread.terminate()
                    self.ocrThread.wait()
                self.ocrThread = None
            
            QApplication.quit()
        except Exception as e:
            logger.error(f"Error during quit: {str(e)}")
            QApplication.quit()

    def editConfig(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def iconActivated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick and self.isHidden():
            self.showNormal()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick and not self.isHidden():
            self.hide()

    def show_preview(self, image_path, result):
        if self.preview_enabled:  # 只在开启预览时显示窗口
            if self.preview_window is not None:
                self.preview_window.close()
            self.preview_window = PreviewWindow(self, image_path, result)
            self.preview_window.show()

    def toggleWindow(self):
        if self.isHidden():
            self.showNormal()
            self.toggleWindowAction.setText("隐藏主窗口")
        else:
            self.hide()
            self.toggleWindowAction.setText("显示主窗口")

    def showAbout(self):
        QMessageBox.about(self, f"关于 {APP_NAME}",
                         f"""<h3>{APP_NAME} v1.0</h3>
                         <p>一个基于 PaddleOCR 的截图文字识别工具</p>
                         <p>作者: formero009</p>
                         <p>邮箱: wangchen2588@gmail.com</p>
                         <p>项目主页: <a href='https://github.com/formero009/SnipasteOCR'>GitHub</a></p>""")

    def showUsage(self):
        QMessageBox.information(self, "使用说明",
                              """<h3>使用步骤：</h3>
                              <p>1. 使用 Snipaste 进行截图</p>
                              <p>2. 程序会自动识别截图中的文字</p>
                              <p>3. 识别结果会自动复制到剪贴板</p>
                              <p>4. 同时会显示识别预览窗口</p>
                              <h3>快捷操作：</h3>
                              <p>- 双击托盘图标：显示/隐藏主窗口</p>
                              <p>- ESC键：关闭预览窗口</p>""")

    def setupSettings(self):
        # Snipaste path setting
        snipaste_layout = QHBoxLayout()
        snipaste_label = QLabel('截图保存路径:')
        self.snipaste_path = QLineEdit()
        snipaste_button = QPushButton('浏览')
        snipaste_button.clicked.connect(lambda: self.browse_folder(self.snipaste_path))
        snipaste_layout.addWidget(snipaste_label)
        snipaste_layout.addWidget(self.snipaste_path)
        snipaste_layout.addWidget(snipaste_button)

        # Model path setting
        model_layout = QHBoxLayout()
        model_label = QLabel('模型路径:')
        self.model_path = QLineEdit()
        model_button = QPushButton('浏览')
        model_button.clicked.connect(lambda: self.browse_folder(self.model_path))
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_path)
        model_layout.addWidget(model_button)

        # Add settings to main layout
        self.layout().addLayout(snipaste_layout)
        self.layout().addLayout(model_layout)

        self.loadConfig()

    def browse_folder(self, line_edit):
        start_dir = line_edit.text() if os.path.isdir(line_edit.text()) else str(pathlib.Path.home())
        folder = QFileDialog.getExistingDirectory(self, '选择文件夹', start_dir)
        if folder:
            line_edit.setText(folder)
            line_edit.setToolTip(folder)

    def loadConfig(self):
        try:
            current_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            config_path = os.path.join(current_path, 'config.yml')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if hasattr(self, 'snipaste_path'):
                    self.snipaste_path.setText(config['snipaste'].get('path', ''))
                    self.snipaste_path.setToolTip(self.snipaste_path.text())
                if hasattr(self, 'model_path'):
                    default_model_path = os.path.join(current_path, 'models')
                    modelpath_text = config['snipaste'].get('modelpath', default_model_path)
                    self.model_path.setText(modelpath_text)
                    self.model_path.setToolTip(modelpath_text)

                snipaste_config = config.get('snipaste', {})
                self.preview_enabled = snipaste_config.get('preview_enabled', True)

                if hasattr(self, 'preview_button'):
                    self.preview_button.setText(f'预览窗口：{"开启" if self.preview_enabled else "关闭"}')
                    self.preview_button.setProperty("preview_off", not self.preview_enabled)
                    self.preview_button.style().unpolish(self.preview_button)
                    self.preview_button.style().polish(self.preview_button)
                    
                if hasattr(self, 'autostart_button'):
                    self.update_autostart_button()
                
                if 'translation' in config:
                    self.translation_settings.update({
                        'secret_id': config['translation'].get('secret_id', ''),
                        'secret_key': config['translation'].get('secret_key', ''),
                        'from_lang': config['translation'].get('from_lang', 'auto'),
                        'to_lang': config['translation'].get('to_lang', 'zh')
                    })
        except FileNotFoundError:
            logger.warning(f"Configuration file not found at {config_path}. Using defaults.")
            if hasattr(self, 'snipaste_path'):
                self.snipaste_path.setText('')
                self.snipaste_path.setToolTip('')
            if hasattr(self, 'model_path'):
                 default_model_path = os.path.join(current_path, 'models')
                 self.model_path.setText(default_model_path)
                 self.model_path.setToolTip(default_model_path)
            self.preview_enabled = True
            if hasattr(self, 'preview_button'):
                 self.preview_button.setText('预览窗口：开启')
                 self.preview_button.setProperty("preview_off", False)
                 self.preview_button.style().unpolish(self.preview_button)
                 self.preview_button.style().polish(self.preview_button)
            if hasattr(self, 'autostart_button'):
                 self.update_autostart_button()
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            QMessageBox.warning(self, '错误', f'加载配置文件失败: {str(e)}')

    def saveConfig(self):
        try:
            current_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            config_path = os.path.join(current_path, 'config.yml')
            
            # 读取现有配置（如果存在）
            existing_config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f) or {}
            
            # 更新配置
            config = {
                'snipaste': {
                    'path': self.snipaste_path.text(),
                    'modelpath': self.model_path.text(),
                    'preview_enabled': self.preview_enabled
                },
                'translation': {
                    'secret_id': self.translation_settings.get('secret_id', ''),
                    'secret_key': self.translation_settings.get('secret_key', ''),
                    'from_lang': self.translation_settings.get('from_lang', 'auto'),
                    'to_lang': self.translation_settings.get('to_lang', 'zh')
                }
            }
            
            # 合并配置
            existing_config.update(config)
            
            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(existing_config, f, allow_unicode=True)

            # 重新启动OCR线程
            if self.ocrThread is not None:
                self.ocrThread.stop()
                self.ocrThread.quit()
                if not self.ocrThread.wait(1000):
                    logger.warning("OCR thread did not exit in time, forcing termination")
                    self.ocrThread.terminate()
                    self.ocrThread.wait()
            
            # 创建新的OCR线程
            self.ocrThread = OCRThread()
            self.ocrThread.preview_signal.connect(self.show_preview)
            self.ocrThread.error_signal.connect(self.show_ocr_error)
            self.ocrThread.start()

            QMessageBox.information(self, '成功', '设置已保存并重新加载OCR服务')
            
            # 重新启用预览按钮（如果之前被禁用）
            self.preview_button.setEnabled(True)
            self.preview_button.setToolTip('')
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")
            QMessageBox.warning(self, '错误', f'保存配置文件失败: {str(e)}')

    def restart(self):
        try:
            logger.info("Restarting application")
            if self.preview_window is not None:
                self.preview_window.close()
                self.preview_window = None

            if self.ocrThread is not None and self.ocrThread.isRunning():
                self.ocrThread.stop()
                self.ocrThread.quit()
                if not self.ocrThread.wait(1000):
                    logger.warning("OCR thread did not exit in time during restart, forcing termination")
                    self.ocrThread.terminate()
                    self.ocrThread.wait()
                self.ocrThread = None

            program = sys.executable
            args = sys.argv
            logger.info(f"Relaunching: {program} {args}")
            if platform.system() == "Windows" and ' ' in program:
                 program = f'"{program}"'
                 
            import subprocess
            subprocess.Popen([program] + args) 
            
            QApplication.quit()
            
        except Exception as e:
            logger.error(f"Failed to restart application: {str(e)}")
            QMessageBox.warning(self, '错误', f'重启程序失败: {str(e)}')

    def toggle_preview(self):
        self.preview_enabled = not self.preview_enabled
        self.preview_button.setText(f'预览窗口：{"开启" if self.preview_enabled else "关闭"}')
        self.preview_button.setProperty("preview_off", not self.preview_enabled)
        self.preview_button.style().unpolish(self.preview_button)
        self.preview_button.style().polish(self.preview_button)

    def show_translation_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('翻译设置')
        dialog.setMinimumSize(400, 250)  # 设置最小宽度和高度，但允许更大
        layout = QFormLayout()
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 添加腾讯云翻译API说明文字
        explanation_label = QLabel('以下设置用于腾讯云机器翻译API，<a href="https://console.cloud.tencent.com/cam/capi">点击此处</a>获取API密钥。')
        explanation_label.setOpenExternalLinks(True)
        explanation_label.setWordWrap(True)
        layout.addRow(explanation_label)
        
        # SecretId输入
        secret_id_layout = QHBoxLayout()
        secret_id_input = QLineEdit(self.translation_settings['secret_id'])
        secret_id_layout.addWidget(secret_id_input)
        layout.addRow('SecretId:', secret_id_layout)
        
        # SecretKey输入
        secret_key_layout = QHBoxLayout()
        secret_key_input = QLineEdit(self.translation_settings['secret_key'])
        secret_key_layout.addWidget(secret_key_input)
        layout.addRow('SecretKey:', secret_key_layout)
        
        # 源语言选择
        from_lang_input = QComboBox()
        from_lang_input.setFixedHeight(30)
        langs = [('auto', '自动检测'), ('zh', '中文'), ('en', '英文'), ('ja', '日文'), ('ko', '韩文')]
        for code, name in langs:
            from_lang_input.addItem(name, code)
        
        # 设置当前选中的语言
        current_from_index = from_lang_input.findData(self.translation_settings['from_lang'])
        from_lang_input.setCurrentIndex(current_from_index if current_from_index >= 0 else 0)
        layout.addRow('源语言:', from_lang_input)
        
        # 目标语言选择
        to_lang_input = QComboBox()
        to_lang_input.setFixedHeight(30)
        target_langs = langs[1:]  # 移除'auto'选项
        for code, name in target_langs:
            to_lang_input.addItem(name, code)
            
        # 设置当前选中的语言
        current_to_index = to_lang_input.findData(self.translation_settings['to_lang'])
        to_lang_input.setCurrentIndex(current_to_index if current_to_index >= 0 else 0)
        layout.addRow('目标语言:', to_lang_input)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        # 设置按钮文本为中文
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.setLayout(layout)
        
        dialog.setWindowFlags(Qt.WindowType.Dialog | 
                            Qt.WindowType.CustomizeWindowHint |
                            Qt.WindowType.WindowTitleHint |
                            Qt.WindowType.WindowCloseButtonHint)
        dialog.setModal(True)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.translation_settings.update({
                'secret_id': secret_id_input.text(),
                'secret_key': secret_key_input.text(),
                'from_lang': from_lang_input.currentData(),
                'to_lang': to_lang_input.currentData()
            })
            # 保存配置
            self.saveConfig()
            
    def get_translation_settings(self):
        return self.translation_settings.copy()

    def toggle_autostart(self):
        """切换开机自启动状态 (Cross-platform)"""
        current_os = platform.system()
        is_enabled = False
        set_successfully = False
        
        try:
            if current_os == "Windows":
                is_enabled = self._is_windows_autostart_enabled()
                self._set_windows_autostart(not is_enabled)
                set_successfully = True
            elif current_os == "Linux":
                is_enabled = self._is_linux_autostart_enabled()
                self._set_linux_autostart(not is_enabled)
                set_successfully = True
            else:
                 logger.warning(f"Autostart not supported on this platform: {current_os}")
                 QMessageBox.warning(self, '不支持', f'此操作系统 ({current_os}) 不支持开机自启动设置。')
                 return

            if set_successfully:
                self.update_autostart_button()

        except Exception as e:
            logger.error(f"Failed to toggle autostart on {current_os}: {str(e)}")
            QMessageBox.warning(self, '错误', f'设置开机自启动失败: {str(e)}')
            self.update_autostart_button()

    def update_autostart_button(self):
        """更新自启动按钮状态 (Cross-platform)"""
        current_os = platform.system()
        is_autostart = False
        supported = True

        try:
            if current_os == "Windows":
                is_autostart = self._is_windows_autostart_enabled()
            elif current_os == "Linux":
                is_autostart = self._is_linux_autostart_enabled()
            else:
                logger.info(f"Autostart checking not implemented for {current_os}")
                supported = False

            if hasattr(self, 'autostart_button'):
                 if supported:
                     self.autostart_button.setText(f'开机自启：{"开启" if is_autostart else "关闭"}')
                     self.autostart_button.setProperty("autostart_off", not is_autostart)
                     self.autostart_button.setEnabled(True)
                 else:
                     self.autostart_button.setText('开机自启：不支持')
                     self.autostart_button.setProperty("autostart_off", True)
                     self.autostart_button.setEnabled(False)
                 
                 self.autostart_button.style().unpolish(self.autostart_button)
                 self.autostart_button.style().polish(self.autostart_button)
                 
        except Exception as e:
             logger.error(f"Failed to update autostart button state on {current_os}: {str(e)}")
             if hasattr(self, 'autostart_button'):
                 self.autostart_button.setText('开机自启：错误')
                 self.autostart_button.setEnabled(False)

    def show_ocr_error(self, error_msg):
        """显示OCR错误消息"""
        QMessageBox.warning(self, '错误', error_msg)
        if hasattr(self, 'preview_button'):
            self.preview_button.setEnabled(False)
            self.preview_button.setToolTip('OCR服务未正常启动') 

    def check_dark_mode(self):
        """检测系统是否处于暗色模式 (Cross-Platform)"""
        current_os = platform.system()
        
        if current_os == "Windows":
             return self._check_windows_dark_mode()
        elif current_os == "Linux":
            try:
                window_color = self.palette().color(QPalette.ColorRole.Window)
                text_color = self.palette().color(QPalette.ColorRole.WindowText)
                is_dark = window_color.lightness() < text_color.lightness() or window_color.lightness() < 100
                logger.debug(f"Linux dark mode check: Window lightness={window_color.lightness()}, Text lightness={text_color.lightness()}. Detected dark: {is_dark}")
                return is_dark
            except Exception as e:
                logger.error(f"Failed to check Linux dark mode via Qt Palette: {str(e)}")
                return False
        else:
            logger.info(f"Dark mode detection not implemented for OS: {current_os}. Assuming light mode.")
            return False

    def _check_windows_dark_mode(self):
        """检测Windows系统是否处于暗色模式 (Windows Specific)"""
        import winreg
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, regtype = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            logger.debug(f"Windows AppsUseLightTheme registry value: {value}")
            return value == 0
        except FileNotFoundError:
             logger.warning("Windows dark mode registry key 'AppsUseLightTheme' not found. Assuming light mode.")
             return False
        except Exception as e:
            logger.error(f"Failed to check Windows dark mode via registry: {str(e)}")
            return False

    def _get_executable_path(self):
        """Gets the absolute path to the executable."""
        if getattr(sys, 'frozen', False):
            # Running as a bundled app (PyInstaller)
             path = sys.executable
        else:
            # Running as a script
             path = os.path.abspath(sys.argv[0])
             # If running via 'python -m src.main', argv[0] might be '-m'
             if sys.argv[0] == '-m': 
                 # Attempt to find the main script file path
                 import inspect
                 frame = inspect.currentframe()
                 while frame.f_back:
                     frame = frame.f_back
                     module_name = frame.f_globals.get('__name__')
                     if module_name == '__main__':
                         path = os.path.abspath(frame.f_code.co_filename)
                         break
                 else: # Fallback if __main__ not found in call stack
                      path = os.path.abspath(os.getcwd()) # Less ideal, but a fallback
             elif not os.path.isabs(path):
                  # Handle relative paths if not running with -m
                  path = os.path.abspath(os.path.join(os.getcwd(), path))

        # On Windows, ensure path is quoted if it contains spaces for registry/desktop files
        if platform.system() == "Windows" and ' ' in path:
              return f'"{path}"'
        return path

    def _get_windows_registry_key(self, access):
        import winreg
        try:
            return winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, access)
        except OSError as e:
            logger.error(f"Failed to open registry key: {e}")
            return None

    def _is_windows_autostart_enabled(self):
        import winreg
        key = self._get_windows_registry_key(winreg.KEY_READ)
        if not key:
            return False
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
        except OSError as e:
            logger.error(f"Error checking Windows autostart registry value: {e}")
            if key: winreg.CloseKey(key)
            return False

    def _set_windows_autostart(self, enabled: bool):
        import winreg
        key = self._get_windows_registry_key(winreg.KEY_ALL_ACCESS)
        if not key:
            raise OSError("Could not open registry key for writing.")
        
        app_path = self._get_executable_path()
        try:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, app_path)
                logger.info(f"Enabled Windows autostart: {APP_NAME} -> {app_path}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info(f"Disabled Windows autostart: {APP_NAME}")
                except FileNotFoundError:
                    logger.info(f"Windows autostart entry not found for {APP_NAME}, nothing to disable.")
            winreg.CloseKey(key)
            return True
        except OSError as e:
            logger.error(f"Failed to set Windows autostart: {e}")
            if key: winreg.CloseKey(key)
            raise

    def _get_linux_autostart_path(self):
        autostart_dir = pathlib.Path.home() / ".config" / "autostart"
        return autostart_dir / f"{APP_NAME}.desktop"

    def _is_linux_autostart_enabled(self):
        return self._get_linux_autostart_path().exists()

    def _set_linux_autostart(self, enabled: bool):
        desktop_file_path = self._get_linux_autostart_path()
        autostart_dir = desktop_file_path.parent

        try:
            if enabled:
                autostart_dir.mkdir(parents=True, exist_ok=True)
                
                exec_path = self._get_executable_path()
                icon_path = os.path.abspath(get_resource_path('assets/icon.png'))
                
                desktop_content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Exec={exec_path}
Icon={icon_path}
Comment=Snipaste OCR Tool based on PaddleOCR
Terminal=false
X-GNOME-Autostart-enabled=true
"""
                desktop_file_path.write_text(desktop_content, encoding='utf-8')
                logger.info(f"Enabled Linux autostart: Created {desktop_file_path}")
            else:
                if desktop_file_path.exists():
                    desktop_file_path.unlink()
                    logger.info(f"Disabled Linux autostart: Removed {desktop_file_path}")
                else:
                     logger.info(f"Linux autostart file not found for {APP_NAME}, nothing to disable.")
            return True
        except (OSError, PermissionError, Exception) as e:
            logger.error(f"Failed to set Linux autostart: {e}")
            raise