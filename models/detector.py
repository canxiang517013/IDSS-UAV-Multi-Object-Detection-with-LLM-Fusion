from ultralytics import YOLO
import cv2

class YOLODetector:
    def __init__(self, model_path="yolov8n.pt", conf_thres=0.4, iou_thres=0.5):
        self.model = YOLO(model_path)
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres

    def detect(self, frame):
        results = self.model(frame, conf=self.conf_thres, iou=self.iou_thres, verbose=False)
        return results[0].boxes  # xyxy, conf, cls