#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动视觉系统界面
"""

import sys
import os

# 获取项目路径
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(current_file)  # SickVision目录

# 添加路径到sys.path
sys.path.insert(0, project_root)  # 添加SickVision目录

# 添加Qcommon到路径中
qcommon_path = os.path.join(project_root, 'Qcommon')
rknn_path = os.path.join(project_root, 'rknn')
sys.path.insert(0, qcommon_path)
sys.path.insert(0, rknn_path)

# ======= 关键部分：创建common模块映射 =======
# 方法一：将sick.common模块映射为common模块
import sick.common
sys.modules['common'] = sick.common

# 直接导入ui模块
from ui.main_window import main

if __name__ == "__main__":
    main() 