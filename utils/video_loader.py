import cv2

class VideoLoader:
    def __init__(self, source):
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise ValueError(f"无法打开视频源: {source}")

    def __iter__(self):
        return self

    def __next__(self):
        ret, frame = self.cap.read()
        if not ret:
            raise StopIteration
        return frame

    def release(self):
        self.cap.release()