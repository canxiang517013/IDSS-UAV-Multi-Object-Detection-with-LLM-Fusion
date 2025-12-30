"""
AirSim客户端封装模块
功能：
- 连接AirSim服务器
- 获取摄像头图像
- 获取无人机状态（位置、高度、姿态）
- 控制无人机移动（可选）
"""

import cv2
import airsim
import numpy as np
from typing import Tuple, Optional
from utils.logger import setup_logger

logger = setup_logger("AirSimClient")


class AirSimClient:
    def __init__(self, ip: str = "127.0.0.1", port: int = 41451):
        """
        初始化AirSim客户端
        
        Args:
            ip: AirSim服务器IP地址（默认本地）
            port: AirSim服务器端口（默认41451）
        """
        self.ip = ip
        self.port = port
        self.client = None
        self.connected = False
        
    def connect(self) -> bool:
        """连接到AirSim服务器"""
        try:
            self.client = airsim.MultirotorClient(ip=self.ip, port=self.port)
            self.client.confirmConnection()
            self.client.enableApiControl(True)
            self.client.armDisarm(True)
            self.connected = True
            logger.info(f"成功连接到AirSim服务器: {self.ip}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"连接AirSim失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.client:
            try:
                self.client.enableApiControl(False)
                self.client.armDisarm(False)
            except:
                pass
            self.connected = False
            logger.info("已断开AirSim连接")
    
    def get_camera_image(self, camera_name: str = "0", 
                        image_type: airsim.ImageType = airsim.ImageType.Scene) -> np.ndarray:
        """
        获取摄像头图像
        
        Args:
            camera_name: 摄像头名称（默认"0"为主摄像头）
            image_type: 图像类型（场景图、深度图等）
            
        Returns:
            BGR格式的OpenCV图像数组
        """
        if not self.connected:
            raise RuntimeError("未连接到AirSim服务器")
        
        try:
            # 获取RGB图像
            response = self.client.simGetImage(camera_name, image_type)
            
            # 转换为OpenCV格式
            if response == "None" or response is None:
                raise RuntimeError("获取图像失败")
            
            # 解码图像数据
            img1d = np.fromstring(response, np.uint8)
            img_bgr = cv2.imdecode(img1d, cv2.IMREAD_COLOR)
            
            if img_bgr is None:
                raise RuntimeError("图像解码失败")
            
            return img_bgr
        except Exception as e:
            logger.error(f"获取摄像头图像失败: {e}")
            raise
    
    def get_drone_state(self) -> dict:
        """
        获取无人机状态信息
        
        Returns:
            包含位置、高度、姿态等信息的字典
        """
        if not self.connected:
            raise RuntimeError("未连接到AirSim服务器")
        
        try:
            state = self.client.getMultirotorState()
            kinematics = state.kinematics_estimated
            
            return {
                "position": {
                    "x": kinematics.position.x_val,
                    "y": kinematics.position.y_val,
                    "z": -kinematics.position.z_val  # AirSim Z轴向下为正，转换为高度
                },
                "velocity": {
                    "x": kinematics.linear_velocity.x_val,
                    "y": kinematics.linear_velocity.y_val,
                    "z": kinematics.linear_velocity.z_val
                },
                "orientation": {
                    "roll": kinematics.orientation.roll_val,
                    "pitch": kinematics.orientation.pitch_val,
                    "yaw": kinematics.orientation.yaw_val
                },
                "collision": state.collision.has_collided
            }
        except Exception as e:
            logger.error(f"获取无人机状态失败: {e}")
            raise
    
    def move_to_position(self, x: float, y: float, z: float, 
                        velocity: float = 5.0, timeout_sec: int = 10):
        """
        移动无人机到指定位置（可选功能）
        
        Args:
            x, y, z: 目标位置（米）
            velocity: 飞行速度（米/秒）
            timeout_sec: 超时时间
        """
        if not self.connected:
            raise RuntimeError("未连接到AirSim服务器")
        
        try:
            self.client.moveToPositionAsync(
                x, y, -z,  # AirSim中Z轴向下为正
                velocity,
                timeout_sec=timeout_sec
            ).join()
            logger.info(f"移动到位置: ({x}, {y}, {z})")
        except Exception as e:
            logger.error(f"移动到位置失败: {e}")
            raise
    
    def rotate_to_yaw(self, yaw: float, timeout_sec: int = 5):
        """
        旋转无人机到指定偏航角（可选功能）
        
        Args:
            yaw: 目标偏航角（度）
            timeout_sec: 超时时间
        """
        if not self.connected:
            raise RuntimeError("未连接到AirSim服务器")
        
        try:
            self.client.rotateToYawAsync(yaw, timeout_sec=timeout_sec).join()
            logger.info(f"旋转到偏航角: {yaw}度")
        except Exception as e:
            logger.error(f"旋转失败: {e}")
            raise
    
    def hover(self):
        """悬停（可选功能）"""
        if not self.connected:
            raise RuntimeError("未连接到AirSim服务器")
        
        try:
            self.client.hoverAsync().join()
            logger.info("无人机进入悬停模式")
        except Exception as e:
            logger.error(f"悬停失败: {e}")
            raise
    
    def moveByVelocityAsync(self, vx: float, vy: float, vz: float, 
                          duration: float = 0.1):
        """
        按速度向量移动无人机
        
        Args:
            vx: X方向速度（米/秒）
            vy: Y方向速度（米/秒）
            vz: Z方向速度（米/秒，正值为下降）
            duration: 持续时间（秒）
        """
        if not self.connected:
            raise RuntimeError("未连接到AirSim服务器")
        
        try:
            self.client.moveByVelocityAsync(
                vx, vy, vz, duration,
                drivetrain=airsim.DrivetrainType.ForwardOnly,
                yaw_mode=airsim.YawMode(True)
            )
        except Exception as e:
            logger.error(f"按速度移动失败: {e}")
            raise
    
    def rotateByYawRateAsync(self, yaw_rate: float, duration: float = 0.1):
        """
        按偏航角速度旋转无人机
        
        Args:
            yaw_rate: 偏航角速度（度/秒，正值为顺时针）
            duration: 持续时间（秒）
        """
        if not self.connected:
            raise RuntimeError("未连接到AirSim服务器")
        
        try:
            self.client.rotateByYawRateAsync(yaw_rate, duration)
        except Exception as e:
            logger.error(f"按角速度旋转失败: {e}")
            raise
    
    def reset(self):
        """重置仿真环境"""
        if self.client:
            try:
                self.client.reset()
                logger.info("仿真环境已重置")
            except Exception as e:
                logger.error(f"重置仿真环境失败: {e}")
