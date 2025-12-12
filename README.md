# 无人机目标跟踪与智能决策系统

## 项目简介

这是一个基于计算机视觉的无人机目标跟踪与智能决策系统。系统使用深度学习模型检测和跟踪无人机视角下的各种目标，并通过大语言模型(LLM)对检测到的目标进行智能分析和决策建议。

## 主要功能

- **目标检测**：使用YOLO模型检测10种常见的地面目标（行人、人、自行车、汽车、面包车、卡车、三轮车、带篷三轮车、公交车、摩托车）
- **目标跟踪**：采用ByteTrack算法实现多目标的持续跟踪
- **距离估算**：基于目标框高度估算目标与无人机的距离
- **智能分析**：集成DeepSeek大语言模型，对检测到的目标进行智能分析
- **可视化界面**：提供友好的PyQt5图形用户界面

## 系统架构

```
drone-tracking-system/
├── main.py                    # 主程序入口
├── config/                    # 配置文件目录
│   ├── config.yaml           # 主配置文件
│   ├── bytetrack.yaml        # ByteTrack跟踪器配置
│   └── llm_prompt.txt        # LLM提示词模板
├── models/                   # 模型相关代码
│   ├── detector.py           # 目标检测器
│   ├── llm_analyzer.py       # LLM分析器
│   └── weights/              # 模型权重文件
│       ├── best.pt           # 最佳模型权重（VisDrone数据集训练）
│       └── last.pt           # 最后一次训练的模型权重
├── ui/                       # 用户界面
│   └── app.py                # PyQt5应用程序
├── utils/                    # 工具函数
│   ├── distance_estimator.py # 距离估算器
│   ├── draw_utils.py         # 绘图工具
│   ├── image_to_video.py     # 图像转视频工具
│   ├── logger.py             # 日志工具
│   └── video_loader.py       # 视频加载器
├── logs/                     # 日志目录
└── requirements.txt          # 项目依赖
```

## 技术栈

- **深度学习框架**：Ultralytics YOLOv8
- **目标跟踪算法**：ByteTrack
- **GUI框架**：PyQt5
- **大语言模型**：DeepSeek
- **计算机视觉**：OpenCV
- **配置管理**：YAML
- **日志管理**：Python logging

## 安装说明

### 1. 环境要求

- Python 3.8+
- CUDA（可选，用于GPU加速）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置API密钥

创建`.env`文件并添加DeepSeek API密钥：

```
DEEPSEEK_API_KEY=your_api_key_here
```

### 4. 模型准备

系统已经包含了在VisDrone数据集上训练的预训练模型（`models/weights/best.pt`），该模型可以在`models/weights/`目录中找到。

## 使用说明

### 1. 启动系统

```bash
python main.py
```

### 2. 操作步骤

1. 点击"打开视频"按钮选择要处理的视频文件
2. 系统将自动开始检测和跟踪目标
3. 右侧面板会显示实时状态信息（FPS、目标数、帧数等）
4. 系统每30帧会调用LLM进行一次智能分析，结果会显示在"LLM智能分析"区域
5. 可以使用暂停/继续按钮控制视频播放
6. 点击"停止"按钮结束视频处理

### 3. 配置参数

可以通过修改`config/config.yaml`文件来调整系统参数：

```yaml
model:
  detector_weights: "models/weights/best.pt"  # 模型权重路径
  conf_threshold: 0.4                          # 置信度阈值
  iou_threshold: 0.5                          # IoU阈值

visdrone_classes:
  - pedestrian
  - people
  - bicycle
  - car
  - van
  - truck
  - tricycle
  - awning-tricycle
  - bus
  - motor

llm:
  analyze_every: 30                           # LLM分析间隔（帧数）
```

## 模型性能

### 检测模型

- **数据集**：VisDrone 2019 Dataset
- **目标类别**：10种常见地面目标
- **模型架构**：YOLOv8
- **评估指标**：mAP（平均精度均值）

### 跟踪算法

- **算法名称**：ByteTrack
- **特点**：高精度、实时性、处理遮挡能力强
- **配置参数**：详见`config/bytetrack.yaml`

## 智能分析功能

系统集成了DeepSeek大语言模型，能够：

1. 分析每个目标的类型、大致距离和可能的行为
2. 判断是否存在异常或高优先级目标
3. 提供具体的飞行任务建议
4. 输出简洁的中文分析报告

## 输出结果

- **实时视频流**：显示检测结果和跟踪轨迹
- **检测数据**：保存为JSON格式（`outputs/detections.json`）
- **分析报告**：实时显示在界面上

## 注意事项

1. 确保已正确配置DeepSeek API密钥
2. 视频文件格式支持：mp4、avi、mov、mkv
3. 建议使用GPU加速以获得更好的性能
4. 系统会自动保存检测数据到outputs目录

## 致谢

### 数据集

本项目的检测模型使用了**VisDrone数据集**进行训练。VisDrone是一个大规模的无人机视角目标检测数据集，包含了各种复杂场景下的目标标注数据。

**VisDrone数据集链接**：[VisDrone Dataset](https://github.com/VisDrone/VisDrone-Dataset)

### 预训练模型

本项目的预训练模型基于CSDN上博主[weixin_45679938](https://blog.csdn.net/weixin_45679938)分享的模型进行微调。该博主提供了详细的VisDrone数据集训练教程和模型权重。

**参考文章链接**：[VisDrone数据集训练YOLO模型教程](https://blog.csdn.net/weixin_45679938/article/details/142439297)

感谢VisDrone数据集的提供者和CSDN上博主的分享，他们的工作为本项目的开发提供了重要的基础支持。

## 开发者信息

本项目由计算机视觉课程设计团队开发，用于学习和研究计算机视觉目标检测与跟踪技术。

## 许可证

本项目仅供学习和研究使用。
