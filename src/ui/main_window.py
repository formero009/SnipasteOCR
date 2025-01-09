import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QCursor, QAction
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QLabel, QWidget, 
                          QMenu, QSystemTrayIcon, QFrame, QMessageBox, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QDialog, QFormLayout, QDialogButtonBox, QComboBox, QApplication)
import logging
import yaml

from src.core.ocr_thread import OCRThread
from src.ui.preview_window import PreviewWindow
from src.utils.logging_config import setup_logging

# Initialize logger for this module
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize logging
        setup_logging()
        
        # 创建中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.ocrThread = OCRThread()
        self.ocrThread.preview_signal.connect(self.show_preview)
        self.preview_window = None
        self.preview_enabled = True
        
        # 添加翻译设置
        self.translation_settings = {
            'secret_id': '',
            'secret_key': '',
            'from_lang': 'auto',
            'to_lang': 'zh'
        }
        
        self.initUI()
        self.initData()
        self.initStyle()
        self.initLayout()
        
        # 创建翻译设置菜单
        self.create_translation_settings_menu()
        
    def initUI(self):
        self.setGeometry(0, 0, 450, 300)
        self.setFixedSize(self.size())
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.setWindowIcon(QIcon('assets/icon.png'))
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
        titleAction = QAction("SnipasteOCR", self)
        titleAction.setIcon(QIcon("assets/icon.png"))
        titleAction.setEnabled(False)
        self.trayIconMenu.addAction(titleAction)
        
        self.trayIconMenu.addSeparator()
        
        # 显示/隐藏主窗口
        self.toggleWindowAction = QAction("显示主窗口", self)
        self.toggleWindowAction.setIcon(QIcon("assets/icon.png"))
        self.toggleWindowAction.triggered.connect(self.toggleWindow)
        self.trayIconMenu.addAction(self.toggleWindowAction)
        
        # 重启选项
        restartAction = QAction("重启程序", self)
        restartAction.setIcon(QIcon("assets/icon.png"))
        restartAction.triggered.connect(self.restart)
        self.trayIconMenu.addAction(restartAction)
        
        self.trayIconMenu.addSeparator()
        
        # 添加帮助菜单
        helpMenu = QMenu("帮助", self)
        helpMenu.setIcon(QIcon("assets/icon.png"))
        
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
        self.quitAction.setIcon(QIcon("assets/icon.png"))
        self.quitAction.triggered.connect(self.quit)
        self.trayIconMenu.addAction(self.quitAction)

        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setContextMenu(self.trayIconMenu)
        self.trayIcon.setIcon(QIcon("assets/icon.png"))
        self.trayIcon.activated.connect(self.iconActivated)
        self.trayIcon.setToolTip("SnipasteOCR - 截图自动识别")
        self.trayIcon.show()

    def initData(self):
        self.ocrThread.start()

    def initStyle(self):
        self.setStyleSheet("""
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
        """)

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
        logoLabel.setPixmap(QIcon("assets/icon.png").pixmap(32, 32))
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

            if self.ocrThread is not None:
                self.ocrThread.stop()
                self.ocrThread.quit()
                if not self.ocrThread.wait(1000):
                    logger.warning("OCR thread did not exit in time, forcing termination")
                    self.ocrThread.terminate()
                    self.ocrThread.wait()
            
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
        QMessageBox.about(self, "关于 SnipasteOCR",
                         """<h3>SnipasteOCR v1.0</h3>
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
        folder = QFileDialog.getExistingDirectory(self, '选择文件夹')
        if folder:
            line_edit.setText(folder)

    def loadConfig(self):
        try:
            current_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            config_path = os.path.join(current_path, 'config.yml')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.snipaste_path.setText(config['snipaste']['path'])
                self.model_path.setText(config['snipaste'].get('modelpath', os.path.join(current_path, 'models')))
                self.preview_enabled = config['snipaste'].get('preview_enabled', True)
                self.preview_button.setText(f'预览窗口：{"开启" if self.preview_enabled else "关闭"}')
                self.preview_button.setProperty("preview_off", not self.preview_enabled)
                self.preview_button.style().unpolish(self.preview_button)
                self.preview_button.style().polish(self.preview_button)
                
                # 加载翻译设置
                if 'translation' in config:
                    self.translation_settings.update({
                        'secret_id': config['translation'].get('secret_id', ''),
                        'secret_key': config['translation'].get('secret_key', ''),
                        'from_lang': config['translation'].get('from_lang', 'auto'),
                        'to_lang': config['translation'].get('to_lang', 'zh')
                    })
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

            QMessageBox.information(self, '成功', '设置已保存')
        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")
            QMessageBox.warning(self, '错误', f'保存配置文件失败: {str(e)}')

    def restart(self):
        try:
            logger.info("Restarting application")
            if self.preview_window is not None:
                self.preview_window.close()
                self.preview_window = None

            if self.ocrThread is not None:
                self.ocrThread.stop()
                self.ocrThread.quit()
                if not self.ocrThread.wait(1000):
                    logger.warning("OCR thread did not exit in time, forcing termination")
                    self.ocrThread.terminate()
                    self.ocrThread.wait()
            
            import sys
            program = sys.executable
            import subprocess
            subprocess.Popen([program] + sys.argv)
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
        layout = QFormLayout()
        
        # SecretId输入
        secret_id_input = QLineEdit(self.translation_settings['secret_id'])
        secret_id_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow('SecretId:', secret_id_input)
        
        # SecretKey输入
        secret_key_input = QLineEdit(self.translation_settings['secret_key'])
        secret_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow('SecretKey:', secret_key_input)
        
        # 源语言选择
        from_lang_input = QComboBox()
        langs = [('auto', '自动检测'), ('zh', '中文'), ('en', '英文'), ('ja', '日文'), ('ko', '韩文')]
        for code, name in langs:
            from_lang_input.addItem(name, code)
        
        # 设置当前选中的语言
        current_from_index = from_lang_input.findData(self.translation_settings['from_lang'])
        from_lang_input.setCurrentIndex(current_from_index if current_from_index >= 0 else 0)
        layout.addRow('源语言:', from_lang_input)
        
        # 目标语言选择
        to_lang_input = QComboBox()
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
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.setLayout(layout)
        
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