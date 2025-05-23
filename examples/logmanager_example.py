"""
@Description :   LogManager使用示例
@Author      :   Cao Yingjie
@Time        :   2023/05/08 11:00:00
"""

import sys
import os
import logging

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from Qcommon.LogManager import LogManager

def basic_usage_example():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建日志管理器实例 (单例模式，多次创建返回同一实例)
    log_manager = LogManager(log_dir="log", app_name="SickVision")
    
    # 获取默认日志器
    logger = log_manager.get_logger()
    
    # 记录不同级别的日志
    logger.debug("这是一条调试日志")  # 默认不会显示，因为默认级别是INFO
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    logger.critical("这是一条严重错误日志")

def multiple_loggers_example():
    """多个日志器示例"""
    print("\n=== 多个日志器示例 ===")
    
    # 获取日志管理器实例
    log_manager = LogManager()
    
    # 创建不同模块的日志器
    camera_logger = log_manager.get_logger("Camera")
    robot_logger = log_manager.get_logger("Robot")
    vision_logger = log_manager.get_logger("Vision")
    
    # 使用不同的日志器记录日志
    camera_logger.info("相机初始化成功")
    robot_logger.warning("机器人连接超时，正在重试...")
    vision_logger.error("图像处理失败: 无法检测到目标")

def change_log_level_example():
    """修改日志级别示例"""
    print("\n=== 修改日志级别示例 ===")
    
    # 获取日志管理器实例
    log_manager = LogManager()
    
    # 获取日志器
    logger = log_manager.get_logger("Debug")
    
    # 默认INFO级别
    logger.debug("这条DEBUG日志不会显示")
    logger.info("这条INFO日志会显示")
    
    # 修改为DEBUG级别
    log_manager.set_level(logging.DEBUG, "Debug")
    logger.debug("现在这条DEBUG日志会显示了")
    
    # 修改所有日志器级别
    log_manager.set_level(logging.WARNING)
    logger.info("这条INFO日志不会显示了")
    logger.warning("这条WARNING日志会显示")

def custom_handler_example():
    """自定义处理器示例"""
    print("\n=== 自定义处理器示例 ===")
    
    # 获取日志管理器实例
    log_manager = LogManager(file_output=False)  # 初始化时不添加文件处理器
    
    # 获取日志器
    logger = log_manager.get_logger("CustomHandler")
    
    # 添加自定义文件处理器
    custom_log_file = os.path.join("log", "custom_debug.log")
    log_manager.add_file_handler("CustomHandler", custom_log_file)
    
    # 记录日志
    logger.info("这条日志会同时输出到控制台和自定义日志文件")

def singleton_pattern_example():
    """单例模式示例"""
    print("\n=== 单例模式示例 ===")
    
    # 创建两个日志管理器实例
    log_manager1 = LogManager(app_name="App1")
    log_manager2 = LogManager(app_name="App2")  # 这不会改变app_name，因为是同一个实例
    
    # 验证是否为同一个实例
    print(f"log_manager1 id: {id(log_manager1)}")
    print(f"log_manager2 id: {id(log_manager2)}")
    print(f"是否为同一实例: {log_manager1 is log_manager2}")
    
    # 获取日志器
    logger1 = log_manager1.get_logger()
    logger2 = log_manager2.get_logger()
    
    # 记录日志
    logger1.info("从实例1记录的日志")
    logger2.info("从实例2记录的日志")  # 实际上使用的是同一个日志器

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 获取日志管理器并创建UI日志器
        self.log_manager = LogManager()
        self.logger = self.log_manager.get_logger("UI")
        
        # 界面操作时记录日志
        self.logger.info("应用程序启动")
        
    def start_button_clicked(self):
        self.logger.info("开始处理按钮被点击")
        # ...

if __name__ == "__main__":
    basic_usage_example()
    multiple_loggers_example()
    change_log_level_example()
    custom_handler_example()
    singleton_pattern_example()
    
    print("\n日志文件已保存在log目录中，请查看。") 