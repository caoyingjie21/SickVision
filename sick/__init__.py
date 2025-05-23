"""
@Description :   SICK相机控制模块
@Author      :   Cao Yingjie
@Time        :   2025/05/12
"""

import sys as _sys

# ===== 映射 common =====
from . import common as _common
_sys.modules.setdefault('common', _common)

# 现在导入SickSDK（其中会用到common模块）
from .SickSDK import QtVisionSick

__all__ = ["QtVisionSick"] 