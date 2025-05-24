from PyQt5.QtCore import QObject, pyqtSignal
from sick.SickSDK import QtVisionSick
from epson.EpsonRobot import EpsonRobot
from rknn.RknnYolo import RKNN_YOLO
from Qcommon.decorators import catch_and_log

class SystemLoader(QObject):
    progress = pyqtSignal(str, str)
    finished = pyqtSignal(object, dict, object)
    error    = pyqtSignal(str)

    def __init__(self, camera_cfg, robots_cfg, model_path):
        super().__init__()
        self.camera_cfg = camera_cfg
        self.robots_cfg = robots_cfg
        self.model_path = model_path

    @catch_and_log()
    def run(self):
        try:
            # 1. 相机
            self.progress.emit("连接相机…", "info")
            cam_svc = QtVisionSick(**self.camera_cfg)
            if not cam_svc.connect(use_single_step=False):
                raise RuntimeError("相机连接失败")

            # 2. 机器人
            robots = {}
            for cfg in self.robots_cfg:
                self.progress.emit(f"连接机器人 {cfg['name']}…", "info")
                bot_svc = EpsonRobot(cfg["ip"], cfg["cmd_port"], cfg["status_port"])
                if bot_svc.connect():
                    robots[cfg["name"]] = bot_svc
                    self.progress.emit(f"{cfg['name']} 连接成功", "info")
                else:
                    self.progress.emit(f"{cfg['name']} 连接失败", "warning")
            if(len(robots) > 4):
                raise BufferError("最大支持4个机器人的连接")
            # 3. 模型加载
            vision_svc = RKNN_YOLO(self.model_path)
            if vision_svc.pc_yolo is None and vision_svc.rknn is None:
                raise RuntimeError("模型加载失败")

            self.finished.emit(cam_svc, robots, vision_svc)

        except Exception as e:
            self.error.emit(str(e))


# class CameraStream(QObject):
#     def __init__(self, camera_cfg):
#         super().__init__()
#         self.camera_cfg = camera_cfg

#     def run(self):

