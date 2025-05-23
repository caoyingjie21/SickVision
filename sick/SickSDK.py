"""
@Description :   this moudle is used to control the sick vision device and get the data.
                 The common module in the folder is required
@Author      :   Cao Yingjie
@Time        :   2025/04/23 08:47:44
"""

from common.Control import Control
from common.Streaming import Data
from common.Stream import Streaming
from common.Streaming.BlobServerConfiguration import BlobClientConfig
from Qcommon.decorators import retry, require_connection, safe_disconnect
import cv2
import numpy as np
import time
import logging
import socket

class QtVisionSick:
    """
    西克相机控制类
    用于获取相机的强度图数据
    该类获取的流默认为TCP流,如果需要UDP流,请参考sick_visionary_python_samples/visionary_StreamingDemo.py
    """
    
    def __init__(self, ipAddr="192.168.10.5", port=2122, protocol="Cola2"):
        """
        初始化西克相机
        
        Args:
            ipAddr (str): 相机IP地址
            port (int): 相机控制端口
            protocol (str): 通信协议
        """
        self.ipAddr = ipAddr
        self.control_port = port  # 控制端口
        self.streaming_port = 2114  # 数据流端口
        self.protocol = protocol
        self.deviceControl = None
        self.streaming_device = None
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        self.camera_params = None  # 存储相机参数
        self.use_single_step = True  # 默认使用单步模式
        
    def _check_camera_available(self):
        """
        检查相机是否可访问
        
        Returns:
            bool: 相机是否可访问
        """
        try:
            # 创建socket连接测试
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # 设置超时时间为2秒
            result = sock.connect_ex((self.ipAddr, self.control_port))
            sock.close()
            return result == 0
        except Exception as e:
            self.logger.error(f"Error checking camera availability: {str(e)}")
            return False
    
    @retry(max_retries=3, delay=1.0, logger_name=__name__)
    def connect(self, use_single_step=True):
        """
        连接相机并初始化流
        
        Args:
            use_single_step (bool): 是否使用单步模式
            
        Returns:
            bool: 连接是否成功
            
        Raises:
            Exception: 连接过程中的任何异常
        """
        if not self._check_camera_available():
            raise ConnectionError(f"Camera at {self.ipAddr}:{self.control_port} is not accessible")
            
        self.use_single_step = use_single_step
        
        # 创建设备控制实例
        self.deviceControl = Control(self.ipAddr, self.protocol, self.control_port)
        
        # 打开连接
        self.deviceControl.open()
        
        # 尝试登录 - 在连接时登录，保持登录状态
        try:
            self.deviceControl.login(Control.USERLEVEL_SERVICE, 'CUST_SERV')
            self.logger.info("以服务级别登录成功")
        except Exception as e:
            self.logger.warning(f"Service level login failed, trying client level: {str(e)}")
            self.deviceControl.login(Control.USERLEVEL_AUTH_CLIENT, 'CLIENT')
            self.logger.info("以客户端级别登录成功")
        
        # 获取设备信息
        name, version = self.deviceControl.getIdent()
        self.logger.info(f"Connected to device: {name.decode('utf-8')}, version: {version.decode('utf-8')}")
        
        # 尝试设置较低的帧速率以减少延迟
        try:
            # 获取当前帧周期 (微秒)
            current_frame_period = self.deviceControl.getFramePeriodUs()
            self.logger.info(f"当前帧周期: {current_frame_period} 微秒")
            
            # 设置较低的帧率 (例如 30 fps = 33333 微秒)
            self.deviceControl.setFramePeriodUs(33333)
            new_frame_period = self.deviceControl.getFramePeriodUs()
            self.logger.info(f"设置新帧周期: {new_frame_period} 微秒")
        except Exception as e:
            self.logger.warning(f"设置帧率失败: {str(e)}")
        
        # 配置流设置
        streamingSettings = BlobClientConfig()
        streamingSettings.setTransportProtocol(self.deviceControl, streamingSettings.PROTOCOL_TCP)
        streamingSettings.setBlobTcpPort(self.deviceControl, self.streaming_port)
        
        # 初始化流
        self.streaming_device = Streaming(self.ipAddr, self.streaming_port)
        self.streaming_device.openStream()
        
        # 根据模式决定流的处理方式
        if self.use_single_step:
            self.logger.info("使用单步模式，先停止流并设置为单步模式")
            # 确保流已停止
            self.deviceControl.stopStream()
        else:
            self.logger.info("使用连续流模式，启动流")
            self.deviceControl.startStream()
        
        self.is_connected = True
        self.logger.info("Successfully connected to camera")
        return True
    @require_connection
    def get_frame(self):
        """
        获取当前帧数据
        
        Returns:
            tuple: (success, depth_data, intensity_image)
                success (bool): 是否成功获取数据
                depth_data (list): 深度图数据
                intensity_image (numpy.ndarray): 强度图
        """
        # 执行单步模式下的一次获取
        if self.use_single_step:
            try:
                # 发送单步命令并获取帧
                self.deviceControl.singleStep()
                time.sleep(0.05)  # 等待相机响应
            except Exception as e:
                self.logger.warning(f"发送单步命令时出错: {str(e)}")
        
        # 获取帧数据
        return self._get_frame_data()
  
    @require_connection
    @retry(max_retries=2, delay=0.5, logger_name=__name__)        
    def get_frame_no_step(self):
        """
        Returns:
            frame: 当前帧数据
        """
        # 获取帧数据，不发送单步命令
        if not self.use_single_step:
            raise ValueError("连续流模式下不能使用get_frame_no_step")
        self.deviceControl.singleStep()
        return self._get_frame_data()
    
    def _get_frame_data(self):
        """
        内部方法：获取并处理帧数据
        
        Returns:
            tuple: (success, depth_data, intensity_image)
        """
        if self.use_single_step:
            wholeFrame = self.streaming_device.getFrame()
        else:
            wholeFrame = self.streaming_device.frame
        # 解析数据
        myData = Data.Data()
        myData.read(wholeFrame)
        if not myData.hasDepthMap:
            raise ValueError("No depth map data available")
        # 获取深度数据
        distance_data = list(myData.depthmap.distance)
        # 获取强度数据
        intensityData = list(myData.depthmap.intensity)
        numCols = myData.cameraParams.width
        numRows = myData.cameraParams.height
        # 重塑数据为图像
        image = np.array(intensityData).reshape((numRows, numCols))
        # 直接调整对比度，不进行归一化
        adjusted_image = cv2.convertScaleAbs(image, alpha=0.05, beta=1)
        # 保存相机参数
        self.camera_params = myData.cameraParams
        return True, distance_data, adjusted_image
    
    @require_connection    
    def start_continuous_mode(self):
        """
        切换到连续模式并启动流
        
        Returns:
            bool: 是否成功启动连续模式
        """
        try:
            # 确保设备处于客户端级别登录状态
            self.deviceControl.login(Control.USERLEVEL_AUTH_CLIENT, 'CLIENT')
            
            # 启动连续流
            self.deviceControl.startStream()
            self.use_single_step = False
            self.logger.info("已切换到连续流模式")
            return True
        except Exception as e:
            self.logger.error(f"启动连续模式失败: {str(e)}")
            return False
            
    @safe_disconnect  
    def disconnect(self):
        """断开相机连接并释放资源"""
        if self.is_connected:
            if self.deviceControl:
                # 先停止流
                try:
                    # 确保在停止流前先登录
                    try:
                        self.deviceControl.login(Control.USERLEVEL_AUTH_CLIENT, 'CLIENT')
                    except Exception as e:
                        self.logger.warning(f"登录设备时出错: {str(e)}")
                        
                    # 如果处于单步模式，先确保停止单步获取
                    if self.use_single_step:
                        try:
                            # 停止所有正在进行的单步操作
                            self.deviceControl.stopStream()
                            time.sleep(0.2)  # 等待相机处理命令
                            self.logger.info("单步模式已停止")
                        except Exception as e:
                            self.logger.warning(f"停止单步模式时出错: {str(e)}")
                    
                    # 停止数据流
                    self.deviceControl.stopStream()
                    time.sleep(0.2)  # 等待相机处理命令
                    self.logger.info("数据流已停止")
                except Exception as e:
                    self.logger.warning(f"停止流时出错: {str(e)}")
                    
                # 关闭流设备
                if self.streaming_device:
                    try:
                        self.streaming_device.closeStream()
                        self.logger.info("流连接已关闭")
                    except Exception as e:
                        self.logger.warning(f"关闭流连接时出错: {str(e)}")
                    
                # 登出设备
                try:
                    self.deviceControl.logout()
                    self.logger.info("设备已登出")
                except Exception as e:
                    self.logger.warning(f"登出设备时出错: {str(e)}")
                    
                # 关闭控制连接
                try:
                    self.deviceControl.close()
                    self.logger.info("控制连接已关闭")
                except Exception as e:
                    self.logger.warning(f"关闭控制连接时出错: {str(e)}")
                    
            self.is_connected = False
            self.logger.info("相机连接已完全断开")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.disconnect()
        
    def __del__(self):
        """确保在销毁时断开连接"""
        self.disconnect()

  
  

