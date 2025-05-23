"""
@Description :   模块导入示例
@Author      :   Cao Yingjie
"""

import os
import sys

# 方法1：直接添加路径（简单但不够优雅）
current_file = os.path.abspath(__file__)
examples_dir = os.path.dirname(current_file)
project_root = os.path.dirname(examples_dir)
parent_dir = os.path.dirname(project_root)

# 添加路径到sys.path
sys.path.insert(0, project_root)  # 添加SickVision目录
sys.path.insert(0, parent_dir)    # 添加SickVision的父目录

# 现在可以导入SickVision模块了
from sick.SickSDK import QtVisionSick
from epson.EpsonRobot import EpsonRobot

# 创建实例
camera = QtVisionSick(ipAddr="192.168.10.5")
robot = EpsonRobot(ip="192.168.10.50")

print(f"成功导入相机模块: {camera.__class__.__name__}")
print(f"成功导入机器人模块: {robot.__class__.__name__}")

# ----------------------------------------------------

# 方法2：使用导入助手（更加优雅）
# 取消下面的注释，使用导入助手方式

"""
# 使用自定义的导入助手
import sys
import os

# 添加common目录到路径
current_file = os.path.abspath(__file__)
examples_dir = os.path.dirname(current_file)
project_root = os.path.dirname(examples_dir)
common_path = os.path.join(project_root, 'common')
sys.path.insert(0, common_path)

# 导入并使用导入助手
from import_helper import setup_project_path

# 设置项目路径
setup_project_path()

# 现在可以导入SickVision模块了
from sick.SickSDK import QtVisionSick
from epson.EpsonRobot import EpsonRobot

# 创建实例
camera = QtVisionSick(ipAddr="192.168.10.5")
robot = EpsonRobot(ip="192.168.10.50")

print(f"成功导入相机模块: {camera.__class__.__name__}")
print(f"成功导入机器人模块: {robot.__class__.__name__}")
""" 