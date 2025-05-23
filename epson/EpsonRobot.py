"""
@Description :   Epson机器人通信模块
@Author      :   Cao Yingjie
@Time        :   2025/04/23 08:47:37
"""

import socket
import time
import logging
from typing import Tuple, Optional, Dict, Any
from Qcommon.LogManager import LogManager

class EpsonRobot:
    """
    Epson机器人通信类
    用于与Epson机器人进行TCP/IP通信
    """
    
    def __init__(self, ip: str = "192.168.10.55", port: int = 60000, status_port: int = 60001):
        """
        初始化Epson机器人通信
        
        Args:
            ip (str): 机器人IP地址
            port (int): 机器人命令端口
            status_port (int): 机器人状态端口
        """
        self.ip = ip
        self.port = port
        self.status_port = status_port
        self.cmd_socket = None  # 命令通道
        self.status_socket = None  # 状态通道
        self.is_connected = False
        self.log_manager = LogManager()
        self.logger = self.log_manager.get_logger()
    
    def connect(self) -> bool:
        """
        连接机器人（同时创建命令通道和状态通道）
        
        Returns:
            bool: 连接是否成功
        """
        if self.is_connected and self.cmd_socket and self.status_socket:
            self.logger.info(f"已经连接到机器人: {self.ip}")
            return True
            
        try:
            # 关闭之前的连接（如果有）
            self._close_sockets()
                
            # 首先连接命令通道
            self.logger.info(f"尝试连接机器人命令通道: {self.ip}:{self.port}")
            print(f"连接机器人命令通道: {self.ip}:{self.port}...")
            
            self.cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.cmd_socket.settimeout(10)  # 设置超时时间为10秒
            
            # 尝试连接命令通道
            cmd_connect_result = self.cmd_socket.connect_ex((self.ip, self.port))
            
            if cmd_connect_result != 0:
                error_message = f"命令通道连接错误: {cmd_connect_result}"
                print(error_message)
                self.logger.error(error_message)
                self._close_sockets()
                return False
                
            self.logger.info(f"命令通道连接成功: {self.ip}:{self.port}")
            print(f"命令通道连接成功: {self.ip}:{self.port}")
            
            # 然后连接状态通道
            self.logger.info(f"尝试连接机器人状态通道: {self.ip}:{self.status_port}")
            print(f"连接机器人状态通道: {self.ip}:{self.status_port}...")
            
            self.status_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.status_socket.settimeout(10)  # 设置超时时间为10秒
            
            # 尝试连接状态通道
            status_connect_result = self.status_socket.connect_ex((self.ip, self.status_port))
            
            if status_connect_result != 0:
                error_message = f"状态通道连接错误: {status_connect_result}"
                print(error_message)
                self.logger.error(error_message)
                self._close_sockets()
                return False
                
            self.logger.info(f"状态通道连接成功: {self.ip}:{self.status_port}")
            print(f"状态通道连接成功: {self.ip}:{self.status_port}")
            
            # 连接成功
            self.is_connected = True
            return True
            
        except socket.timeout:
            error_message = f"连接机器人 {self.ip} 超时"
            print(error_message)
            self.logger.error(error_message)
            self._close_sockets()
            return False
        except Exception as e:
            error_message = f"连接机器人失败: {str(e)}"
            print(error_message)
            self.logger.error(error_message)
            self._close_sockets()
            return False
            
    def _close_sockets(self):
        """关闭所有socket连接"""
        # 关闭命令通道
        if self.cmd_socket:
            try:
                self.cmd_socket.close()
            except:
                pass
            self.cmd_socket = None
            
        # 关闭状态通道
        if self.status_socket:
            try:
                self.status_socket.close()
            except:
                pass
            self.status_socket = None


    def send_command(self, command: str, wait_for_response: bool = False, timeout: float = 5.0) -> Optional[str]:
        """
        通过命令通道发送命令到机器人
        
        Args:
            command (str): 要发送的命令
            wait_for_response (bool): 是否等待响应
            timeout (float): 等待响应的超时时间（秒）
            
        Returns:
            Optional[str]: 如果wait_for_response为True则返回响应，否则返回True表示发送成功
                          如果发送失败或读取响应失败，返回None
        """
        if not self.is_connected or not self.cmd_socket:
            self.logger.error("未连接到机器人命令通道")
            return None
            
        try:
            # 使用GBK编码发送命令
            self.cmd_socket.sendall((command + "\r\n").encode('gbk'))
            self.logger.info(f"发送命令: {command}")
            
            # 如果需要等待响应
            if wait_for_response:
                # 等待并读取响应
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        data = self.cmd_socket.recv(1024)
                        if data:
                            response = data.decode('gbk').strip()
                            self.logger.info(f"接收到响应: {response}")
                            return response
                    except socket.timeout:
                        # 超时但仍在总超时时间内，继续尝试
                        continue
                    except Exception as e:
                        self.logger.error(f"读取响应错误: {str(e)}")
                        return None
                
                # 如果循环结束仍未收到响应
                self.logger.error(f"等待响应超时 ({timeout}秒)")
                return None
            
            return True
            
        except Exception as e:
            self.logger.error(f"发送命令错误: {str(e)}")
            return None
            
    def send_status_command(self, command: str, wait_for_response: bool = False, timeout: float = 1.0) -> Optional[str]:
        """
        通过状态通道发送状态查询命令
        
        Args:
            command (str): 要发送的状态查询命令
            wait_for_response (bool): 是否等待响应
            timeout (float): 等待响应的超时时间（秒）
            
        Returns:
            Optional[str]: 如果wait_for_response为True则返回响应，否则返回True表示发送成功
                          如果发送失败或读取响应失败，返回None
        """
        if not self.is_connected or not self.status_socket:
            self.logger.error("未连接到机器人状态通道")
            return None
            
        try:
            # 使用GBK编码发送状态查询命令
            self.status_socket.sendall((command).encode('gbk'))
            
            # 如果需要等待响应
            if wait_for_response:
                # 等待并读取响应
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        data = self.status_socket.recv(1024)
                        if data:
                            status = data.decode('gbk').strip()
                            return status
                    except socket.timeout:
                        # 超时但仍在总超时时间内，继续尝试
                        continue
                    except Exception as e:
                        self.logger.error(f"读取状态错误: {str(e)}")
                        return None
                
                # 如果循环结束仍未收到响应
                self.logger.error(f"等待状态响应超时 ({timeout}秒)")
                return None
            
            return True
            
        except Exception as e:
            self.logger.error(f"发送状态查询错误: {str(e)}")
            return None

    def is_moving(self) -> bool:
        """
        检查机器人是否正在移动

        Returns:
            bool: 如果机器人正在移动则返回True，否则返回False
        """
        if not self.is_connected: 
            self.logger.error("未连接到机器人")
            return False
        
        # 通过状态通道查询状态
        status = self.send_status_command("Stat", wait_for_response=True, timeout=1.0)
        if status is None:
            self.logger.error("无法从机器人读取状态")
            return False

        # 解析状态数据
        if "1" in status:  # 假设1表示移动状态
            return True
        else:
            return False

    def move_to_position(self, flag: str, x: float, y: float, z: float, u: float) -> bool:
        """
        控制机器人移动到指定位置
        
        Args:
            flag (str): 移动标志，例如 "Go"
            x (float): X坐标
            y (float): Y坐标
            z (float): Z坐标
            u (float): U角度
            
        Returns:
            bool: 命令发送是否成功
        """
        if not self.is_connected or not self.cmd_socket: 
            self.logger.error("未连接到机器人命令通道")
            return False
            
        command = f"{flag} {x:.3f} {y:.3f} {z:.3f} {u:.3f}"
        result = self.send_command(command)
        return result is not None

    def get_current_position(self) -> Optional[Dict[str, float]]:
        """
        获取机器人当前位置
        
        Returns:
            Optional[Dict[str, float]]: 包含当前位置的字典，如果获取失败则返回None
        """
        if not self.is_connected:
            self.logger.error("未连接到机器人")
            return None
            
        # 发送位置查询命令
        response = self.send_command("Where", wait_for_response=True)
        if not response:
            self.logger.error("获取位置失败")
            return None
            
        # 解析位置数据
        try:
            # 假设响应格式为: "X Y Z U"
            parts = response.split()
            if len(parts) >= 4:
                return {
                    "x": float(parts[0]),
                    "y": float(parts[1]),
                    "z": float(parts[2]),
                    "u": float(parts[3])
                }
            else:
                self.logger.error(f"位置数据格式错误: {response}")
                return None
        except Exception as e:
            self.logger.error(f"解析位置数据错误: {str(e)}")
            return None

    def check_connection(self) -> bool:
        """
        检查与机器人的连接是否仍然有效
        
        Returns:
            bool: 如果连接仍然有效返回True，否则返回False
        """
        if not self.is_connected or not self.cmd_socket or not self.status_socket:
            return False
            
        try:
            # 发送一个简单的心跳命令
            result = self.send_status_command("Echo", wait_for_response=True, timeout=1.0)
            return result is not None
        except Exception as e:
            self.logger.error(f"检查连接状态时出错: {str(e)}")
            return False

    def disconnect(self):
        """断开与机器人的连接"""
        self.logger.info("开始断开机器人连接...")
        
        # 设置连接标志为False
        self.is_connected = False
        
        # 关闭socket
        self.logger.info("关闭socket通道...")
        self._close_sockets()
        
        self.logger.info("机器人已断开连接")

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.disconnect()
        return False
        
    def __del__(self):
        """
        析构函数，对象被销毁时自动调用
        确保机器人连接被正确断开，防止资源泄漏
        """
        try:
            # 检查是否仍然连接
            if hasattr(self, 'is_connected') and self.is_connected:
                # 记录日志
                if hasattr(self, 'logger'):
                    self.logger.info("对象被销毁，自动断开机器人连接")
                # 断开连接
                self.disconnect()
        except Exception as e:
            # 记录可能发生的错误
            if hasattr(self, 'logger'):
                self.logger.error(f"析构函数断开连接时出错: {str(e)}")
            # 不能在析构函数中抛出异常
            pass