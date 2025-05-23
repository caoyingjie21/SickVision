#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
展示如何使用重试装饰器的示例
"""

import sys
import os
import time
import random
import logging

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Qcommon.decorators import retry
from sick import QtVisionSick

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 示例1: 简单的重试装饰器使用
@retry(max_retries=3, delay=1.0)
def unstable_function():
    """模拟一个不稳定的函数，有75%的概率失败"""
    logger.info("尝试执行不稳定函数...")
    if random.random() < 0.75:  # 75%的概率抛出异常
        raise ConnectionError("随机连接错误!")
    logger.info("函数执行成功!")
    return "成功结果"

# 示例2: 使用自定义异常类型
@retry(max_retries=2, exceptions=(ValueError, KeyError))
def picky_function(input_dict):
    """只接受特定格式的输入"""
    if 'key1' not in input_dict:
        raise KeyError("缺少必需的key1!")
    if not isinstance(input_dict['key1'], str):
        raise ValueError("key1必须是字符串!")
    return f"处理了: {input_dict['key1']}"

# 示例3: 使用重试前回调函数
def before_retry(attempt, exception, args_dict):
    """重试前执行的回调函数"""
    logger.warning(f"准备第{attempt}次重试，上次异常: {str(exception)}")
    logger.warning(f"参数: {args_dict}")

@retry(max_retries=3, delay=2.0, on_retry=before_retry)
def function_with_callback(value):
    """演示带回调的重试函数"""
    if random.random() < 0.8:  # 80%的概率抛出异常
        raise TimeoutError(f"处理 {value} 超时!")
    return f"成功处理: {value}"

def main():
    """运行示例"""
    logger.info("===== 重试装饰器使用示例 =====")
    
    # 示例1
    logger.info("\n示例1: 简单的重试装饰器")
    try:
        result = unstable_function()
        logger.info(f"得到结果: {result}")
    except Exception as e:
        logger.error(f"最终失败: {str(e)}")
    
    # 示例2
    logger.info("\n示例2: 特定异常类型的重试")
    try:
        # 第一次调用 - 应该失败
        result = picky_function({})
    except Exception as e:
        logger.error(f"预期的失败: {str(e)}")
    
    try:
        # 第二次调用 - 应该成功
        result = picky_function({'key1': '有效值'})
        logger.info(f"得到结果: {result}")
    except Exception as e:
        logger.error(f"意外失败: {str(e)}")
    
    # 示例3
    logger.info("\n示例3: 带回调的重试")
    try:
        result = function_with_callback("测试数据")
        logger.info(f"得到结果: {result}")
    except Exception as e:
        logger.error(f"最终失败: {str(e)}")
    
    # 示例4: 实际使用相机SDK
    logger.info("\n示例4: 使用重试装饰器的相机SDK")
    # 使用无效的IP地址来模拟连接失败
    camera = QtVisionSick(ipAddr="192.168.255.255")
    success = camera.connect()
    if success:
        logger.info("相机连接成功!")
    else:
        logger.warning("相机连接失败，这在示例中是预期的行为")

if __name__ == "__main__":
    main() 