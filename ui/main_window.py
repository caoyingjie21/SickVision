#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
                            QPushButton, QTextEdit, QGroupBox, QSplitter, 
                            QFrame, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QImage, QFont, QPalette, QColor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和尺寸
        self.setWindowTitle("视觉系统")
        self.resize(1200, 800)
        
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
        
        # 创建机器人连接配置组
        robot_group = QGroupBox("机器人连接配置")
        robot_layout = QGridLayout(robot_group)
        
        # IP地址配置
        ip_label = QLabel("机器人IP地址:")
        self.ip_input = QLineEdit("192.168.1.1")
        
        # 端口配置
        port_label = QLabel("端口号:")
        self.port_input = QLineEdit("8080")
        
        # 连接按钮
        self.connect_btn = QPushButton("连接机器人")
        self.connect_btn.setMinimumHeight(35)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:pressed {
                background-color: #2a66c8;
            }
        """)
        
        # 添加到机器人连接配置布局
        robot_layout.addWidget(ip_label, 0, 0)
        robot_layout.addWidget(self.ip_input, 0, 1)
        robot_layout.addWidget(port_label, 1, 0)
        robot_layout.addWidget(self.port_input, 1, 1)
        robot_layout.addWidget(self.connect_btn, 2, 0, 1, 2)
        
        # 创建参数配置组（预留空间）
        param_group = QGroupBox("参数配置")
        param_layout = QVBoxLayout(param_group)
        
        # 这里可以添加更多参数配置控件
        param_layout.addWidget(QLabel("参数配置区域（待添加）"))
        
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
        
        # 添加到右侧布局
        right_layout.addWidget(robot_group)
        right_layout.addWidget(param_group)
        right_layout.addStretch()  # 添加弹性空间，使启动按钮位于底部
        right_layout.addWidget(self.start_btn)

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
        """)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 