"""
@Description :   导入助手模块，用于解决模块导入问题
@Author      :   Cao Yingjie
"""

import os
import sys
from typing import Optional

def setup_project_path(add_to_pythonpath: bool = True) -> str:
    """
    设置项目路径，以便正确导入项目模块
    
    Args:
        add_to_pythonpath (bool): 是否添加到PYTHONPATH
        
    Returns:
        str: 项目根目录路径
    """
    # 获取当前模块的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 获取项目根目录 (common的上一级目录)
    project_root = os.path.dirname(current_dir)
    
    # 获取项目的上一级目录
    parent_dir = os.path.dirname(project_root)
    
    # 将这些路径添加到sys.path
    if add_to_pythonpath:
        # 先添加项目根目录
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            
        # 再添加父目录
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
    
    return project_root

def get_module_path(module_name: Optional[str] = None) -> str:
    """
    获取指定模块或当前模块的绝对路径
    
    Args:
        module_name (str): 模块名称，如果为None则返回当前模块路径
        
    Returns:
        str: 模块路径
    """
    if module_name is None:
        # 获取调用者的帧
        import inspect
        frame = inspect.currentframe().f_back
        module = inspect.getmodule(frame)
        module_file = module.__file__
    else:
        # 尝试导入模块并获取其路径
        try:
            module = __import__(module_name)
            module_file = module.__file__
        except ImportError:
            raise ImportError(f"无法导入模块 {module_name}")
    
    return os.path.dirname(os.path.abspath(module_file)) 