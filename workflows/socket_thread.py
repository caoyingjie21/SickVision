from PyQt5.QtCore import pyqtSignal, QThread
import time

class RobotCommandThread(QThread):
    """机器人命令通信线程"""
    signal = pyqtSignal(str)  # 信号用于发送日志
    
    def __init__(self, robot, name):
        super().__init__()
        self.robot = robot
        self.name = name
        self.is_running = True
        
    def run(self):
        self.signal.emit(f"启动机器人{self.name}命令通信线程")
        while self.is_running:
            try:
                # 在这里实现保持命令连接的逻辑
                self.robot.keep_command_alive()
                # 避免CPU占用过高
                time.sleep(0.1)
            except Exception as e:
                self.signal.emit(f"机器人{self.name}命令通信异常: {str(e)}")
                time.sleep(1)  # 发生异常时等待一段时间再尝试
    
    def stop(self):
        self.is_running = False
        self.wait()  # 等待线程结束

# 添加机器人状态监听线程类
class RobotStatusThread(QThread):
    """机器人状态监听线程"""
    signal = pyqtSignal(str)  # 信号用于发送日志
    status_update = pyqtSignal(str, dict)  # 信号用于更新状态
    
    def __init__(self, robot, name):
        super().__init__()
        self.robot = robot
        self.name = name
        self.is_running = True
        
    def run(self):
        self.signal.emit(f"启动机器人{self.name}状态监听线程")
        while self.is_running:
            try:
                # 在这里实现状态监听的逻辑
                status = self.robot.get_status()
                if status:
                    self.status_update.emit(self.name, status)
                # 避免CPU占用过高
                time.sleep(0.2)
            except Exception as e:
                self.signal.emit(f"机器人{self.name}状态监听异常: {str(e)}")
                time.sleep(1)  # 发生异常时等待一段时间再尝试
    
    def stop(self):
        self.is_running = False
        self.wait()  # 等待线程结束
