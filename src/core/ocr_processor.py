"""
OCR处理模块
使用 PaddleOCR 进行文字识别
"""

import os
import cv2
import logging
import fastdeploy as fd
import pyperclip
from src.utils.logging_config import setup_logging

# Initialize logger for this module
logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self, modelpath):
        """初始化OCR处理器

        Args:
            modelpath: 模型文件路径
        """
        setup_logging()
        logger.info(f"Initializing OCR processor with model path: {modelpath}")
        
        self.det_model = os.path.join(modelpath, 'ch_PP-OCRv3_det_infer')
        self.rec_model = os.path.join(modelpath, 'ch_PP-OCRv3_rec_infer')
        self.cls_model = os.path.join(modelpath, 'ch_ppocr_mobile_v2.0_cls_infer')
        self.label_file = os.path.join(modelpath, 'labels.txt')

        self.init_model()

    def init_model(self):
        """初始化模型文件路径"""
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

        # Verify model files exist
        for file_path in [self.det_model_file, self.det_params_file, 
                         self.cls_model_file, self.cls_params_file,
                         self.rec_model_file, self.rec_params_file,
                         self.rec_label_file]:
            if not os.path.exists(file_path):
                logger.error(f"Model file not found: {file_path}")
                raise FileNotFoundError(f"Model file not found: {file_path}")

    def build_option(self):
        """构建运行时选项"""
        option = fd.RuntimeOption()
        option.set_cpu_thread_num(6)
        option.use_cpu() # Use default CPU backend
        logger.info("Using default CPU backend for FastDeploy.")
        return option

    def process_image(self, image_path):
        """处理图片

        Args:
            image_path: 图片路径

        Returns:
            OCR识别结果
        """
        logger.info(f"Processing image: {image_path}")
        try:
            option = self.build_option()

            # 初始化检测模型
            det_option = option
            det_option.set_trt_input_shape("x", [1, 3, 64, 64], [1, 3, 640, 640],
                                       [1, 3, 960, 960])
            det_model = fd.vision.ocr.DBDetector(
                self.det_model_file, self.det_params_file, runtime_option=det_option)

            # 初始化分类模型
            cls_option = option
            cls_option.set_trt_input_shape("x", [1, 3, 48, 10], [10, 3, 48, 320],
                                           [64, 3, 48, 1024])
            cls_model = fd.vision.ocr.Classifier(
                self.cls_model_file, self.cls_params_file, runtime_option=cls_option)

            # 初始化识别模型
            rec_option = option
            rec_option.set_trt_input_shape("x", [1, 3, 48, 10], [10, 3, 48, 320],
                                           [64, 3, 48, 2304])
            rec_model = fd.vision.ocr.Recognizer(
                self.rec_model_file, self.rec_params_file, self.rec_label_file, runtime_option=rec_option)

            # 组合成完整的OCR系统
            ppocr_v3 = fd.vision.ocr.PPOCRv3(
                det_model=det_model, cls_model=cls_model, rec_model=rec_model)

            # 预测图片
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Failed to read image: {image_path}")

            result = ppocr_v3.predict(image)

            # 处理结果
            content = self._parse_result(result)
            self._save_to_file(image_path.replace('.png', '.txt'), content)
            pyperclip.copy(content)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            raise

    def _parse_result(self, result):
        """解析OCR结果

        Args:
            result: OCR原始结果

        Returns:
            格式化后的文本内容
        """
        content = ''
        last = 0
        for i, box in enumerate(result.boxes):
            if abs(box[1] - last) <= 5:
                t = result.text[i] + " "
            else:
                t = result.text[i] + " \n"
            last = box[1]
            content += t
        return content

    def _save_to_file(self, file_path, content):
        """保存结果到文件

        Args:
            file_path: 保存路径
            content: 文本内容
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(content))
        except Exception as e:
            logger.error(f"Error saving results to file {file_path}: {str(e)}")
            raise 