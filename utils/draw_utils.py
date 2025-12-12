import cv2

def draw_tracks(frame, boxes, class_names):
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        track_id = int(box.id.item()) if box.id is not None else -1
        cls_id = int(box.cls.item())
        conf = float(box.conf.item())

        label = f"ID:{track_id} {class_names[cls_id]} {conf:.2f}"
        color = (0, 255, 0) if track_id != -1 else (0, 0, 255)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame