"""
@Description :   日志管理器类，用于统一管理应用程序的日志
@Author      :   Cao Yingjie
@Time        :   2023/05/08 10:30:00
"""

import os
import logging
import datetime
from logging.handlers import TimedRotatingFileHandler
import sys
import threading

class LogManager:
    """
    日志管理器类
    用于统一管理应用程序的日志，支持控制台和文件输出，
    以及按日期自动切割日志文件
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LogManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, log_dir="log", app_name="SickVision", level=logging.INFO, 
                 console_output=True, file_output=True, max_backup_count=30):
        """
        初始化日志管理器
        
        Args:
            log_dir (str): 日志目录路径
            app_name (str): 应用程序名称，用于生成日志文件名
            level (int): 日志级别
            console_output (bool): 是否输出到控制台
            file_output (bool): 是否输出到文件
            max_backup_count (int): 最大备份日志文件数量
        """
        if self._initialized:
            return
            
        self.log_dir = log_dir
        self.app_name = app_name
        self.level = level
        self.console_output = console_output
        self.file_output = file_output
        self.max_backup_count = max_backup_count
        self.loggers = {}
        
        # 创建日志目录
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        self._initialized = True
    
    def get_logger(self, name=None):
        """
        获取指定名称的日志器
        
        Args:
            name (str): 日志器名称，如果为None则使用root logger
            
        Returns:
            logging.Logger: 日志器实例
        """
        if name is None:
            name = self.app_name
            
        if name in self.loggers:
            return self.loggers[name]
            
        # 创建新的日志器
        logger = logging.getLogger(name)
        logger.setLevel(self.level)
        logger.propagate = False  # 避免日志传播到父日志器
        
        # 清除已有的处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 日志格式（不包含文件名和行号，保护源码信息）
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 添加控制台处理器
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # 添加文件处理器（按日期生成文件名）
        if self.file_output:
            today_str = datetime.date.today().isoformat()
            log_file = os.path.join(self.log_dir, f"{name}_{today_str}.log")

            # 如果已经有旧日期的文件处理器，则移除
            for h in logger.handlers[:]:
                if isinstance(h, TimedRotatingFileHandler):
                    logger.removeHandler(h)

            file_handler = TimedRotatingFileHandler(
                log_file,
                when="midnight",
                interval=1,
                backupCount=self.max_backup_count,
                encoding="utf-8"
            )
            # 设置后缀模板，使轮转文件名称符合日期
            file_handler.suffix = "%Y-%m-%d.log"
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        self.loggers[name] = logger
        return logger
    
    def set_level(self, level, name=None):
        """
        设置日志器的日志级别
        
        Args:
            level (int): 日志级别
            name (str): 日志器名称，如果为None则设置所有日志器
        """
        if name is not None and name in self.loggers:
            self.loggers[name].setLevel(level)
        elif name is None:
            self.level = level
            for logger in self.loggers.values():
                logger.setLevel(level)
    
    def add_file_handler(self, name, log_file, when="midnight", interval=1, 
                        backup_count=30, encoding="utf-8"):
        """
        为指定日志器添加文件处理器
        
        Args:
            name (str): 日志器名称
            log_file (str): 日志文件路径
            when (str): 日志切割时机
            interval (int): 切割间隔
            backup_count (int): 最大备份数量
            encoding (str): 文件编码
        """
        if name not in self.loggers:
            self.get_logger(name)
            
        logger = self.loggers[name]
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        
        # 添加文件处理器
        file_handler = TimedRotatingFileHandler(
            log_file,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding=encoding
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    def add_console_handler(self, name):
        """
        为指定日志器添加控制台处理器
        
        Args:
            name (str): 日志器名称
        """
        if name not in self.loggers:
            self.get_logger(name)
            
        logger = self.loggers[name]
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    def get_all_loggers(self):
        """
        获取所有日志器
        
        Returns:
            dict: 所有日志器的字典
        """
        return self.loggers 