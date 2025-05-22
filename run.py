#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动视觉系统界面
"""

import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import main

if __name__ == "__main__":
    main() 