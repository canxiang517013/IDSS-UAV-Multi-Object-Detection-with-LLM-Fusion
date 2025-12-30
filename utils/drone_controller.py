"""
无人机控制模块
功能：根据LLM决策生成控制指令，控制AirSim无人机
"""

import re
from typing import Optional, Dict, List
from utils.airsim_client import AirSimClient
from utils.logger import setup_logger

logger = setup_logger("DroneController")


class DroneController:
    def __init__(self, airsim_client: AirSimClient):
        """
        初始化无人机控制器
        
        Args:
            airsim_client: AirSimClient实例
        """
        self.client = airsim_client
        self.current_position = None
        self.enabled = True  # 控制开关
        
    def set_enabled(self, enabled: bool):
        """设置控制开关"""
        self.enabled = enabled
        logger.info(f"无人机控制已{'启用' if enabled else '禁用'}")
        
    def parse_llm_command(self, llm_analysis: str) -> Optional[Dict]:
        """
        解析LLM分析文本，提取控制指令
        
        支持的指令格式：
        - "飞向ID {id}的{class_name}..."
        - "远离{target}..."
        - "保持{distance}米高度..."
        - "向{direction}移动..."
        
        Args:
            llm_analysis: LLM生成的分析文本
            
        Returns:
            控制指令字典，包含action和parameters
        """
        if not self.enabled:
            return None
            
        command = {
            "action": None,
            "parameters": {}
        }
        
        # 匹配"飞向ID X的..."
        match = re.search(r'飞向ID\s*(\d+)', llm_analysis)
        if match:
            target_id = int(match.group(1))
            command["action"] = "move_to_target"
            command["parameters"]["target_id"] = target_id
            return command
        
        # 匹配"远离..."
        match = re.search(r'远离(\w+)', llm_analysis)
        if match:
            target = match.group(1)
            command["action"] = "move_away"
            command["parameters"]["target"] = target
            return command
        
        # 匹配"保持X米高度"
        match = re.search(r'保持(\d+(?:\.\d+)?)米高度', llm_analysis)
        if match:
            altitude = float(match.group(1))
            command["action"] = "set_altitude"
            command["parameters"]["altitude"] = altitude
            return command
            
        # 匹配"上升"或"下降"
        match = re.search(r'(上升|下降)\s*(\d+(?:\.\d+)?)\s*米', llm_analysis)
        if match:
            direction = match.group(1)
            altitude_delta = float(match.group(2))
            command["action"] = "adjust_altitude"
            command["parameters"]["direction"] = direction
            command["parameters"]["delta"] = altitude_delta
            return command
        
        # 匹配"悬停"
        match = re.search(r'悬停', llm_analysis)
        if match:
            command["action"] = "hover"
            return command
        
        return None
    
    def execute_command(self, command: Dict, tracked_objects: List[Dict] = None):
        """
        执行控制指令
        
        Args:
            command: 控制指令字典
            tracked_objects: 当前跟踪的目标列表（用于位置计算）
        """
        if not self.enabled:
            logger.debug("无人机控制已禁用，跳过指令执行")
            return
            
        if not command or not command.get("action"):
            logger.info("无有效控制指令")
            return
        
        action = command["action"]
        params = command["parameters"]
        
        try:
            if action == "move_to_target":
                self._move_to_target(params.get("target_id"), tracked_objects)
            elif action == "move_away":
                self._move_away(params.get("target"), tracked_objects)
            elif action == "set_altitude":
                self._set_altitude(params.get("altitude"))
            elif action == "adjust_altitude":
                self._adjust_altitude(params.get("direction"), params.get("delta"))
            elif action == "hover":
                self._hover()
            else:
                logger.warning(f"未知指令: {action}")
                
        except Exception as e:
            logger.error(f"执行指令失败: {e}")
    
    def _move_to_target(self, target_id: int, tracked_objects: List[Dict]):
        """飞向指定目标"""
        if not tracked_objects:
            logger.warning("目标列表为空，无法移动")
            return
        
        # 查找目标
        target_obj = None
        for obj in tracked_objects:
            if obj["id"] == target_id:
                target_obj = obj
                break
        
        if not target_obj:
            logger.warning(f"未找到ID为{target_id}的目标")
            return
        
        # 获取当前无人机位置
        state = self.client.get_drone_state()
        current_pos = state["position"]
        
        # 获取目标距离信息
        target_distance = target_obj.get("distance", 0)
        target_class = target_obj.get("class_name", "unknown")
        
        logger.info(f"飞向ID {target_id}的{target_class}，当前距离约{target_distance:.1f}米")
        
        # 简单策略：保持当前高度，向前移动一定距离
        # 实际应用中需要结合目标在图像中的位置计算精确的目标位置
        move_distance = min(target_distance - 5.0, 50.0)  # 保持5米安全距离，最多移动50米
        if move_distance > 0:
            # 假设无人机朝向目标，简化为向前移动
            # 实际应用需要计算目标在世界坐标系中的位置
            logger.info(f"向前移动{move_distance:.1f}米接近目标")
            # self.client.move_to_position(
            #     current_pos["x"],  # 简化示例，实际需要计算目标位置
            #     current_pos["y"],
            #     current_pos["z"],
            #     velocity=3.0
            # )
        else:
            logger.info("目标距离过近，保持当前位置")
    
    def _move_away(self, target: str, tracked_objects: List[Dict]):
        """远离指定目标"""
        logger.info(f"远离{target}")
        
        # 获取当前无人机位置
        state = self.client.get_drone_state()
        current_pos = state["position"]
        
        # 简单策略：向后移动20米
        logger.info("向后移动20米远离目标")
        # self.client.move_to_position(
        #     current_pos["x"] - 20,  # 简化示例
        #     current_pos["y"],
        #     current_pos["z"],
        #     velocity=3.0
        # )
    
    def _set_altitude(self, altitude: float):
        """设置高度"""
        logger.info(f"设置高度为{altitude}米")
        
        # 获取当前无人机位置
        state = self.client.get_drone_state()
        current_pos = state["position"]
        
        # 只改变Z坐标
        # self.client.move_to_position(
        #     current_pos["x"],
        #     current_pos["y"],
        #     altitude,
        #     velocity=2.0
        # )
    
    def _adjust_altitude(self, direction: str, delta: float):
        """调整高度"""
        state = self.client.get_drone_state()
        current_pos = state["position"]
        current_altitude = current_pos["z"]
        
        if direction == "上升":
            new_altitude = current_altitude + delta
        else:  # 下降
            new_altitude = current_altitude - delta
        
        # 限制高度范围（10米 - 150米）
        new_altitude = max(10.0, min(new_altitude, 150.0))
        
        logger.info(f"{direction}{delta}米，从{current_altitude:.1f}米调整到{new_altitude:.1f}米")
        
        # self.client.move_to_position(
        #     current_pos["x"],
        #     current_pos["y"],
        #     new_altitude,
        #     velocity=2.0
        # )
    
    def _hover(self):
        """悬停"""
        try:
            self.client.hover()
            logger.info("无人机进入悬停模式")
        except Exception as e:
            logger.error(f"悬停失败: {e}")
    
    def get_control_status(self) -> Dict:
        """
        获取控制器状态
        
        Returns:
            包含控制器状态信息的字典
        """
        return {
            "enabled": self.enabled,
            "connected": self.client.connected if self.client else False
        }
