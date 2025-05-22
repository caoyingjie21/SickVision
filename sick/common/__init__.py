# -*- coding: utf-8 -*-
"""
SDK common模块初始化文件
设置SDK组件的日志级别
"""
import logging

# 设置SDK common模块的根日志级别为WARNING
logging.getLogger('common').setLevel(logging.WARNING)
logging.getLogger('root').setLevel(logging.WARNING)
