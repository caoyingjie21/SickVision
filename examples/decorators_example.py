#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
展示如何使用连接装饰器的示例
"""

import sys
import os
import time
import logging

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.decorators import require_connection, safe_disconnect, retry
from sick import QtVisionSick

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 演示用途的简化版相机类，用于展示装饰器用法
class DemoCamera:
    def __init__(self, device_id):
        self.device_id = device_id
        self.is_connected = False
        self.logger = logger
        
    @retry(max_retries=2, delay=1.0)
    def connect(self):
        """连接相机"""
        logger.info(f"连接相机 {self.device_id}...")
        # 模拟连接逻辑
        time.sleep(0.5)
        self.is_connected = True
        logger.info(f"相机 {self.device_id} 已连接")
        return True
        
    @safe_disconnect
    def disconnect(self):
        """断开相机连接"""
        logger.info(f"断开相机 {self.device_id} 连接...")
        # 模拟断开连接过程可能抛出的异常
        if self.device_id == "error_device":
            raise RuntimeError("模拟断开连接异常")
        # 模拟断开逻辑
        time.sleep(0.5)
        logger.info(f"相机 {self.device_id} 已断开连接")
        
    @require_connection
    def capture_image(self):
        """捕获图像"""
        logger.info(f"从相机 {self.device_id} 捕获图像")
        # 模拟捕获逻辑
        time.sleep(0.5)
        return f"图像数据 - 相机{self.device_id}"
        
    @require_connection
    def change_settings(self, exposure=None, gain=None):
        """修改相机设置"""
        settings = []
        if exposure is not None:
            settings.append(f"曝光: {exposure}")
        if gain is not None:
            settings.append(f"增益: {gain}")
            
        logger.info(f"相机 {self.device_id} 设置已更改: {', '.join(settings)}")
        return True


def demonstrate_decorators():
    """演示连接装饰器的使用"""
    logger.info("===== 连接状态装饰器示例 =====")
    
    # 创建示例相机
    camera = DemoCamera("cam01")
    
    # 示例1: 在连接前调用需要连接的方法
    logger.info("\n示例1: 在连接前调用方法")
    try:
        camera.capture_image()
    except Exception as e:
        logger.error(f"预期的错误: {str(e)}")
    
    # 示例2: 连接后调用方法
    logger.info("\n示例2: 连接后调用方法")
    camera.connect()
    try:
        image = camera.capture_image()
        logger.info(f"获取的数据: {image}")
        camera.change_settings(exposure=100, gain=2.0)
    except Exception as e:
        logger.error(f"意外错误: {str(e)}")
    
    # 示例3: 安全断开连接
    logger.info("\n示例3: 安全断开连接")
    camera.disconnect()
    
    # 示例4: 断开后再次调用方法
    logger.info("\n示例4: 断开后再次调用方法")
    try:
        camera.capture_image()
    except Exception as e:
        logger.error(f"预期的错误: {str(e)}")
        
    # 示例5: 测试异常断开连接
    logger.info("\n示例5: 异常断开连接")
    error_camera = DemoCamera("error_device")
    error_camera.connect()
    error_camera.disconnect()
    # 验证即使断开出错，is_connected仍被重置
    assert not error_camera.is_connected, "连接状态应该被重置为False"
    logger.info("连接状态被正确重置")


def demonstrate_sick_camera():
    """演示在实际相机SDK中使用装饰器"""
    logger.info("\n===== 使用装饰器的相机SDK示例 =====")
    
    # 创建相机实例（使用无效IP以避免真实连接）
    camera = QtVisionSick(ipAddr="192.168.255.255")
    
    # 示例1: 尝试在未连接状态下获取帧
    logger.info("\n示例1: 未连接状态下获取帧")
    try:
        camera.get_frame()
    except Exception as e:
        logger.info(f"预期的错误: {str(e)}")
    
    # 示例2: 连接并获取帧
    logger.info("\n示例2: 连接并获取帧（将失败，因为使用了无效IP）")
    try:
        camera.connect()
        camera.get_frame()
    except Exception as e:
        logger.info(f"预期的错误: {str(e)}")
    
    # 示例3: 安全断开连接
    logger.info("\n示例3: 安全断开连接")
    camera.disconnect()
    logger.info(f"连接状态: {camera.is_connected}")
    

def main():
    """运行示例"""
    demonstrate_decorators()
    demonstrate_sick_camera()

if __name__ == "__main__":
    main() 