"""
键盘控制无人机模块
功能：
- 监听键盘事件
- 映射按键到控制指令
- 支持多键同时按下
- 连续按键控制
"""

import time
from typing import Set, Dict, Optional
from PyQt5.QtCore import Qt
from utils.logger import setup_logger

logger = setup_logger("KeyboardController")


class KeyboardController:
    def __init__(self, airsim_client):
        """
        初始化键盘控制器
        
        Args:
            airsim_client: AirSimClient实例
        """
        self.client = airsim_client
        self.enabled = False
        self.speed = 5.0  # 默认速度 m/s
        self.rotation_speed = 30.0  # 旋转速度 度/秒
        self.vertical_speed = 2.0  # 垂直速度 m/s
        
        # 按键状态跟踪
        self.pressed_keys: Set[int] = set()
        self.last_update_time = 0
        
        # 按键到控制动作的映射
        self.key_map = {
            # 方向控制
            Qt.Key_W: "forward",
            Qt.Key_S: "backward",
            Qt.Key_A: "left",
            Qt.Key_D: "right",
            Qt.Key_Q: "rotate_left",
            Qt.Key_E: "rotate_right",
            Qt.Key_PageUp: "up",
            Qt.Key_PageDown: "down",
            
            # 功能控制
            Qt.Key_Space: "hover",
            Qt.Key_Plus: "speed_up",
            Qt.Key_Minus: "speed_down",
            Qt.Key_R: "reset"
        }
        
        # 速度限制
        self.max_speed = 20.0  # 最大速度 m/s
        self.min_speed = 1.0   # 最小速度 m/s
    
    def set_enabled(self, enabled: bool):
        """启用/禁用键盘控制"""
        self.enabled = enabled
        logger.info(f"键盘控制已{'启用' if enabled else '禁用'}")
    
    def on_key_press(self, key: int):
        """
        处理按键按下事件
        
        Args:
            key: Qt按键代码
        """
        if not self.enabled:
            return
        
        self.pressed_keys.add(key)
        action = self.key_map.get(key)
        
        if action:
            logger.debug(f"按键按下: {key} -> {action}")
            self._execute_action(action)
    
    def on_key_release(self, key: int):
        """
        处理按键释放事件
        
        Args:
            key: Qt按键代码
        """
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
            logger.debug(f"按键释放: {key}")
    
    def _execute_action(self, action: str):
        """
        执行控制动作
        
        Args:
            action: 动作名称
        """
        try:
            if action == "forward":
                self.client.moveByVelocityAsync(
                    self.speed, 0, 0, 0.1
                )
            elif action == "backward":
                self.client.moveByVelocityAsync(
                    -self.speed, 0, 0, 0.1
                )
            elif action == "left":
                self.client.moveByVelocityAsync(
                    0, self.speed, 0, 0.1
                )
            elif action == "right":
                self.client.moveByVelocityAsync(
                    0, -self.speed, 0, 0.1
                )
            elif action == "up":
                self.client.moveByVelocityAsync(
                    0, 0, -self.vertical_speed, 0.1
                )
            elif action == "down":
                self.client.moveByVelocityAsync(
                    0, 0, self.vertical_speed, 0.1
                )
            elif action == "rotate_left":
                self.client.rotateByYawRateAsync(
                    -self.rotation_speed, 0.1
                )
            elif action == "rotate_right":
                self.client.rotateByYawRateAsync(
                    self.rotation_speed, 0.1
                )
            elif action == "hover":
                self.client.hover()
            elif action == "speed_up":
                self.speed = min(self.speed + 1.0, self.max_speed)
                logger.info(f"速度增加: {self.speed:.1f} m/s")
            elif action == "speed_down":
                self.speed = max(self.speed - 1.0, self.min_speed)
                logger.info(f"速度降低: {self.speed:.1f} m/s")
            elif action == "reset":
                self.client.reset()
                logger.info("无人机已重置")
                
        except Exception as e:
            logger.error(f"执行动作 {action} 失败: {e}")
    
    def update_continuous_control(self):
        """
        更新连续控制（用于定时器）
        处理需要持续按住按键的控制
        """
        if not self.enabled or not self.pressed_keys:
            return
        
        current_time = time.time()
        if current_time - self.last_update_time < 0.05:  # 20Hz更新频率
            return
        
        self.last_update_time = current_time
        
        # 处理持续按键
        for key in self.pressed_keys:
            action = self.key_map.get(key)
            if action in ["forward", "backward", "left", "right", 
                        "up", "down", "rotate_left", "rotate_right"]:
                self._execute_action(action)
    
    def get_key_bindings(self) -> Dict[str, str]:
        """
        获取按键绑定说明
        
        Returns:
            按键绑定字典
        """
        return {
            "W": "前进",
            "S": "后退",
            "A": "向左",
            "D": "向右",
            "Q": "左转",
            "E": "右转",
            "PageUp": "上升",
            "PageDown": "下降",
            "空格": "悬停",
            "+": "加速",
            "-": "减速",
            "R": "重置"
        }
    
    def set_speed(self, speed: float):
        """
        设置飞行速度
        
        Args:
            speed: 速度值（米/秒）
        """
        self.speed = max(self.min_speed, min(speed, self.max_speed))
        logger.info(f"设置速度: {self.speed:.1f} m/s")
    
    def get_speed(self) -> float:
        """获取当前速度"""
        return self.speed
    
    def reset_speed(self):
        """重置速度到默认值"""
        self.speed = 5.0
        logger.info(f"速度已重置: {self.speed:.1f} m/s")
