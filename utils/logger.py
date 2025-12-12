# utils/logger.py
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

def setup_logger(
    name: str = "DroneTracking",
    log_dir: str = "logs",
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    encoding: str = "utf-8"
) -> logging.Logger:
    """
    配置并返回一个 Logger 实例
    
    Args:
        name (str): Logger 名称（建议用模块名或项目名）
        log_dir (str): 日志文件保存目录
        console_level (int): 控制台输出的最低日志级别
        file_level (int): 文件输出的最低日志级别
        encoding (str): 日志文件编码（推荐 utf-8 支持中文）
    
    Returns:
        logging.Logger: 配置好的 Logger 对象
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加 Handler（防止多次调用导致日志重复）
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # Logger 本身设为最低级别，由 Handler 控制输出

    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # === Formatter ===
    file_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)-8s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_formatter = logging.Formatter(
        fmt="%(levelname)-8s - %(message)s"
    )

    # === File Handler（按天轮转，保留30天）===
    file_handler = TimedRotatingFileHandler(
        filename=log_path / f"{name}.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding=encoding,
        utc=False
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(file_formatter)
    file_handler.suffix = "%Y-%m-%d"  # 日志文件后缀：DroneTracking.log.2025-12-09

    # === Console Handler ===
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)

    # 添加 Handler
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 禁止日志向上传播（避免被 root logger 重复处理）
    logger.propagate = False

    return logger


# 全局 Logger 实例（可选）
# 如果你希望整个项目共用一个 logger，取消注释下面一行：
# logger = setup_logger()

if __name__ == "__main__":
    # 测试日志输出
    test_logger = setup_logger("TestLogger")
    test_logger.debug("这是一条调试信息")
    test_logger.info("系统启动成功")
    test_logger.warning("检测到低电量")
    test_logger.error("视频流中断")
    test_logger.critical("致命错误：无法连接无人机")