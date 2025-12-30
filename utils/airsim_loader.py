"""
AirSim图像流加载器（生成器模式）
功能：从AirSim实时获取图像流，模拟VideoLoader接口
"""

import time
from typing import Generator
from utils.airsim_client import AirSimClient
from utils.logger import setup_logger

logger = setup_logger("AirSimLoader")


class AirSimLoader:
    def __init__(self, airsim_client: AirSimClient, camera_name: str = "0"):
        """
        初始化AirSim图像加载器
        
        Args:
            airsim_client: AirSimClient实例
            camera_name: 摄像头名称
        """
        self.client = airsim_client
        self.camera_name = camera_name
        self.is_running = False
        self.frame_count = 0
        
    def __iter__(self):
        return self
    
    def __next__(self):
        """获取下一帧图像"""
        if not self.is_running:
            raise StopIteration
        
        try:
            frame = self.client.get_camera_image(self.camera_name)
            self.frame_count += 1
            return frame
        except Exception as e:
            logger.error(f"获取图像失败: {e}")
            raise StopIteration
    
    def start(self):
        """启动图像流"""
        if not self.client.connected:
            raise RuntimeError("AirSim客户端未连接")
        self.is_running = True
        self.frame_count = 0
        logger.info("AirSim图像流已启动")
    
    def stop(self):
        """停止图像流"""
        self.is_running = False
        logger.info(f"AirSim图像流已停止，共获取{self.frame_count}帧")
    
    def release(self):
        """释放资源"""
        self.stop()
