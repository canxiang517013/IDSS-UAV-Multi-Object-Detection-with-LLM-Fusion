# utils/image_to_video.py
import os
import cv2
import argparse
from pathlib import Path

def images_to_video(
    image_folder: str,
    output_path: str,
    fps: int = 30,
    width: int = None,
    height: int = None,
    sort_by_name: bool = True
):
    """
    将文件夹中的 JPG 图片合成为 MP4 视频
    
    Args:
        image_folder (str): 包含 JPG 图片的文件夹路径
        output_path (str): 输出 MP4 文件路径（如 output.mp4）
        fps (int): 视频帧率，默认 30
        width (int): 输出视频宽度（若为 None，则使用第一张图的宽）
        height (int): 输出视频高度（若为 None，则使用第一张图的高）
        sort_by_name (bool): 是否按文件名排序（确保顺序正确）
    """
    image_folder = Path(image_folder)
    if not image_folder.exists():
        raise FileNotFoundError(f"图片文件夹不存在: {image_folder}")

    # 获取所有 .jpg / .jpeg 文件
    extensions = ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG']
    image_paths = []
    for ext in extensions:
        image_paths.extend(image_folder.glob(ext))
    
    if not image_paths:
        raise ValueError(f"在 {image_folder} 中未找到 JPG 图片")

    # 按文件名排序（保证顺序）
    if sort_by_name:
        image_paths = sorted(image_paths, key=lambda x: x.name)

    # 读取第一张图获取尺寸
    first_img = cv2.imread(str(image_paths[0]))
    if first_img is None:
        raise ValueError(f"无法读取首张图片: {image_paths[0]}")
    
    if width is None or height is None:
        height, width = first_img.shape[:2]

    # 创建 VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4 编码
    video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not video_writer.isOpened():
        raise RuntimeError("无法创建视频写入器，请检查 OpenCV 是否支持 mp4v 编码")

    print(f"正在合成视频: {len(image_paths)} 张图片 → {output_path}")
    for img_path in image_paths:
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"警告: 跳过无效图片 {img_path}")
            continue
        # 调整尺寸（如果指定了 width/height）
        if img.shape[1] != width or img.shape[0] != height:
            img = cv2.resize(img, (width, height))
        video_writer.write(img)

    video_writer.release()
    print(f"✅ 视频已保存至: {output_path}")


def batch_images_to_videos(root_folder: str, output_dir: str, **kwargs):
    """
    批量将 root_folder 下的每个子文件夹中的图片转换为同名视频。
    
    Args:
        root_folder (str): 根目录，包含多个子文件夹
        output_dir (str): 输出视频的目录
        **kwargs: 传递给 images_to_video 的参数（如 fps, width, height）
    """
    root = Path(root_folder)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not root.is_dir():
        raise NotADirectoryError(f"指定路径不是目录: {root}")

    subfolders = [d for d in root.iterdir() if d.is_dir()]
    if not subfolders:
        raise ValueError(f"在 {root} 中未找到任何子文件夹")

    for folder in subfolders:
        video_name = f"{folder.name}.mp4"
        output_path = output_dir / video_name
        try:
            images_to_video(image_folder=str(folder), output_path=str(output_path), **kwargs)
        except Exception as e:
            print(f"❌ 处理文件夹 {folder} 时出错: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将 JPG 图片序列合成为 MP4 视频（支持单文件夹或批量多文件夹）")
    parser.add_argument("input_path", help="输入路径：单个图片文件夹 或 包含多个子文件夹的根目录")
    parser.add_argument("output_path", help="输出路径：单个 MP4 文件 或 视频输出目录")
    parser.add_argument("--batch", action="store_true", help="启用批量模式（自动处理 input_path 下所有子文件夹）")
    parser.add_argument("--fps", type=int, default=30, help="视频帧率（默认 30）")
    parser.add_argument("--width", type=int, default=None, help="输出视频宽度（可选）")
    parser.add_argument("--height", type=int, default=None, help="输出视频高度（可选）")

    args = parser.parse_args()

    if args.batch:
        # 批量模式：input_path 是根目录，output_path 是输出目录
        batch_images_to_videos(
            root_folder=args.input_path,
            output_dir=args.output_path,
            fps=args.fps,
            width=args.width,
            height=args.height
        )
    else:
        # 单文件夹模式
        images_to_video(
            image_folder=args.input_path,
            output_path=args.output_path,
            fps=args.fps,
            width=args.width,
            height=args.height
        )