#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time
import json
import platform
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
                            QPushButton, QTextEdit, QGroupBox, QSplitter, 
                            QFrame, QSpacerItem, QSizePolicy, QComboBox,
                            QFileDialog, QTableWidget, QTableWidgetItem,
                            QHeaderView, QAbstractItemView, QDialog, QFormLayout,
                            QMessageBox, QAction)
from PyQt5.QtCore import Qt, QSize, QObject, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont, QPalette, QColor
from Qcommon.decorators import catch_and_log
# 直接从各个包导入，不使用完整的SickVision路径
from sick.SickSDK import QtVisionSick
from epson.EpsonRobot import EpsonRobot
from rknn.RknnYolo import RKNN_YOLO
from Qcommon.LogManager import LogManager
from workflows.system_loader import SystemLoader

class RobotDialog(QDialog):
    """机器人配置对话框"""
    def __init__(self, parent=None, robot_data=None):
        super().__init__(parent)
        self.setWindowTitle("机器人配置")
        self.resize(400, 250)
        
        # 设置布局
        layout = QFormLayout(self)
        
        # 机器人名称
        self.name_input = QLineEdit()
        if robot_data and 'name' in robot_data:
            self.name_input.setText(robot_data['name'])
        layout.addRow("机器人名称:", self.name_input)
        
        # IP地址
        self.ip_input = QLineEdit()
        if robot_data and 'ip' in robot_data:
            self.ip_input.setText(robot_data['ip'])
        else:
            self.ip_input.setText("192.168.1.1")
        layout.addRow("IP地址:", self.ip_input)
        
        # 通信端口
        self.cmd_port_input = QLineEdit()
        if robot_data and 'cmd_port' in robot_data:
            self.cmd_port_input.setText(str(robot_data['cmd_port']))
        else:
            self.cmd_port_input.setText("60000")
        layout.addRow("通信端口:", self.cmd_port_input)
        
        # 状态端口
        self.status_port_input = QLineEdit()
        if robot_data and 'status_port' in robot_data:
            self.status_port_input.setText(str(robot_data['status_port']))
        else:
            self.status_port_input.setText("60001")
        layout.addRow("状态端口:", self.status_port_input)
        
        # 备注
        self.remark_input = QLineEdit()
        if robot_data and 'remark' in robot_data:
            self.remark_input.setText(robot_data['remark'])
        layout.addRow("备注:", self.remark_input)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addRow("", button_layout)
    
    def get_data(self):
        """获取对话框中的数据"""
        return {
            'name': self.name_input.text(),
            'ip': self.ip_input.text(),
            'cmd_port': int(self.cmd_port_input.text()),
            'status_port': int(self.status_port_input.text()),
            'remark': self.remark_input.text()
        }

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.log_manager = LogManager()
        self.logger = self.log_manager.get_logger()
        # 界面操作时记录日志
        self.logger.info("应用程序启动")
        # 设置窗口标题和尺寸
        self.setWindowTitle("视觉系统")
        self.resize(1200, 800)
        self.robots = {}
        # 创建菜单栏
        self.setup_menu_bar()
        
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # 创建左侧显示区域和右侧控制面板
        self.left_panel = QWidget()
        self.right_panel = QWidget()
        
        # 左侧面板占据更多空间
        self.main_layout.addWidget(self.left_panel, 7)
        self.main_layout.addWidget(self.right_panel, 3)
        
        # 设置左侧面板布局
        self.setup_left_panel()
        
        # 设置右侧面板布局
        self.setup_right_panel()
        
        # 设置样式
        self.setup_styles()
        # 加载默认配置
        self.load_robot_config()
        self.log_output.append("界面加载完成")

        # 用于实时刷新相机画面的定时器
        self.camera_timer: QTimer | None = None

        # 平台显示
        platform_text = platform.system().lower()
        if platform_text.startswith("windows"):
            self.current_platform = "win"
        elif "linux" in platform_text and os.uname().machine in ("aarch64", "armv7l", "arm64"):
            self.current_platform = "aarch"
        else:
            self.current_platform = "other"

        self.platform_label = QLabel(f"当前平台: {self.current_platform}")
        self.platform_label.setStyleSheet("color:#333;")

        # 系统运行状态标志
        self.system_running = False

    def add_log(self, text: str, level: str = "info"):
        """根据等级向日志输出控件写入彩色文本
        level 可选: debug / info / warning / error
        """
        level = level.lower()
        color_map = {
            "debug": "gray",
            "info": "blue",
            "warning": "orange",
            "error": "red",
        }
        color = color_map.get(level, "black")
        self.log_output.append(f'<span style="color:{color};">[{level.upper()}] {text}</span>')

    def on_start_clicked(self):
        cfg_cam = {"ipAddr": "192.168.10.5", "port": 2122 }
        cfg_robots = self.get_robot_list()
        mdl_path = getattr(self, "model_path", None)

        self.loader_thread = QThread(self)
        self.loader = SystemLoader(cfg_cam, cfg_robots, mdl_path)
        self.loader.moveToThread(self.loader_thread)

        self.loader.progress.connect(self.add_log)
        self.loader.finished.connect(self.on_system_ready)
        self.loader.error.connect(self.handle_worker_error)
        self.loader_thread.started.connect(self.loader.run)
        self.loader_thread.start()

    def on_system_ready(self, camera, robots, detector):
        self.camera = camera
        self.robots = robots
        self.detector = detector
        self.add_log("系统加载完成", "info")
        self.system_running = True
        # 切换按钮为"停止系统"
        self.start_btn.setText("停止系统")
        self.start_btn.clicked.disconnect()
        self.start_btn.clicked.connect(self.stop_system)
        # 启动相机画面刷新
        self.start_camera_stream()
        if hasattr(self, "loader_thread") and self.loader_thread.isRunning() and self.loader_thread != QThread.currentThread():
            self.loader_thread.quit()
            self.loader_thread.wait()
        self.start_btn.setEnabled(True)
        

    def handle_worker_error(self, msg: str):
        """
        所有后台线程错误统一走这里
        连接方式: worker.error.connect(self.handle_worker_error)
        """
        # 1. UI 日志 / 文件日志
        self.add_log(f"任务失败: {msg}", "error")
        self.logger.error(f"任务失败: {msg}")

        # 2. 弹窗提示
        QMessageBox.critical(self, "任务执行失败", msg)

        # 3. 找到触发此错误的 Worker 所在线程，并安全结束
        worker = self.sender()
        if worker is not None:
            th = worker.thread()
            if th and th.isRunning() and th != QThread.currentThread():
                th.quit()
                th.wait()

        # 4. 恢复界面可用状态（按需）
        self.start_btn.setEnabled(True)
        self.start_btn.setText("启动系统")  # 失败后复原按钮
        self.start_btn.clicked.disconnect()
        self.start_btn.clicked.connect(self.on_start_clicked)
        self.system_running = False
        # 停止画面刷新，避免继续调用已失效的相机
        self.stop_camera_stream()

    def setup_left_panel(self):
        """设置左侧面板，包含视频/图像显示和日志输出"""
        left_layout = QVBoxLayout(self.left_panel)
        
        # 创建上部显示区域的分割器
        display_splitter = QSplitter(Qt.Horizontal)
        
        # 创建相机视频流窗口
        self.camera_view = QLabel("相机视频流")
        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setMinimumSize(400, 300)
        self.camera_view.setStyleSheet("background-color: #2a2a2a; color: white; border-radius: 5px;")
        
        # 创建图像显示窗口
        self.image_view = QLabel("图像显示")
        self.image_view.setAlignment(Qt.AlignCenter)
        self.image_view.setMinimumSize(400, 300)
        self.image_view.setStyleSheet("background-color: #2a2a2a; color: white; border-radius: 5px;")
        
        # 添加到分割器
        display_splitter.addWidget(self.camera_view)
        display_splitter.addWidget(self.image_view)
        
        # 设置分割器初始尺寸
        display_splitter.setSizes([500, 500])
        
        # 创建日志输出区域
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)
        self.log_output.setStyleSheet("background-color: #f5f5f5; border-radius: 5px;")
        
        log_layout.addWidget(self.log_output)
        
        # 添加到左侧布局
        left_layout.addWidget(display_splitter, 7)
        left_layout.addWidget(log_group, 3)

    def setup_right_panel(self):
        """设置右侧面板，包含机器人连接配置和启动按钮"""
        right_layout = QVBoxLayout(self.right_panel)
        
        # ---------------- 相机配置组 -----------------
        camera_group = QGroupBox("相机配置")
        cam_form = QGridLayout(camera_group)

        cam_ip_label = QLabel("IP 地址:")
        self.camera_ip_input = QLineEdit("192.168.10.5")
        cam_port_label = QLabel("控制端口:")
        self.camera_port_input = QLineEdit("2122")

        self.camera_test_btn = QPushButton("测试连接")
        self.camera_test_btn.clicked.connect(self.test_camera_connection)

        cam_form.addWidget(cam_ip_label,   0, 0)
        cam_form.addWidget(self.camera_ip_input, 0, 1)
        cam_form.addWidget(cam_port_label, 1, 0)
        cam_form.addWidget(self.camera_port_input, 1, 1)
        cam_form.addWidget(self.camera_test_btn, 2, 0, 1, 2)

        # ---------------- 机器人连接配置组 -----------------
        # 创建机器人连接配置组
        robot_group = QGroupBox("机器人连接配置")
        robot_layout = QVBoxLayout(robot_group)
        
        # 创建表格
        self.robot_table = QTableWidget(0, 5)  # 初始为0行，5列
        self.robot_table.setHorizontalHeaderLabels(["名称", "IP地址", "通信端口", "状态端口", "备注"])
        self.robot_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.robot_table.verticalHeader().setVisible(False)
        self.robot_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.robot_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.robot_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # 创建按钮区域
        btn_layout = QHBoxLayout()
        
        # 添加按钮
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_robot)
        
        # 编辑按钮
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.clicked.connect(self.edit_robot)
        
        # 删除按钮
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_robot)
        
        # 连接按钮
        self.connect_btn = QPushButton("测试连接")
        self.connect_btn.clicked.connect(self.connect_robot)
        
        # 保存配置按钮
        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.clicked.connect(self.save_robot_config)
        
        # 添加到按钮布局
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.save_config_btn)
        
        # 添加表格和按钮到机器人配置布局
        robot_layout.addWidget(self.robot_table)
        robot_layout.addLayout(btn_layout)
        
        # 创建模型配置组
        model_group = QGroupBox("模型配置")
        model_layout = QGridLayout(model_group)
        
        # 模型选择下拉框
        model_label = QLabel("选择模型:")
        self.model_combo = QComboBox()
        
        # 添加刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_model_list)
        
        # 添加浏览和测试按钮
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_model)

        self.test_model_btn = QPushButton("测试模型")
        self.test_model_btn.clicked.connect(self.test_model)
        
        # 平台显示
        platform_text = platform.system().lower()
        if platform_text.startswith("windows"):
            self.current_platform = "win"
        elif "linux" in platform_text and os.uname().machine in ("aarch64", "armv7l", "arm64"):
            self.current_platform = "aarch"
        else:
            self.current_platform = "other"

        self.platform_label = QLabel(f"当前平台: {self.current_platform}")
        self.platform_label.setStyleSheet("color:#333;")
        
        # 模型信息
        info_label = QLabel("模型信息:")
        self.model_info = QLabel("未选择模型")
        self.model_info.setStyleSheet("color: #666; background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        self.model_info.setWordWrap(True)
        
        # 选择模型时更新信息
        self.model_combo.currentIndexChanged.connect(self.update_model_info)
        
        # 添加到模型配置布局
        model_layout.addWidget(model_label, 0, 0)
        model_layout.addWidget(self.model_combo, 0, 1)
        model_layout.addWidget(self.refresh_btn, 0, 2)
        model_layout.addWidget(self.browse_btn, 1, 0, 1, 2)
        model_layout.addWidget(self.test_model_btn, 1, 2)
        model_layout.addWidget(self.platform_label, 2, 0, 1, 3)
        model_layout.addWidget(info_label, 3, 0)
        model_layout.addWidget(self.model_info, 4, 0, 1, 3)
        
        # 创建启动按钮（位于右下角）
        self.start_btn = QPushButton("启动系统")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
            QPushButton:pressed {
                background-color: #1a8047;
            }
        """)
        self.start_btn.clicked.connect(self.on_start_clicked)
        # 按顺序添加到右侧布局
        right_layout.addWidget(camera_group)
        right_layout.addWidget(robot_group)
        right_layout.addWidget(model_group)
        right_layout.addStretch()  # 添加弹性空间，使启动按钮位于底部
        right_layout.addWidget(self.start_btn)
        
        # 现在所有UI组件都已创建，可以安全地刷新模型列表
        self.refresh_model_list()  # 初始化模型列表
    
    def _add_table_item(self, row, col, text):
        """添加带工具提示的表格项"""
        item = QTableWidgetItem(text)
        item.setToolTip(text)  # 设置悬停提示，显示完整内容
        self.robot_table.setItem(row, col, item)
        
    def add_robot(self):
        """添加新的机器人配置"""
        # 打开对话框
        dialog = RobotDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 获取对话框数据
            robot_data = dialog.get_data()
            
            # 添加到表格
            row_count = self.robot_table.rowCount()
            self.robot_table.insertRow(row_count)
            
            # 设置表格内容
            self._add_table_item(row_count, 0, robot_data['name'])
            self._add_table_item(row_count, 1, robot_data['ip'])
            self._add_table_item(row_count, 2, str(robot_data['cmd_port']))
            self._add_table_item(row_count, 3, str(robot_data['status_port']))
            self._add_table_item(row_count, 4, robot_data['remark'])
            
            # 选中新添加的行
            self.robot_table.selectRow(row_count)
            self.log_output.append(f"添加了新的机器人配置: {robot_data['name']}")
    
    def edit_robot(self):
        """编辑选中的机器人配置"""
        # 获取选中行
        selected_rows = self.robot_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要编辑的机器人")
            return
        
        row = selected_rows[0].row()
        
        # 获取当前数据
        current_data = {
            'name': self.robot_table.item(row, 0).text(),
            'ip': self.robot_table.item(row, 1).text(),
            'cmd_port': int(self.robot_table.item(row, 2).text()),
            'status_port': int(self.robot_table.item(row, 3).text()),
            'remark': self.robot_table.item(row, 4).text() if self.robot_table.item(row, 4) else ""
        }
        
        # 打开对话框
        dialog = RobotDialog(self, current_data)
        if dialog.exec_() == QDialog.Accepted:
            # 获取对话框数据
            robot_data = dialog.get_data()
            
            # 更新表格数据
            self._add_table_item(row, 0, robot_data['name'])
            self._add_table_item(row, 1, robot_data['ip'])
            self._add_table_item(row, 2, str(robot_data['cmd_port']))
            self._add_table_item(row, 3, str(robot_data['status_port']))
            self._add_table_item(row, 4, robot_data['remark'])
            
            self.log_output.append(f"更新了机器人配置: {robot_data['name']}")
    
    def delete_robot(self):
        """删除选中的机器人配置"""
        # 获取选中行
        selected_rows = self.robot_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的机器人")
            return
        
        row = selected_rows[0].row()
        robot_name = self.robot_table.item(row, 0).text()
        
        # 确认删除
        reply = QMessageBox.question(self, "确认删除", 
                                     f"确定要删除机器人 \"{robot_name}\" 的配置吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.robot_table.removeRow(row)
            self.log_output.append(f"删除了机器人配置: {robot_name}")
    
    def connect_robot(self):
        """连接选中的机器人"""
        # 获取选中行
        selected_rows = self.robot_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要连接的机器人")
            return
        
        row = selected_rows[0].row()
        
        # 获取连接信息
        robot_name = self.robot_table.item(row, 0).text()
        ip = self.robot_table.item(row, 1).text()
        cmd_port = int(self.robot_table.item(row, 2).text())
        status_port = int(self.robot_table.item(row, 3).text())
        if(self.robots[robot_name] is not None):
            QMessageBox.warning(self, "警告", "机器人已连接,无需重复连接")
            self.add_log("机器人已连接,无需重复连接", "warning")
            return
        # 这里只是模拟连接，实际应用需要实现真正的连接逻辑
        self.log_output.append(f"正在连接到机器人: {robot_name}({ip}:{cmd_port}/{status_port})...")
        robot = EpsonRobot(ip, cmd_port, status_port)
        if not robot.connect():
            QMessageBox.warning(self, "连接失败", f"连接到机器人: {robot_name} 失败")
            self.add_log(f"连接到机器人: {robot_name} 失败", "error")
            return
        QMessageBox.information(self, "连接成功", f"已成功连接到机器人: {robot_name}")
        self.log_output.append(f"可以连接到机器人: {robot_name}")
        robot.disconnect()
    
    def save_robot_config(self):
        """保存机器人配置到文件"""
        # 获取配置目录
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_dir = os.path.join(root_dir, "config")
        
        # 确保目录存在
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # 配置文件路径
        config_file = os.path.join(config_dir, "robots.json")
        
        # 收集所有机器人配置
        robots = []
        for row in range(self.robot_table.rowCount()):
            robot = {
                'name': self.robot_table.item(row, 0).text(),
                'ip': self.robot_table.item(row, 1).text(),
                'cmd_port': int(self.robot_table.item(row, 2).text()),
                'status_port': int(self.robot_table.item(row, 3).text()),
                'remark': self.robot_table.item(row, 4).text() if self.robot_table.item(row, 4) else ""
            }
            robots.append(robot)
        
        # 保存到文件
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(robots, f, ensure_ascii=False, indent=4)
            
            self.log_output.append(f"机器人配置已保存到: {config_file}")
            QMessageBox.information(self, "保存成功", "机器人配置已保存")
        except Exception as e:
            self.log_output.append(f"保存机器人配置时出错: {str(e)}")
            QMessageBox.warning(self, "保存失败", f"保存机器人配置时出错: {str(e)}")
    
    def load_robot_config(self):
        """从文件加载机器人配置"""
        # 获取配置文件路径
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file = os.path.join(root_dir, "config", "robots.json")
        
        # 检查文件是否存在
        if not os.path.exists(config_file):
            self.log_output.append("未找到机器人配置文件，使用默认配置")
            # 添加一个默认机器人配置
            self.robot_table.insertRow(0)
            self._add_table_item(0, 0, "默认机器人")
            self._add_table_item(0, 1, "192.168.1.1")
            self._add_table_item(0, 2, "60000")
            self._add_table_item(0, 3, "60001")
            self._add_table_item(0, 4, "默认配置")
            return
        
        # 从文件加载配置
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                robots = json.load(f)
            
            # 清空表格
            self.robot_table.setRowCount(0)
            
            # 添加机器人配置到表格
            for i, robot in enumerate(robots):
                self.robot_table.insertRow(i)
                self._add_table_item(i, 0, robot.get('name', ""))
                self._add_table_item(i, 1, robot.get('ip', ""))
                self._add_table_item(i, 2, str(robot.get('cmd_port', "")))
                self._add_table_item(i, 3, str(robot.get('status_port', "")))
                self._add_table_item(i, 4, robot.get('remark', ""))
            
            self.log_output.append(f"已加载 {len(robots)} 个机器人配置")
            
            # 选中第一行
            if self.robot_table.rowCount() > 0:
                self.robot_table.selectRow(0)
        
        except Exception as e:
            self.log_output.append(f"加载机器人配置时出错: {str(e)}")
            # 添加一个默认机器人配置
            self.robot_table.insertRow(0)
            self._add_table_item(0, 0, "默认机器人")
            self._add_table_item(0, 1, "192.168.1.1")
            self._add_table_item(0, 2, "60000")
            self._add_table_item(0, 3, "60001")
            self._add_table_item(0, 4, "默认配置")

    def refresh_model_list(self):
        """刷新模型列表"""
        # 记住当前选择的模型
        current_model = self.model_combo.currentText() if self.model_combo.count() > 0 else ""
        
        self.model_combo.clear()
        
        # 获取项目根目录
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        models_dir = os.path.join(root_dir, "models")
        
        ext = ".rknn" if self.current_platform == "aarch" else ".onnx" and ".pt"
        
        if os.path.exists(models_dir):
            # 查找rknn模型文件
            model_files = [f for f in os.listdir(models_dir)
                          if f.endswith(ext) and os.path.isfile(os.path.join(models_dir, f))]
            
            if model_files:
                for model in model_files:
                    self.model_combo.addItem(model)
                self.log_output.append(f"找到 {len(model_files)} 个{ext}模型文件")
                
                # 如果之前有选择模型，尝试恢复选择
                if current_model and current_model in model_files:
                    index = self.model_combo.findText(current_model)
                    if index >= 0:
                        self.model_combo.setCurrentIndex(index)
                else:
                    # 默认选择第一个模型
                    self.model_combo.setCurrentIndex(0)
                
                # 确保更新模型信息
                self.update_model_info()
            else:
                self.model_combo.addItem("未找到模型文件")
                self.log_output.append(f"models目录中未找到{ext}模型文件")
                self.model_info.setText("未找到模型")
        else:
            self.model_combo.addItem("models目录不存在")
            self.log_output.append("models目录不存在")
            self.model_info.setText("models目录不存在")
    
    def browse_model(self):
        """浏览选择模型文件"""
        # 获取项目根目录
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        models_dir = os.path.join(root_dir, "models")
        
        # 打开文件对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择RKNN模型文件", 
            models_dir, 
            "RKNN模型文件 (*.rknn)"
        )
        
        if file_path:
            # 显示文件名
            file_name = os.path.basename(file_path)
            
            # 检查是否已在列表中
            index = self.model_combo.findText(file_name)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            else:
                # 添加到下拉列表
                self.model_combo.addItem(file_name)
                self.model_combo.setCurrentText(file_name)
            
            self.log_output.append(f"已选择模型文件: {file_name}")
    
    def update_model_info(self):
        """更新模型信息"""
        if self.model_combo.count() == 0:
            self.model_info.setText("未选择模型")
            return
            
        current_model = self.model_combo.currentText()
        
        if current_model and current_model not in ["未找到模型文件", "models目录不存在"]:
            # 获取项目根目录
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(root_dir, "models", current_model)
            # 将完整路径保存到实例属性，供后续使用
            self.model_path = model_path
            
            if os.path.exists(model_path):
                try:
                    # 获取文件大小
                    size_bytes = os.path.getsize(model_path)
                    size_mb = size_bytes / (1024 * 1024)
                    
                    # 获取修改时间
                    mod_time = os.path.getmtime(model_path)
                    mod_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
                    
                    # 更新信息显示
                    info_text = f"文件名: {current_model}\n大小: {size_mb:.2f} MB\n修改日期: {mod_time_str}"
                    self.model_info.setText(info_text)
                except Exception as e:
                    self.model_info.setText(f"读取模型信息出错: {str(e)}")
                    self.log_output.append(f"读取模型信息出错: {str(e)}")
            else:
                self.model_info.setText("模型文件不存在")
                self.model_path = None  # 文件不存在，清空路径
        else:
            self.model_info.setText("未选择有效模型")
            self.model_path = None

    def setup_styles(self):
        """设置界面样式"""
        # 设置全局字体
        font = QFont("微软雅黑", 10)
        QApplication.setFont(font)
        
        # 设置整体样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
            QLabel {
                padding: 2px;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QPushButton {
                padding: 5px;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QTableWidget {
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #e6f3ff;
                color: black;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #cccccc;
                font-weight: bold;
            }
        """)

    def setup_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()

        # 系统菜单
        system_menu = menu_bar.addMenu("系统")
        exit_act = QAction("退出", self)
        exit_act.triggered.connect(self.close)
        system_menu.addAction(exit_act)

        # 详细配置菜单
        detail_menu = menu_bar.addMenu("详细配置")
        open_cfg_act = QAction("打开机器人配置", self)
        open_cfg_act.triggered.connect(self.open_config_file)
        detail_menu.addAction(open_cfg_act)

        # 版本菜单
        version_menu = menu_bar.addMenu("版本")
        about_act = QAction("关于", self)
        about_act.triggered.connect(self.show_about_dialog)
        version_menu.addAction(about_act)

    def open_config_file(self):
        """打开机器人配置文件所在目录"""
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_dir = os.path.join(root_dir, "config")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        # 使用文件浏览器打开目录
        try:
            if sys.platform.startswith("win"):
                os.startfile(config_dir)
            elif sys.platform.startswith("darwin"):
                os.system(f"open {config_dir}")
            else:
                os.system(f"xdg-open {config_dir}")
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开目录: {str(e)}")

    def show_about_dialog(self):
        """显示版本信息"""
        about_text = "VisionSystem\n版本: 1.0.0\n开发者:曹英杰"
        QMessageBox.information(self, "关于", about_text)

    def get_robot_list(self):
        """
        返回当前表格中的机器人配置列表
        [
            {"name": "...", "ip": "...", "cmd_port": 60000, "status_port": 60001, "remark": "..."},
            ...
        ]
        同时缓存到 self.robot_configs
        """
        robots = []
        for row in range(self.robot_table.rowCount()):
            robots.append({
                "name": self.robot_table.item(row, 0).text(),
                "ip": self.robot_table.item(row, 1).text(),
                "cmd_port": int(self.robot_table.item(row, 2).text()),
                "status_port": int(self.robot_table.item(row, 3).text()),
                "remark": self.robot_table.item(row, 4).text() if self.robot_table.item(row, 4) else ""
            })
        self.robot_configs = robots
        return robots

    # ---------- 相机测试连接 ----------
    def test_camera_connection(self):
        ip = self.camera_ip_input.text().strip()
        try:
            port = int(self.camera_port_input.text())
        except ValueError:
            QMessageBox.warning(self, "输入错误", "相机端口必须为数字！")
            return

        self.add_log("测试相机连接…", "info")
        if(self.camera is not None):
            QMessageBox.warning(self, "测试结果", "相机已连接,无需测试")
            self.add_log("相机已连接,无需测试", "warning")
            return
        cam = QtVisionSick(ipAddr=ip, port=port)
        ok = False
        try:
            ok = cam.connect(use_single_step=False)
        except Exception as e:
            self.add_log(f"连接失败: {e}", "error")
        finally:
            cam.disconnect()

        if ok:
            self.add_log("相机连接正常", "info")
            QMessageBox.information(self, "测试结果", "相机连接成功！")
        else:
            self.add_log("相机连接失败", "error")
            QMessageBox.warning(self, "测试结果", "相机连接失败！")

    # ------------------ 相机画面刷新 ------------------
    def start_camera_stream(self):
        """创建并启动QTimer定时刷新相机视频流"""
        if self.camera is None:
            return
        if self.camera_timer is None:
            self.camera_timer = QTimer(self)
            self.camera_timer.timeout.connect(self.update_camera_view)
        if not self.camera_timer.isActive():
            self.camera_timer.start(50)  # 约20FPS

    def stop_camera_stream(self):
        if self.camera_timer and self.camera_timer.isActive():
            self.camera_timer.stop()

        # 清空 QLabel 中的图像并恢复占位文字
        if hasattr(self, "camera_view") and isinstance(self.camera_view, QLabel):
            self.camera_view.clear()
            self.camera_view.setText("相机视频流")

    def update_camera_view(self):
        """抓取一帧并显示到 QLabel"""
        if self.camera is None:
            return
        try:
            success, _, frame = self.camera.get_frame()
            if not success:
                return
            # frame 是灰度 np.ndarray -> 转成 RGB 便于QImage显示
            import cv2
            rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            h, w, _ = rgb.shape
            bytes_per_line = 3 * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg).scaled(self.camera_view.size(), Qt.KeepAspectRatio)
            self.camera_view.setPixmap(pix)
        except Exception as e:
            self.add_log(f"更新相机画面失败: {e}", "warning")

    # ---------- 窗口关闭事件 ----------
    def closeEvent(self, event):
        # 停止定时器，断开设备
        self.stop_camera_stream()
        try:
            if hasattr(self, "camera") and self.camera:
                self.camera.disconnect()
            if hasattr(self, "robots"):
                for bot in self.robots.values():
                    bot.disconnect()
        except Exception:
            pass
        super().closeEvent(event)

    # ---------------- 停止系统 ----------------
    def stop_system(self):
        self.start_btn.setEnabled(False)
        self.add_log("停止系统中…", "info")

        # 停止相机流
        self.stop_camera_stream()

        # 断开相机
        try:
            if hasattr(self, "camera") and self.camera:
                self.camera.disconnect()
        except Exception:
            pass

        # 断开机器人
        try:
            if hasattr(self, "robots"):
                for bot in self.robots.values():
                    bot.disconnect()
        except Exception:
            pass

        self.add_log("系统已停止", "info")

        # 恢复按钮为启动
        self.start_btn.setText("启动系统")
        self.start_btn.clicked.disconnect()
        self.start_btn.clicked.connect(self.on_start_clicked)
        self.start_btn.setEnabled(True)
        self.system_running = False

    # ------------------ 测试模型 ------------------
    def test_model(self):
        """尝试加载当前选择的模型，验证可用性"""
        if not hasattr(self, "model_path") or self.model_path is None:
            QMessageBox.warning(self, "测试模型", "请先选择模型文件！")
            self.add_log("未选择模型文件，无法测试", "warning")
            return
        
        self.add_log("开始测试模型加载…", "info")
        try:
            detector = RKNN_YOLO(self.model_path)
            detector.release()
            QMessageBox.information(self, "测试模型", "模型加载成功！")
            self.add_log("模型加载成功", "info")
        except Exception as e:
            QMessageBox.warning(self, "测试模型", f"模型加载失败: {e}")
            self.add_log(f"模型加载失败: {e}", "error")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())