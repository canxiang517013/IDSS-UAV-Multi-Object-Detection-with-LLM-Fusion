import numpy as np

class DistanceEstimator:
    def __init__(self):
        # 预设各类目标的平均真实高度（单位：米）
        self.average_heights = {
            "pedestrian": 1.7,
            "people": 1.7,
            "bicycle": 1.2,
            "car": 1.5,
            "van": 2.0,
            "truck": 3.0,
            "tricycle": 1.8,
            "awning-tricycle": 1.8,
            "bus": 3.0,
            "motor": 1.2,
        }

    def estimate(self, class_name: str, bbox_height: int) -> float:
        """
        基于目标框高度估算距离（单位：米）
        公式：distance = (real_height * focal_length) / pixel_height
        简化版：假设 focal_length 已归一化，直接用比例
        """
        if bbox_height <= 0:
            return 0.0  # 防止除零

        real_height = self.average_heights.get(class_name, 1.0)  # ← 默认 1.0 米
        # 简单反比模型：目标越大，距离越近
        distance = real_height * 1000.0 / bbox_height  # 调整系数使结果合理
        return max(0.1, min(distance, 1000.0))  # 限制在 [0.1, 1000] 米