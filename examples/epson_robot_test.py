#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试Epson机器人通信模块的功能
"""

import sys
import os
import time
import logging
import socket
import threading
from typing import Optional, Dict, Any, Tuple

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from epson import EpsonRobot

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EpsonRobotTest")


class MockSocket:
    """模拟socket对象用于测试"""

    def __init__(self, responses: Dict[str, str] = None):
        """初始化模拟socket"""
        self.responses = responses or {}
        self.sent_data = []
        self.timeout = 10.0
        self.closed = False
        self.default_response = "OK"
        self.last_command = None

    def sendall(self, data):
        """模拟发送数据"""
        decoded_data = data.decode('gbk')
        self.last_command = decoded_data.strip()
        self.sent_data.append(self.last_command)
        logger.info(f"Mock socket sendall: {self.last_command}")

    def recv(self, bufsize):
        """模拟接收数据"""
        if not self.last_command:
            return b""
            
        # 查找匹配的响应
        for cmd_prefix, response in self.responses.items():
            if self.last_command.startswith(cmd_prefix):
                logger.info(f"Mock socket recv: {response}")
                return response.encode('gbk')
                
        # 使用默认响应
        logger.info(f"Mock socket recv (default): {self.default_response}")
        return self.default_response.encode('gbk')

    def close(self):
        """模拟关闭socket"""
        self.closed = True
        logger.info("Mock socket closed")

    def settimeout(self, timeout):
        """模拟设置超时"""
        self.timeout = timeout
        logger.info(f"Mock socket timeout set to {timeout}")


class MockEpsonRobot(EpsonRobot):
    """模拟Epson机器人类，用于测试"""

    def __init__(self, ip: str = "192.168.10.55", port: int = 60000, status_port: int = 60001):
        """初始化模拟机器人"""
        super().__init__(ip, port, status_port)
        self.mock_cmd_socket = None
        self.mock_status_socket = None
        
        # 定义模拟响应
        self.cmd_responses = {
            "Where": "100.000 200.000 50.000 30.000",
            "Go": "OK",
            "Motor": "OK",
            "Speed": "OK",
            "Reset": "OK"
        }
        
        self.status_responses = {
            "Stat": "0",  # 0表示停止状态，1表示移动状态
            "Echo": "Echo"
        }

    def connect(self) -> bool:
        """模拟连接机器人"""
        logger.info("模拟连接到机器人...")
        
        # 创建模拟socket
        self.mock_cmd_socket = MockSocket(self.cmd_responses)
        self.mock_status_socket = MockSocket(self.status_responses)
        
        # 替换真实socket
        self.cmd_socket = self.mock_cmd_socket
        self.status_socket = self.mock_status_socket
        
        # 设置连接状态
        self.is_connected = True
        
        logger.info("模拟机器人连接成功")
        return True

    def set_robot_moving(self, is_moving: bool = True):
        """设置机器人模拟移动状态"""
        self.status_responses["Stat"] = "1" if is_moving else "0"
        logger.info(f"设置机器人移动状态为: {'移动中' if is_moving else '停止'}")


def test_epson_robot():
    """测试Epson机器人通信模块的所有方法"""
    logger.info("===== 开始测试Epson机器人通信模块 =====")
    
    # 创建模拟机器人对象
    robot = MockEpsonRobot()
    
    # 测试1: 连接机器人
    logger.info("\n测试1: 连接机器人")
    success = robot.connect()
    assert success, "连接机器人失败"
    assert robot.is_connected, "连接状态不正确"
    
    # 测试2: 发送命令并获取响应
    logger.info("\n测试2: 发送命令并获取响应")
    response = robot.send_command("Motor On", wait_for_response=True)
    assert response == "OK", f"命令响应不正确: {response}"
    
    # 测试3: 发送状态查询
    logger.info("\n测试3: 发送状态查询")
    status = robot.send_status_command("Stat", wait_for_response=True)
    assert status == "0", f"状态查询响应不正确: {status}"
    
    # 测试4: 检查移动状态
    logger.info("\n测试4: 检查移动状态")
    is_moving = robot.is_moving()
    assert not is_moving, "移动状态不正确"
    
    # 测试4.1: 改变移动状态并再次检查
    robot.set_robot_moving(True)
    is_moving = robot.is_moving()
    assert is_moving, "移动状态更改后不正确"
    
    # 测试5: 移动到指定位置
    logger.info("\n测试5: 移动到指定位置")
    move_success = robot.move_to_position("Go", 100.0, 200.0, 50.0, 30.0)
    assert move_success, "移动命令发送失败"
    
    # 测试6: 获取当前位置
    logger.info("\n测试6: 获取当前位置")
    position = robot.get_current_position()
    assert position is not None, "获取位置失败"
    assert position["x"] == 100.0, f"X坐标不正确: {position['x']}"
    assert position["y"] == 200.0, f"Y坐标不正确: {position['y']}"
    assert position["z"] == 50.0, f"Z坐标不正确: {position['z']}"
    assert position["u"] == 30.0, f"U角度不正确: {position['u']}"
    
    # 测试7: 检查连接状态
    logger.info("\n测试7: 检查连接状态")
    connected = robot.check_connection()
    assert connected, "连接状态检查不正确"
    
    # 测试8: 断开连接
    logger.info("\n测试8: 断开连接")
    robot.disconnect()
    assert not robot.is_connected, "断开连接后状态不正确"
    assert robot.cmd_socket is None, "命令socket未正确关闭"
    assert robot.status_socket is None, "状态socket未正确关闭"
    
    # 测试9: 上下文管理器用法
    logger.info("\n测试9: 上下文管理器用法")
    with MockEpsonRobot() as context_robot:
        assert context_robot.is_connected, "上下文管理器初始化连接失败"
        cmd_result = context_robot.send_command("Speed 50", wait_for_response=True)
        assert cmd_result == "OK", "上下文内命令发送失败"
    assert not context_robot.is_connected, "上下文管理器退出后未断开连接"
    
    logger.info("\n===== 所有测试通过! =====")


def test_with_real_robot(ip: str, port: int = 60000, status_port: int = 60001):
    """使用真实机器人进行测试（谨慎使用）"""
    logger.info(f"===== 开始测试真实Epson机器人 {ip}:{port}/{status_port} =====")
    
    # 创建真实机器人对象
    robot = EpsonRobot(ip, port, status_port)
    
    try:
        # 测试连接
        logger.info("尝试连接到真实机器人...")
        success = robot.connect()
        if not success:
            logger.error("连接失败，测试终止")
            return False
        
        
        logger.info("检查机器人是否在移动...")
        is_moving = robot.is_moving()
        logger.info(f"机器人{'正在移动' if is_moving else '静止中'}")
        
        # 不要执行真实移动命令，可能导致机器人移动！
        logger.info("发送移动命令...")
        robot.move_to_position("Go", 10, 10, 109, 109)
        
        logger.info("测试完成，断开连接...")
        robot.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")
        return False
    finally:
        # 确保断开连接
        if robot.is_connected:
            robot.disconnect()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试Epson机器人通信模块")
    parser.add_argument("--real", action="store_true", help="使用真实机器人进行测试")
    parser.add_argument("--ip", type=str, default="192.168.50.7", help="机器人IP地址")
    parser.add_argument("--port", type=int, default=60000, help="机器人命令端口")
    parser.add_argument("--status-port", type=int, default=60001, help="机器人状态端口")
    
    args = parser.parse_args()
    
    if args.real:
        logger.warning("!!! 警告: 将使用真实机器人进行测试 !!!")
        logger.warning("这可能导致机器人移动或状态改变")
        logger.warning(f"目标机器人: {args.ip}:{args.port}/{args.status_port}")
        
        confirmation = input("确认继续? (y/n): ")
        if confirmation.lower() != 'y':
            logger.info("测试已取消")
            return
            
        test_with_real_robot(args.ip, args.port, args.status_port)
    else:
        # 使用模拟测试
        test_epson_robot()


if __name__ == "__main__":
    main() 