# encoding: utf-8

'''
  @author: Forme
  @contact: 425953474@qq.com
  @file: mainWindow.py
  @time: 2022/11/29 9:59
  @desc:
主窗口
'''
import _thread
import os
import sys

import yaml
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QLabel, QWidget, QDesktopWidget, QMenu, QAction, QSystemTrayIcon

from FolderDetect import FolderMonitor


class MainWindow(QWidget):
	def __init__(self):
		super(MainWindow, self).__init__()
		self.ocrThread = OCRThread()
		self.initUI()
		self.initData()
		self.initStyle()
		self.initLayout()

	def initUI(self):
		self.setGeometry(0, 0, 300, 100)
		self.setFixedSize(self.size())
		self.setCursor(QCursor(Qt.PointingHandCursor))
		self.setWindowIcon(QIcon('icon.png'))
		self.setWindowTitle('SnipasteOCR')
		# 初始化到屏幕中间
		screen = QDesktopWidget().screenGeometry()
		size = self.geometry()
		screen = QDesktopWidget().screenGeometry()
		self.move(int((screen.width() - size.width()) / 2), int((screen.height() - size.height()) / 2))
		# self.setWindowFlags(Qt.WindowStaysOnTopHint)

		self.label = QLabel()
		self.label.setText('程序运行中...')
		self.label.setAlignment(Qt.AlignCenter)
		self.label.setScaledContents(True)

		self.trayIconMenu = QMenu(self)
		self.settingAction = QAction("设置", self)
		self.settingAction.triggered.connect(self.editConfig)
		self.trayIconMenu.addAction(self.settingAction)
		self.quitAction = QAction("退出", self)
		self.quitAction.triggered.connect(self.quit)
		self.trayIconMenu.addAction(self.quitAction)

		self.trayIcon = QSystemTrayIcon(self)
		self.trayIcon.setContextMenu(self.trayIconMenu)
		self.trayIcon.setIcon(QIcon("icon.png"))
		self.trayIcon.activated.connect(self.iconActivated)
		self.trayIcon.setToolTip("通过Snipaste截图后自动识别")
		self.trayIcon.show()

	def initData(self):
		self.ocrThread.start()

	def initStyle(self):
		self.setStyleSheet(
			"QLabel{font-size:14px;font-weight:bold;font-family:Roman times;background:white; background-color:rgba(255,255,255,0.4);}")
		self.trayIconMenu.setStyleSheet(
			"QMenu{font-size:14px;font-weight:bold;font-family:Roman times;}")
		self.setWindowOpacity(0.8)

	def closeEvent(self, event):
		event.ignore()
		self.hide()

	def showMinimized(self, event):
		event.ignore()
		self.hide()

	def initLayout(self):
		mainLayout = QVBoxLayout()
		mainLayout.addWidget(self.label)
		self.setLayout(mainLayout)

	def quit(self):
		exit(0)

	def open_config(self):
		os.system('notepad config.yml')

	def editConfig(self):
		# 创建两个线程
		try:
			_thread.start_new_thread(self.open_config, ())
		except:
			print("Error: open config file failed")

	def iconActivated(self, reason):
		if reason == QSystemTrayIcon.DoubleClick and self.isHidden():
			self.showNormal()
		elif reason == QSystemTrayIcon.DoubleClick and not self.isHidden():
			self.hide()

class OCRThread(QThread):
	def __init__(self):
		super().__init__()
		# 读取yml文件
		current_path = os.path.abspath(os.path.dirname(__file__))
		with open(current_path + '/config.yml', 'r') as f:
			temp = yaml.load(f.read(), Loader=yaml.CLoader)
			self.path = temp['snipaste']['path']
			self.modelpath = temp['snipaste']['modelpath'] if 'modelpath' in temp['snipaste'] else os.path.join(current_path, 'models')

	def run(self):
		self.FolderMonitor = FolderMonitor(self.path, self.modelpath)
		self.FolderMonitor.start()

if __name__ == '__main__':
	app = QApplication(sys.argv)
	mainWindow = MainWindow()
	mainWindow.show()
	sys.exit(app.exec_())