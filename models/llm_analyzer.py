# models/llm_analyzer.py
import os
import json
import requests
from typing import List, Dict
from utils.logger import setup_logger

logger = setup_logger("LLMAnalyzer")


class LLMAnalyzer:
    def __init__(self, model: str = "deepseek-chat"):
        """
        初始化 DeepSeek LLM 分析器
        
        Args:
            model (str): 使用的模型名称，默认为 'deepseek-chat'
        """
        self.model = model
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
        # 从环境变量加载 API Key
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            logger.error("未找到 DEEPSEEK_API_KEY 环境变量，请检查 .env 文件")
            raise ValueError("DeepSeek API Key 未配置")

        # 系统提示词（可根据需求调整）
        self.system_prompt = (
            "你是一个无人机智能决策助手。请根据以下检测到的地面目标信息，完成以下任务："
            "1. 分析每个目标的类型、大致距离（米）、可能的行为（如“静止”、“移动”、“聚集”）。"
            "2. 判断是否存在异常或高优先级目标（如人群聚集、违停车辆）。"
            "3. 给出1-2条具体的飞行任务建议（例如：“飞向ID 3的公交车进行车牌识别”，“远离人群区域保持50米以上高度”）。"
            "4. 用简洁中文输出，不要使用Markdown。"
        )

    def format_detections(self, tracked_objects: List[Dict]) -> str:
        lines = []
        for obj in tracked_objects:
            dist = obj.get("distance", 0.0)
            if dist is None:
                dist_str = "未知"
            else:
                dist_str = f"{dist:.1f}"
            line = f"ID{obj['id']}: {obj['class_name']} (置信度{obj['conf']:.2f}, 距离{dist_str}米)"
            lines.append(line)
        return "\n".join(lines)

    def analyze(self, tracked_objects: List[Dict]) -> str:
        """
        调用 DeepSeek API 生成分析结果
        
        Args:
            tracked_objects: 结构化目标列表
            
        Returns:
            str: LLM 生成的中文分析文本
        """
        if not tracked_objects:
            return "当前画面中未检测到任何目标。"

        # 构造用户消息
        input_text = self.format_detections(tracked_objects)
        user_message = f"输入数据：\n{input_text}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.3,
            "stream": False
        }

        try:
            logger.debug(f"正在调用 DeepSeek API，目标数量: {len(tracked_objects)}")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30  # 30秒超时
            )

            # === 关键：检查 HTTP 状态码 ===
            if response.status_code != 200:
                error_snippet = response.text[:200] if response.text else "[无响应体]"
                logger.error(
                    f"DeepSeek API 返回错误 [{response.status_code}]: {error_snippet}"
                )
                return (
                    f"[API 错误] 状态码: {response.status_code}\n"
                    f"响应: {error_snippet}..."
                )

            # === 检查响应是否为空 ===
            if not response.text.strip():
                logger.error("DeepSeek API 返回空响应")
                return "[API 调用失败] 服务器返回空内容"

            # === 尝试解析 JSON ===
            try:
                data = response.json()
                # 提取 LLM 回复
                content = data["choices"][0]["message"]["content"].strip()
                logger.info("LLM 分析成功完成")
                return content
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(
                    f"JSON 解析失败: {e}. 原始响应: {response.text[:200]}"
                )
                return (
                    f"[解析失败] 非预期响应格式\n"
                    f"原始内容: {response.text[:100]}..."
                )

        except requests.exceptions.Timeout:
            logger.error("DeepSeek API 调用超时（30秒）")
            return "[API 调用失败] 请求超时，请检查网络连接"
        except requests.exceptions.ConnectionError:
            logger.error("无法连接 DeepSeek API 服务器")
            return "[API 调用失败] 网络连接错误，请检查代理或防火墙设置"
        except Exception as e:
            logger.exception("DeepSeek 调用发生未预期异常")
            return f"[系统错误] {str(e)}"