import os
import sys

def get_resource_path(relative_path):
    """获取资源文件的绝对路径
    
    Args:
        relative_path: 相对于项目根目录的资源文件路径
        
    Returns:
        str: 资源文件的绝对路径
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的路径
        base_path = sys._MEIPASS
    else:
        # 开发环境下的路径
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path) 