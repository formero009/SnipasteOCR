# encoding: utf-8

'''
  @author: Forme
  @license: (C) Copyright 2013-2017, Node Supply Chain Manager Corporation Limited. 
  @contact: 425953474@qq.com
  @file: FolderDetect.py
  @time: 2022/11/28 10:35
  @desc:
  文件夹中有新增图片文件时，获取该文件的路径
'''


import os
import threading

import cv2
import fastdeploy as fd
import pyperclip as pyperclip
import win32con
import win32file

class FolderMonitor():
	def __init__(self, path, modelpath):
		self.path = path
		self.imageRec = ImageRecognition(modelpath)
		self.hDir = win32file.CreateFile(
			path,
			win32con.GENERIC_READ,
			win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
			None,
			win32con.OPEN_EXISTING,
			win32con.FILE_FLAG_BACKUP_SEMANTICS,
			None
		)

	def start(self):
		while True:
			results = win32file.ReadDirectoryChangesW(
				self.hDir,
				1024,
				True,
				win32con.FILE_NOTIFY_CHANGE_FILE_NAME,
				None,
				None
			)
			for action, file in results:
				full_filename = os.path.join(self.path, file).replace('\\', '/')
				if action == 1 and os.path.isfile(full_filename) and file.startswith('Snipaste') and file.endswith('.png'):
					# 检测到截图新增文件
					workThread = WorkThread(full_filename, self.imageRec)
					workThread.start()

class WorkThread(threading.Thread):
	# super
	def __init__(self, file, imageRec):
		threading.Thread.__init__(self)
		self.file = file
		self.imgRec = imageRec
		print('working thread created')

	def run(self):
		self.imgRec.textOCR(self.file)
		print('working thread destroyed')

class ImageRecognition():
	def __init__(self, modelpath):
		self.det_model = os.path.join(modelpath, 'ch_PP-OCRv3_det_infer')
		self.rec_model = os.path.join(modelpath, 'ch_PP-OCRv3_rec_infer')
		self.cls_model = os.path.join(modelpath, 'ch_ppocr_mobile_v2.0_cls_infer')
		self.label_file = os.path.join(modelpath, 'labels.txt')

		self.initModel()
		# self.textOcr = PaddleOCR(use_angle_cls=False, lang="ch", rec=True, det=True, cls=True, use_gpu=False,
		# 						 rec_model_dir='../models/ch_PP-OCRv3_rec_infer',
		# 						 det_model_dir='../models/ch_PP-OCRv3_det_infer',
		# 						 cls_model_dir='../models/ch_ppocr_mobile_v2.0_cls_infer',
		# 						 rec_batch_num=16,
		# 						 enable_mkldnn=True, cpu_threads=6,
		# 						 use_mp=True,
		# 						 total_process_num=2,
		# 						 show_log=False
		# 						 )
		print('loading models success~')

	def initModel(self):
		# Detection模型, 检测文字框
		self.det_model_file = os.path.join(self.det_model, "inference.pdmodel")
		self.det_params_file = os.path.join(self.det_model, "inference.pdiparams")
		# Classification模型，方向分类，可选
		self.cls_model_file = os.path.join(self.cls_model, "inference.pdmodel")
		self.cls_params_file = os.path.join(self.cls_model, "inference.pdiparams")
		# Recognition模型，文字识别模型
		self.rec_model_file = os.path.join(self.rec_model, "inference.pdmodel")
		self.rec_params_file = os.path.join(self.rec_model, "inference.pdiparams")
		self.rec_label_file = self.label_file

	def buildOption(self):
		option = fd.RuntimeOption()
		option.set_cpu_thread_num(6)
		option.use_openvino_backend()

		return option

	def textOCR(self, file):
		option = self.buildOption()

		det_option = option
		det_option.set_trt_input_shape("x", [1, 3, 64, 64], [1, 3, 640, 640],
								   [1, 3, 960, 960])
		det_model = fd.vision.ocr.DBDetector(
			self.det_model_file, self.det_params_file, runtime_option=det_option)

		cls_option = option
		cls_option.set_trt_input_shape("x", [1, 3, 48, 10], [10, 3, 48, 320],
									   [64, 3, 48, 1024])
		cls_model = fd.vision.ocr.Classifier(
			self.cls_model_file, self.cls_params_file, runtime_option=cls_option)

		rec_option = option
		rec_option.set_trt_input_shape("x", [1, 3, 48, 10], [10, 3, 48, 320],
									   [64, 3, 48, 2304])
		rec_model = fd.vision.ocr.Recognizer(
			self.rec_model_file, self.rec_params_file, self.rec_label_file, runtime_option=rec_option)

		ppocr_v3 = fd.vision.ocr.PPOCRv3(
			det_model=det_model, cls_model=cls_model, rec_model=rec_model)

		# 预测图片准备
		im = cv2.imread(file)

		# 预测并打印结果
		result = ppocr_v3.predict(im)
		content = self.parseResult(result)

		print('detect result：', content)
		savingFile = file.replace('.png', '.txt')
		# 保存
		self.saveToFile(savingFile, content)
		# 将内容放到剪切板中
		pyperclip.copy(content)

	def parseResult(self,result):
		#解析识别结果
		content = ''
		last = 0
		for i,box in enumerate(result.boxes):
			if abs(box[1] - last) <= 5:
				t = result.text[i] + " "
			else:
				t = result.text[i] + " \n"
			last = box[1]
			content += t
		print(content)
		return content

	def saveToFile(self, file, content):
		#将识别结果保存到文件中
		with open(file, 'w', encoding='utf-8') as f:
			f.write(str(content))

if __name__ == '__main__':
	folderMonitor = FolderMonitor('C:/Users/Forme/Pictures/saving_cut', 'E:\deep_learning\SnipasteRecognizer\models')
	folderMonitor.start()