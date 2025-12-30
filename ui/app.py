# ui/app.py
import sys
import os
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QScrollArea, QFrame,QTextEdit,
    QCheckBox
)
from PyQt5.QtGui import QImage, QPixmap, QFont, QKeyEvent
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
import cv2
import yaml
import time

# 本地模块
from utils.video_loader import VideoLoader
from utils.draw_utils import draw_tracks
from utils.distance_estimator import DistanceEstimator
from models.llm_analyzer import LLMAnalyzer
from utils.logger import setup_logger

logger = setup_logger("UIApp")


class LLMWorker(QThread):
    """后台线程执行 LLM 分析，避免阻塞 UI"""
    result_ready = pyqtSignal(str)

    def __init__(self, llm_analyzer, tracked_objects):
        super().__init__()
        self.llm_analyzer = llm_analyzer
        self.tracked_objects = tracked_objects

    def run(self):
        try:
            result = self.llm_analyzer.analyze(self.tracked_objects)
            self.result_ready.emit(result)
        except Exception as e:
            logger.error(f"LLM 分析异常: {e}")
            self.result_ready.emit(f"[分析失败] {str(e)}")


class TrackingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("无人机目标跟踪与智能决策系统")
        self.resize(1400, 800)

        # 加载配置
        config_path = "config/config.yaml"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.cfg = yaml.safe_load(f)
            if self.cfg is None:
                raise ValueError("配置文件为空")
        except Exception as e:
            QMessageBox.critical(None, "配置错误", f"无法加载配置文件:\n{config_path}\n\n{str(e)}")
            sys.exit(1)

        # 初始化模型
        self.model = None
        self.init_model()

        # 视频相关
        self.video_loader = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.fps = 0
        self.frame_count = 0
        self.last_time = None

        # 距离估算器
        self.distance_estimator = DistanceEstimator()

        # LLM 分析器
        self.llm_analyzer = LLMAnalyzer(model="deepseek-chat")
        self.llm_worker = None
        self.analyze_every = self.cfg.get("llm", {}).get("analyze_every", 30)

        # AirSim相关
        self.airsim_client = None
        self.airsim_loader = None
        self.drone_controller = None
        self.use_airsim = False
        
        # 键盘控制
        self.keyboard_controller = None
        self.control_update_timer = QTimer()
        self.control_update_timer.timeout.connect(self._update_continuous_control)

        # 视频状态
        self.is_paused = False
        
        # 跟踪目标列表（用于无人机控制）
        self.tracked_objects = []

        # 输出目录
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)

        # 初始化 UI
        self.init_ui()

    def init_model(self):
        weights_path = self.cfg["model"]["detector_weights"]
        if not os.path.exists(weights_path):
            logger.warning(f"模型权重不存在: {weights_path}，将使用 Ultralytics 自动下载")
        from ultralytics import YOLO
        self.model = YOLO(weights_path)
        self.class_names = self.cfg["visdrone_classes"]
        logger.info("YOLO 模型加载成功")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # === 左侧：视频显示区 ===
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setStyleSheet("background-color: #000; color: white; font-size: 18px;")
        self.video_label.setText("请加载视频文件")
        main_layout.addWidget(self.video_label)

        # === 右侧：控制面板 ===
        control_panel = QFrame()
        control_panel.setFixedWidth(350)
        control_panel.setStyleSheet("background-color: #f8f9fa; border-left: 1px solid #ddd;")
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(15, 15, 15, 15)

        title_label = QLabel("控制面板")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        control_layout.addWidget(title_label)

        self.status_label = QLabel("状态: 就绪")
        self.status_label.setStyleSheet("color: #555; margin-top: 10px;")
        control_layout.addWidget(self.status_label)

        self.fps_label = QLabel("FPS: --")
        self.target_label = QLabel("目标数: --")
        self.frame_label = QLabel("帧数: --")
        for label in [self.fps_label, self.target_label, self.frame_label]:
            label.setStyleSheet("color: #666;")
            control_layout.addWidget(label)

        control_layout.addSpacing(20)

        # 按钮
        self.open_btn = QPushButton("📁 打开视频")
        self.open_btn.setStyleSheet("padding: 8px; font-size: 14px;")
        self.open_btn.clicked.connect(self.open_video)

        self.pause_btn = QPushButton("⏸ 暂停")
        self.pause_btn.setStyleSheet("padding: 8px; font-size: 14px;")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setStyleSheet("padding: 8px; font-size: 14px;")
        self.stop_btn.clicked.connect(self.stop_video)
        self.stop_btn.setEnabled(False)
        
        self.airsim_btn = QPushButton("🚁 连接AirSim")
        self.airsim_btn.setStyleSheet("padding: 8px; font-size: 14px; background-color: #e7f3ff;")
        self.airsim_btn.clicked.connect(self.toggle_airsim)

        control_layout.addWidget(self.open_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addSpacing(10)
        control_layout.addWidget(self.airsim_btn)
        control_layout.addStretch()

        # LLM 分析区域
        llm_title = QLabel("🧠 LLM 智能分析")
        llm_title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        llm_title.setStyleSheet("margin-top: 20px;")
        control_layout.addWidget(llm_title)

        self.llm_output = QTextEdit()
        self.llm_output.setReadOnly(True)  # 只读
        self.llm_output.setPlaceholderText("等待分析结果...")
        self.llm_output.setStyleSheet(
            "background-color: white; padding: 10px; border: 1px solid #ccc; border-radius: 4px;"
        )
        self.llm_output.setMinimumHeight(120)
        self.llm_output.setMaximumHeight(200)  # 可适当增加，或移除限制


        control_layout.addWidget(self.llm_output)
        
        # === 键盘控制面板 ===
        self.keyboard_panel = QFrame()
        self.keyboard_panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.keyboard_panel.setStyleSheet("margin-top: 20px;")
        keyboard_layout = QVBoxLayout(self.keyboard_panel)
        
        keyboard_title = QLabel("⌨️ 键盘控制")
        keyboard_title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        keyboard_layout.addWidget(keyboard_title)
        
        # 按键说明
        self.keyboard_help = QLabel()
        self.keyboard_help.setTextFormat(Qt.RichText)
        self.keyboard_help.setText(self._get_keyboard_help_text())
        self.keyboard_help.setStyleSheet("font-size: 11px; line-height: 1.5;")
        keyboard_layout.addWidget(self.keyboard_help)
        
        # 速度显示
        self.speed_label = QLabel("飞行速度: 5.0 m/s")
        self.speed_label.setStyleSheet("font-weight: bold; color: #007bff; margin-top: 10px;")
        keyboard_layout.addWidget(self.speed_label)
        
        # 控制开关
        self.keyboard_enabled_btn = QPushButton("启用键盘控制")
        self.keyboard_enabled_btn.setCheckable(True)
        self.keyboard_enabled_btn.setStyleSheet(
            "padding: 8px; font-size: 14px;"
        )
        self.keyboard_enabled_btn.clicked.connect(self._toggle_keyboard_control)
        keyboard_layout.addWidget(self.keyboard_enabled_btn)
        
        control_layout.addWidget(self.keyboard_panel)

        main_layout.addWidget(control_panel)

    def open_video(self):
        video_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        if not video_path:
            return

        try:
            self.video_loader = VideoLoader(video_path)
            self.timer.start(int(1000 / 30))  # ~30 FPS
            self.open_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.is_paused = False
            self.pause_btn.setText("⏸ 暂停")
            self.frame_count = 0
            self.last_time = None
            self.status_label.setText("状态: 正在播放")
            logger.info(f"开始播放视频: {video_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载视频:\n{str(e)}")
            logger.error(f"视频加载失败: {e}")

    def toggle_pause(self):
        if self.is_paused:
            # 继续播放
            self.timer.start(int(1000 / 30))
            self.is_paused = False
            self.pause_btn.setText("⏸ 暂停")
            self.status_label.setText("状态: 正在播放")
            logger.info("视频继续播放")
        else:
            # 暂停
            self.timer.stop()
            self.is_paused = True
            self.pause_btn.setText("▶ 继续")
            self.status_label.setText("状态: 已暂停")
            logger.info("视频已暂停")

    def stop_video(self):
        self.timer.stop()
        
        # 停止视频加载器
        if self.video_loader:
            self.video_loader.release()
            self.video_loader = None
            
        # 停止AirSim加载器
        if self.airsim_loader:
            self.airsim_loader.stop()
            self.airsim_loader = None
        
        # 如果使用AirSim，断开连接
        if self.use_airsim:
            self.stop_airsim()
        
        self.video_label.setText("视频已停止")
        self.open_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.is_paused = False
        self.pause_btn.setText("⏸ 暂停")
        self.status_label.setText("状态: 已停止")
        self.fps_label.setText("FPS: --")
        self.target_label.setText("目标数: --")
        self.frame_label.setText("帧数: --")
        self.tracked_objects = []
        logger.info("视频播放已停止")
    
    def toggle_airsim(self):
        """切换AirSim连接"""
        if not self.use_airsim:
            # 尝试连接AirSim
            try:
                from utils.airsim_client import AirSimClient
                from utils.airsim_loader import AirSimLoader
                from utils.drone_controller import DroneController
                
                # 从配置文件读取AirSim参数
                airsim_config = self.cfg.get("airsim", {})
                ip = airsim_config.get("ip", "127.0.0.1")
                port = airsim_config.get("port", 41451)
                
                self.airsim_client = AirSimClient(ip=ip, port=port)
                
                # 显示连接对话框
                reply = QMessageBox.question(
                    self, "连接AirSim",
                    f"确认连接到AirSim仿真环境？\n\nIP: {ip}\n端口: {port}\n\n确保AirSim已启动并处于运行状态。",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    if self.airsim_client.connect():
                        self.airsim_loader = AirSimLoader(self.airsim_client)
                        self.drone_controller = DroneController(self.airsim_client)
                        self.use_airsim = True
                        
                        # 更新UI
                        self.airsim_btn.setText("🚁 断开AirSim")
                        self.airsim_btn.setStyleSheet("padding: 8px; font-size: 14px; background-color: #ffcccc;")
                        self.open_btn.setEnabled(False)
                        self.video_label.setText("AirSim已连接，点击暂停开始")
                        
                        # 启动定时器
                        self.timer.start(int(1000 / 30))
                        self.pause_btn.setEnabled(True)
                        self.stop_btn.setEnabled(True)
                        self.is_paused = False
                        self.frame_count = 0
                        self.last_time = None
                        self.status_label.setText("状态: AirSim已连接")
                        
                        logger.info("已连接AirSim仿真环境")
                        QMessageBox.information(self, "成功", "已连接到AirSim仿真环境")
                    else:
                        QMessageBox.critical(self, "错误", "连接AirSim失败，请检查AirSim是否正在运行")
                        self.airsim_client = None
                else:
                    self.airsim_client = None
                    
            except ImportError as e:
                QMessageBox.critical(self, "错误", f"缺少AirSim依赖: {e}\n请运行: pip install airsim")
                logger.error(f"缺少AirSim依赖: {e}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"连接AirSim异常: {e}")
                logger.error(f"连接AirSim异常: {e}")
        else:
            # 断开AirSim
            self.stop_airsim()
    
    def stop_airsim(self):
        """停止AirSim连接"""
        # 禁用键盘控制
        if self.keyboard_controller:
            self.keyboard_controller.set_enabled(False)
            self.control_update_timer.stop()
            self.keyboard_enabled_btn.setChecked(False)
            self.keyboard_enabled_btn.setText("启用键盘控制")
            self.keyboard_enabled_btn.setStyleSheet(
                "padding: 8px; font-size: 14px; background-color: #e7f3ff;"
            )
        
        if self.airsim_loader:
            self.airsim_loader.stop()
            self.airsim_loader = None
        
        if self.airsim_client:
            self.airsim_client.disconnect()
            self.airsim_client = None
        
        self.drone_controller = None
        self.use_airsim = False
        
        # 更新UI
        self.airsim_btn.setText("🚁 连接AirSim")
        self.airsim_btn.setStyleSheet("padding: 8px; font-size: 14px; background-color: #e7f3ff;")
        self.open_btn.setEnabled(True)
        
        logger.info("已断开AirSim连接")

    def update_frame(self):
        start_time = time.time()
        try:
            # 根据数据源获取图像
            if self.use_airsim and self.airsim_loader:
                # 从AirSim获取图像
                if not self.airsim_loader.is_running:
                    self.airsim_loader.start()
                frame = next(self.airsim_loader)
            else:
                # 从视频文件获取图像
                frame = next(self.video_loader)
            
            # 目标检测与跟踪
            results = self.model.track(
                frame,
                conf=self.cfg["model"]["conf_threshold"],
                iou=self.cfg["model"]["iou_threshold"],
                persist=True,
                tracker="config/bytetrack.yaml",
                verbose=False
            )
            boxes = results[0].boxes
            annotated_frame = draw_tracks(frame, boxes, self.class_names)

            # 构建结构化目标列表
            tracked_objs = []
            for box in boxes:
                if box.id is None:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls.item())
                class_name = self.class_names[cls_id]
                bbox_h = y2 - y1
                distance = self.distance_estimator.estimate(class_name, bbox_h)

                tracked_objs.append({
                    "id": int(box.id.item()),
                    "class_name": class_name,
                    "conf": float(box.conf.item()),
                    "bbox": [x1, y1, x2, y2],
                    "distance": distance
                })
            
            # 保存跟踪目标列表（用于无人机控制）
            self.tracked_objects = tracked_objs

            # 更新状态
            self.frame_count += 1
            self.frame_label.setText(f"帧数: {self.frame_count}")
            self.target_label.setText(f"目标数: {len(tracked_objs)}")

            if self.last_time:
                elapsed = time.time() - self.last_time
                self.fps = 1.0 / elapsed if elapsed > 0 else 0
                self.fps_label.setText(f"FPS: {self.fps:.1f}")
            self.last_time = time.time()

            # LLM 分析（每 N 帧）
            if self.frame_count % self.analyze_every == 0 and tracked_objs:
                json_path = self.output_dir / "detections.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(tracked_objs, f, ensure_ascii=False, indent=2)
                logger.debug(f"已保存 {len(tracked_objs)} 个目标到 {json_path}")

                if self.llm_worker is None or not self.llm_worker.isRunning():
                    self.llm_worker = LLMWorker(self.llm_analyzer, tracked_objs)
                    self.llm_worker.result_ready.connect(self.on_llm_result)
                    self.llm_worker.start()

            # 显示视频帧
            rgb_image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(
                pixmap.scaled(
                    self.video_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

        except StopIteration:
            self.stop_video()
        except Exception as e:
            logger.exception("处理帧时发生错误")
            self.stop_video()
            QMessageBox.critical(self, "错误", f"视频处理异常:\n{str(e)}")

    def on_llm_result(self, result: str):
        """处理LLM分析结果"""
        # 设置文本并自动滚动到底部
        self.llm_output.setPlainText(result)
        self.llm_output.verticalScrollBar().setValue(
            self.llm_output.verticalScrollBar().maximum()
        )
        
        # 如果连接了AirSim且启用了控制，执行无人机控制
        if self.use_airsim and self.drone_controller and self.tracked_objects:
            try:
                # 解析LLM指令
                command = self.drone_controller.parse_llm_command(result)
                if command:
                    logger.info(f"解析到控制指令: {command}")
                    # 执行控制指令
                    self.drone_controller.execute_command(command, self.tracked_objects)
                else:
                    logger.debug("LLM分析中未包含可执行的控制指令")
            except Exception as e:
                logger.error(f"无人机控制执行失败: {e}")
        
        logger.info("LLM 分析完成")

    def _get_keyboard_help_text(self) -> str:
        """生成键盘帮助文本"""
        help_text = """
        <table>
        <tr><td><b>W</b></td><td>前进</td></tr>
        <tr><td><b>S</b></td><td>后退</td></tr>
        <tr><td><b>A</b></td><td>向左</td></tr>
        <tr><td><b>D</b></td><td>向右</td></tr>
        <tr><td><b>Q</b></td><td>左转</td></tr>
        <tr><td><b>E</b></td><td>右转</td></tr>
        <tr><td><b>PageUp</b></td><td>上升</td></tr>
        <tr><td><b>PageDown</b></td><td>下降</td></tr>
        <tr><td><b>空格</b></td><td>悬停</td></tr>
        <tr><td><b>+/-</b></td><td>加速/减速</td></tr>
        <tr><td><b>R</b></td><td>重置</td></tr>
        </table>
        """
        return help_text
    
    def _toggle_keyboard_control(self, enabled: bool):
        """切换键盘控制"""
        if not self.use_airsim:
            QMessageBox.warning(self, "提示", "请先连接AirSim")
            self.keyboard_enabled_btn.setChecked(False)
            return
        
        if enabled:
            if not self.keyboard_controller:
                from utils.keyboard_controller import KeyboardController
                self.keyboard_controller = KeyboardController(self.airsim_client)
            
            self.keyboard_controller.set_enabled(True)
            self.control_update_timer.start(50)  # 20Hz更新频率
            self.keyboard_enabled_btn.setText("禁用键盘控制")
            self.keyboard_enabled_btn.setStyleSheet(
                "padding: 8px; font-size: 14px; background-color: #ffcccc;"
            )
            self.video_label.setFocus()  # 设置焦点以接收键盘事件
            logger.info("键盘控制已启用")
        else:
            if self.keyboard_controller:
                self.keyboard_controller.set_enabled(False)
            self.control_update_timer.stop()
            self.keyboard_enabled_btn.setText("启用键盘控制")
            self.keyboard_enabled_btn.setStyleSheet(
                "padding: 8px; font-size: 14px; background-color: #e7f3ff;"
            )
            logger.info("键盘控制已禁用")
    
    def _update_continuous_control(self):
        """更新连续控制"""
        if self.keyboard_controller:
            self.keyboard_controller.update_continuous_control()
            
            # 更新速度显示
            if self.keyboard_controller:
                self.speed_label.setText(
                    f"飞行速度: {self.keyboard_controller.get_speed():.1f} m/s"
                )
    
    def keyPressEvent(self, event: QKeyEvent):
        """处理按键按下事件"""
        super().keyPressEvent(event)
        if self.keyboard_controller:
            self.keyboard_controller.on_key_press(event.key())
    
    def keyReleaseEvent(self, event: QKeyEvent):
        """处理按键释放事件"""
        super().keyReleaseEvent(event)
        if self.keyboard_controller:
            self.keyboard_controller.on_key_release(event.key())
    
    def closeEvent(self, event):
        self.stop_video()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    window = TrackingApp()
    window.show()
    sys.exit(app.exec_())
