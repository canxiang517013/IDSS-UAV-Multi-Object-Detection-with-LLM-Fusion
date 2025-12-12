# ui/app.py
import sys
import os
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QScrollArea, QFrame,QTextEdit
)
from PyQt5.QtGui import QImage, QPixmap, QFont
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

        # 视频状态
        self.is_paused = False

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

        control_layout.addWidget(self.open_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.stop_btn)
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
        if self.video_loader:
            self.video_loader.release()
            self.video_loader = None
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
        logger.info("视频播放已停止")

    def update_frame(self):
        start_time = time.time()
        try:
            frame = next(self.video_loader)
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
        # 设置文本并自动滚动到底部（适合流式输出，此处为一次性）
        self.llm_output.setPlainText(result)
        self.llm_output.verticalScrollBar().setValue(
            self.llm_output.verticalScrollBar().maximum()
        )
        logger.info("LLM 分析完成")

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