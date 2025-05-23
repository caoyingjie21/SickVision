"""
@Description :   通用装饰器模块
@Author      :   Cao Yingjie
@Time        :   2025/05/12
"""

import time
import logging
import functools
from typing import Type, Union, Tuple, List, Callable, Optional
import traceback

logger = logging.getLogger(__name__)

def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    logger_name: Optional[str] = None,
    on_retry: Optional[Callable] = None
):
    """
    重试装饰器，用于自动重试可能失败的函数
    
    Args:
        max_retries (int): 最大重试次数
        delay (float): 重试之间的延迟时间（秒）
        exceptions (Exception or tuple): 需要捕获的异常类型
        logger_name (str, optional): 日志记录器名称，如不指定则使用默认日志记录器
        on_retry (callable, optional): 重试前调用的函数，接收(重试次数, 异常, 参数字典)作为参数
        
    Returns:
        function: 装饰过的函数
        
    Example:
        @retry(max_retries=3, delay=2.0)
        def connect_to_device(self, device_id):
            # 连接代码...
            pass
    """
    # 获取指定的日志记录器或使用默认的
    log = logging.getLogger(logger_name) if logger_name else logger
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            # 第一次尝试 + 最大重试次数
            for attempt in range(max_retries + 1):
                try:
                    # 第一次尝试或重试
                    if attempt > 0:
                        log.info(f"重试 {func.__name__}，第 {attempt}/{max_retries} 次尝试")
                        if on_retry:
                            on_retry(attempt, last_exception, dict(args=args, kwargs=kwargs))
                        if delay > 0:
                            time.sleep(delay)
                    
                    # 执行被装饰的函数
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    log.warning(f"{func.__name__} 第 {attempt + 1} 次尝试失败: {str(e)}")
                    
                    # 如果是最后一次尝试，则抛出异常
                    if attempt >= max_retries:
                        log.error(f"{func.__name__} 在 {max_retries + 1} 次尝试后失败")
                        raise
            
            # 理论上不会执行到这里
            return None
            
        return wrapper
    
    return decorator


def require_connection(func):
    """
    检查相机是否已连接的装饰器
    
    为相机操作类的方法添加此装饰器，会在执行方法前检查相机是否已连接。
    如果未连接，将抛出ConnectionError异常。
    
    注意：此装饰器假设被装饰的方法属于一个具有is_connected属性的类
    
    Args:
        func: 需要装饰的方法
        
    Returns:
        function: 装饰过的函数
        
    Example:
        @require_connection
        def get_frame(self):
            # 获取帧的代码...
            pass
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # 检查对象是否有is_connected属性且为True
        if not getattr(self, 'is_connected', False):
            method_name = func.__name__
            class_name = self.__class__.__name__
            error_msg = f"设备未连接，无法执行 {class_name}.{method_name}() 操作"
            
            # 记录错误日志
            log = getattr(self, 'logger', logger)
            log.error(error_msg)
            
            # 抛出连接错误异常
            raise ConnectionError(error_msg)
            
        # 设备已连接，执行原方法
        return func(self, *args, **kwargs)
        
    return wrapper


def safe_disconnect(func):
    """
    安全断开连接的装饰器
    
    为相机类的disconnect方法添加此装饰器，可以确保无论发生什么异常，
    设备的连接状态都会被正确重置，资源会被释放。
    
    Args:
        func: 断开连接的方法
        
    Returns:
        function: 装饰过的函数
        
    Example:
        @safe_disconnect
        def disconnect(self):
            # 断开连接的代码...
            pass
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            # 执行原始的断开连接方法
            return func(self, *args, **kwargs)
        except Exception as e:
            # 记录异常但不重新抛出
            log = getattr(self, 'logger', logger)
            log.error(f"断开连接时发生错误: {str(e)}")
        finally:
            # 无论发生什么，确保连接状态被重置
            self.is_connected = False
            # 确保资源被释放
            if hasattr(self, 'deviceControl'):
                self.deviceControl = None
            if hasattr(self, 'streaming_device'):
                self.streaming_device = None
                
    return wrapper


def catch_and_log(
    logger_name: Optional[str] = None,
    log_level: int = logging.ERROR,
    re_raise: bool = False,
):
    """捕获函数执行中的异常并记录日志，同时在带有 add_log 方法的对象上输出到界面。

    Args:
        logger_name (str, optional): 指定日志器名称，默认为从实例 logger 属性或根日志器。
        log_level (int): 记录日志的级别，默认 logging.ERROR。
        re_raise (bool): 捕获后是否继续抛出异常，默认 False。

    用法示例：
        @catch_and_log(logger_name=__name__)
        def some_method(self):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 推测第一个参数是 self
            instance = args[0] if args else None
            # 选择日志器
            if logger_name is not None:
                log = logging.getLogger(logger_name)
                # 如果未配置处理器，则通过LogManager创建，避免丢失输出
                if not log.handlers:
                    try:
                        from Qcommon.LogManager import LogManager
                        log = LogManager().get_logger(logger_name)
                    except Exception:
                        pass
            else:
                log = getattr(instance, "logger", logger)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录详细堆栈
                err_trace = traceback.format_exc()
                log.log(log_level, f"{func.__name__} 发生异常: {e}\n{err_trace}")

                # 立即刷新所有处理器，确保写入文件
                for h in log.handlers:
                    try:
                        h.flush()
                    except Exception:
                        pass

                # 如果实例有 add_log 方法，则输出到UI日志面板
                if instance is not None and hasattr(instance, "add_log"):
                    try:
                        instance.add_log(f"{func.__name__} 发生异常: {e}", "error")
                    except Exception:
                        pass  # 确保不会因 UI 输出再次报错

                if re_raise:
                    raise
                return None  # 出错时返回 None

        return wrapper

    return decorator 