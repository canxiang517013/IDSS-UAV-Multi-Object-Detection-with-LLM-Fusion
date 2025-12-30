# AirSim仿真平台集成说明

## 概述

本文档说明如何将无人机跟踪系统与AirSim仿真平台集成，实现从仿真环境实时获取摄像头图像流，进行目标检测、跟踪和智能决策。

## 系统架构

```
AirSim仿真环境
    ↓ (图像流)
AirSim客户端 → AirSim加载器 → 检测跟踪系统
    ↓ (LLM决策)
无人机控制器 → AirSim控制API
```

## 安装步骤

### 1. 安装AirSim

#### Windows安装

1. 下载AirSim二进制包：
   - 访问：https://github.com/microsoft/AirSim/releases
   - 下载最新版本的Windows二进制包

2. 解压并运行：
   ```bash
   cd AirSim
   .\run.bat
   ```

#### Linux安装

```bash
# 安装依赖
sudo apt-get update
sudo apt-get install -y build-essential git cmake libx11-dev libxmu-dev libgl1-mesa-dev libglu1-mesa-dev libxt-dev libboost-all-dev

# 克隆AirSim仓库
git clone https://github.com/microsoft/AirSim.git
cd AirSim

# 编译（需要Unreal Engine 4.27+）
./setup.sh
./build.sh
```

### 2. 安装Python依赖

```bash
pip install airsim==1.6.0
```

### 3. 配置环境

确保`.env`文件中已配置DeepSeek API密钥：
```
DEEPSEEK_API_KEY=your_api_key_here
```

## 使用方法

### 启动AirSim仿真环境

1. 运行AirSim：
   - Windows：运行`run.bat`
   - Linux：运行`./run.sh`

2. 在AirSim中选择合适的场景（如City环境）

3. 确保AirSim处于运行状态（按F11进入飞行模式）

### 启动跟踪系统

```bash
python main.py
```

### 连接AirSim

1. 在UI界面点击"🚁 连接AirSim"按钮

2. 确认连接对话框：
   - 检查IP地址和端口是否正确
   - 确保AirSim正在运行
   - 点击"是"进行连接

3. 连接成功后：
   - 按钮变为红色"🚁 断开AirSim"
   - 系统自动开始从AirSim获取图像
   - 实时显示检测结果和跟踪信息

### 断开AirSim

点击"🚁 断开AirSim"按钮即可断开连接。

## 功能特性

### 1. 实时图像获取

- 从AirSim无人机摄像头实时获取图像流
- 支持30FPS帧率
- 自动处理图像格式转换（RGB → BGR）

### 2. 目标检测与跟踪

- 使用YOLOv8检测10种地面目标
- 使用ByteTrack进行多目标持续跟踪
- 实时估算目标距离

### 3. 智能决策

- 每30帧调用DeepSeek LLM进行分析
- 分析目标类型、距离、行为
- 提供飞行任务建议

### 4. 无人机控制（可选）

根据LLM分析结果，系统可以解析并执行以下控制指令：

- **飞向目标**："飞向ID X的XXX"
- **远离目标**："远离XXX"
- **设置高度**："保持X米高度"
- **调整高度**："上升X米" / "下降X米"
- **悬停**："悬停"

> 注意：默认情况下，无人机控制功能已禁用（`control_enabled: false`），仅输出控制日志。如需启用，请修改`config/config.yaml`。

## 配置文件说明

在`config/config.yaml`中添加的AirSim配置项：

```yaml
airsim:
  enabled: false           # 是否默认启用AirSim
  ip: "127.0.0.1"      # AirSim服务器IP地址
  port: 41451            # AirSim服务器端口
  camera_name: "0"        # 摄像头名称
  control_enabled: false   # 是否启用自动控制
```

### 配置参数说明

- **enabled**：是否在启动时自动连接AirSim（一般设为false，手动连接）
- **ip**：AirSim服务器IP地址（本地使用127.0.0.1，远程使用实际IP）
- **port**：AirSim RPC端口（默认41451）
- **camera_name**：摄像头名称（"0"为主摄像头，"1"为副摄像头）
- **control_enabled**：是否启用根据LLM决策自动控制无人机

## 模块说明

### utils/airsim_client.py

AirSim客户端封装类，提供以下功能：
- 连接/断开AirSim服务器
- 获取摄像头图像
- 获取无人机状态（位置、高度、姿态）
- 控制无人机移动、旋转、悬停

### utils/airsim_loader.py

AirSim图像流加载器，实现与VideoLoader相同的接口：
- 支持生成器模式（`__iter__`, `__next__`）
- 启动/停止图像流
- 自动处理图像格式

### utils/drone_controller.py

无人机控制模块，功能：
- 解析LLM分析文本中的控制指令
- 执行无人机控制动作
- 提供控制开关

## 故障排查

### 问题1：连接AirSim失败

**原因**：
- AirSim未启动
- 端口被占用
- 网络连接问题

**解决方案**：
1. 确保AirSim正在运行
2. 检查端口41451是否被占用
3. 尝试重启AirSim
4. 检查防火墙设置

### 问题2：图像获取失败

**原因**：
- 摄像头未启用
- 图像格式问题
- AirSim API调用超时

**解决方案**：
1. 在AirSim中启用摄像头视图
2. 检查AirSim日志
3. 增加超时时间

### 问题3：缺少AirSim依赖

**错误信息**：
```
ImportError: No module named 'airsim'
```

**解决方案**：
```bash
pip install airsim==1.6.0
```

### 问题4：控制指令未执行

**原因**：
- `control_enabled`设置为false
- LLM分析中未包含可识别的指令
- 指令解析失败

**解决方案**：
1. 检查配置文件中的`control_enabled`设置
2. 查看日志确认指令是否被解析
3. 检查LLM输出格式

## 性能优化建议

### 1. 降低图像分辨率

在AirSim中降低摄像头分辨率可以提升帧率：
- 默认：1280x720
- 推荐：640x480或800x600

### 2. 减少检测频率

修改`config/config.yaml`：
```yaml
llm:
  analyze_every: 60  # 从30改为60帧
```

### 3. 使用GPU加速

确保安装了CUDA版本的PyTorch：
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## 扩展功能

### 1. 多摄像头支持

修改`config/config.yaml`添加多个摄像头：
```yaml
airsim:
  cameras:
    - name: "0"  # 主摄像头
    - name: "1"  # 副摄像头
```

### 2. 深度信息融合

获取深度图用于更精确的距离估算：
```python
depth_image = client.get_camera_image("0", airsim.ImageType.DepthVis)
```

### 3. 轨迹记录

记录无人机飞行轨迹：
```python
trajectory = []
while running:
    state = client.get_drone_state()
    trajectory.append(state["position"])
```

## 安全注意事项

1. **控制安全**：启用自动控制前，确保在安全的仿真环境中测试
2. **高度限制**：代码中已限制高度范围（10-150米）
3. **碰撞检测**：使用AirSim的碰撞检测功能避免碰撞
4. **紧急停止**：点击"停止"按钮可立即停止所有操作

## 技术支持

如遇到问题，请：
1. 查看日志文件：`logs/`目录
2. 检查AirSim控制台输出
3. 参考AirSim官方文档：https://microsoft.github.io/AirSim/

## 更新日志

### v1.0.0 (2025-12-26)
- 初始版本
- 支持AirSim图像流获取
- 支持目标检测与跟踪
- 支持LLM智能分析
- 支持无人机控制（可选）
