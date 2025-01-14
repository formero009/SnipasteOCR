import os
import yaml
import logging
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from src.core.folder_monitor import FolderMonitor
from src.utils.logging_config import setup_logging

# Initialize logger for this module
logger = logging.getLogger(__name__)

class OCRThread(QThread):
    preview_signal = pyqtSignal(str, object)
    error_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        setup_logging()
        self.running = True
        
        # Load configuration
        try:
            current_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            config_path = os.path.join(current_path, 'config.yml')
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.path = config['snipaste']['path']
                self.modelpath = config['snipaste'].get('modelpath', os.path.join(current_path, 'models'))
                
                # Validate model path
                if not self.modelpath or not os.path.exists(self.modelpath):
                    error_msg = "模型路径无效或为空，请在设置中指定正确的模型路径。"
                    logger.error(error_msg)
                    self.error_signal.emit(error_msg)
                    return
                    
        except Exception as e:
            logger.error(f"Failed to load OCR configuration: {str(e)}")
            raise

    def run(self):
        logger.info("Starting OCR thread")
        try:
            self.FolderMonitor = FolderMonitor(self.path, self.modelpath)
            self.FolderMonitor.result_signal.connect(self.handle_result)
        except Exception as e:
            error_msg = f"启动OCR服务失败: {str(e)}"
            logger.error(error_msg)
            self.error_signal.emit(error_msg)
        
    def handle_result(self, image_path, result):
        if self.running:
            logging.info(f"Received result: \n\n{result}\n\n")
            self.preview_signal.emit(image_path, result)
            
    def stop(self):
        """停止OCR线程并清理资源"""
        logger.info("Stopping OCR thread")
        self.running = False
        if hasattr(self, 'FolderMonitor'):
            try:
                self.FolderMonitor.result_signal.disconnect()
            except Exception:
                pass
            self.FolderMonitor.stop()
            delattr(self, 'FolderMonitor')