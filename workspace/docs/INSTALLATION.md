# ComfyGram 安装教程

本文档提供 ComfyGram 的详细安装指南。

## 目录

- [系统要求](#系统要求)
- [安装 ComfyUI](#安装-comfyui)
- [安装 ComfyGram](#安装-comfygram)
- [配置](#配置)
- [验证安装](#验证安装)
- [故障排除](#故障排除)

---

## 系统要求

### 最低配置

| 组件 | 要求 |
|------|------|
| 操作系统 | Linux / macOS 10.15+ / Windows 10+ (WSL2) |
| Python | 3.8 或更高 |
| 内存 | 8 GB RAM |
| 显存 | 4 GB VRAM |
| 存储 | 20 GB 可用空间 |

### 推荐配置

| 组件 | 要求 |
|------|------|
| 操作系统 | Ubuntu 22.04 / macOS 13+ |
| Python | 3.10 |
| 内存 | 16 GB RAM |
| 显存 | 8 GB+ VRAM |
| 存储 | 50 GB+ SSD |

---

## 安装 ComfyUI

ComfyUI 是 ComfyGram 的核心图像生成引擎，必须先安装。

### 步骤 1：克隆 ComfyUI

```bash
# 克隆仓库
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# 或使用镜像（如果 GitHub 访问慢）
git clone https://gitee.com/mirrors/ComfyUI.git
cd ComfyUI
```

### 步骤 2：创建虚拟环境

```bash
# 创建 Python 虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate       # Linux/macOS
# 或
venv\Scripts\activate          # Windows
```

### 步骤 3：安装依赖

```bash
# 安装 PyTorch（根据你的系统选择）
# Linux/Windows with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# macOS with MPS (Apple Silicon)
pip install torch torchvision torchaudio

# 安装 ComfyUI 依赖
pip install -r requirements.txt
```

### 步骤 4：下载模型

#### 方式 A：手动下载

1. 访问 [Hugging Face](https://huggingface.co/models)
2. 搜索并下载模型：
   - Flux.1-dev
   - SDXL Turbo
   - 或其他 Stable Diffusion 模型
3. 将模型文件放置在：
   - `models/checkpoints/` - 主模型
   - `models/loras/` - LoRA 模型
   - `models/vae/` - VAE 模型

#### 方式 B：使用下载脚本

```bash
# 创建下载脚本
cat > download_models.sh << 'SCRIPT'
#!/bin/bash
cd ComfyUI/models

# 创建目录
mkdir -p checkpoints clip vae loras

# 下载 SDXL Turbo（示例）
wget https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sdxl_turbo.safetensors \
  -O checkpoints/sdxl_turbo.safetensors

SCRIPT

# 运行脚本
chmod +x download_models.sh
./download_models.sh
```

### 步骤 5：启动 ComfyUI

```bash
# 在 ComfyUI 目录中
python main.py --listen 127.0.0.1 --port 8000
```

验证：打开浏览器访问 http://127.0.0.1:8000

---

## 安装 ComfyGram

### 步骤 1：克隆 ComfyGram

```bash
# 克隆仓库
git clone https://github.com/leoredrum/ComfyGram-ai-powered-Pic-generator.git
cd ComfyGram-ai-powered-Pic-generator
```

### 步骤 2：安装 Python 依赖

```bash
# 使用系统的 pip
pip install -r requirements.txt

# 或使用虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 步骤 3：配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
nano .env
# 或使用其他编辑器：vim .env, code .env
```

**必需配置：**

```bash
# Telegram Bot 配置
TG_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_ALLOWED_USER_ID=123456789

# ComfyUI 配置
COMFYUI_API_URL=http://127.0.0.1:8000
COMFYUI_BASE_DIR=/path/to/ComfyUI

# 工作区配置
IMAGECREATOR_WORKSPACE=./workspace
```

**获取配置值：**

1. **TG_BOT_TOKEN**:
   - 在 Telegram 中找到 [@BotFather](https://t.me/BotFather)
   - 发送 `/newbot`
   - 按提示设置机器人名称
   - 保存返回的 token

2. **TELEGRAM_ALLOWED_USER_ID**:
   - 在 Telegram 中找到 [@userinfobot](https://t.me/userinfobot)
   - 发送任意消息
   - 保存返回的数字 ID

### 步骤 4：创建工作区

```bash
# 创建必要的目录
mkdir -p workspace/inbox
mkdir -p workspace/outbox
mkdir -p workspace/tmp
mkdir -p workspace/logs
```

---

## 配置

### ComfyUI 模型配置

编辑 `workspace/configs/material_registry.json`：

```json
{
  "models": {
    "flux": {
      "file": "flux1-dev.safetensors",
      "type": "checkpoint"
    },
    "sdxl": {
      "file": "sdxl_turbo.safetensors",
      "type": "checkpoint"
    }
  }
}
```

### LoRA 配置

编辑 `workspace/configs/lora_registry.json`：

```json
{
  "loras": {
    "anime_style": {
      "file": "anime_lora.safetensors",
      "strength": 0.8,
      "trigger_word": "anime_style"
    }
  }
}
```

---

## 验证安装

### 1. 测试 ComfyUI 连接

```bash
curl http://127.0.0.1:8000/system_stats
```

应该返回 JSON 格式的系统信息。

### 2. 测试 ComfyGram 配置

```bash
cd /path/to/ComfyGram-ai-powered-Pic-generator
python workspace/bot/tg_bot.py --check-config
```

### 3. 启动 ComfyGram

```bash
./workspace/bot/tg_bot.py
```

### 4. 在 Telegram 中测试

1. 打开你的机器人
2. 发送 `/start`
3. 应该收到欢迎消息

---

## 故障排除

### ComfyUI 无法启动

**问题**: `ModuleNotFoundError: No module named 'torch'`

**解决**: 
```bash
pip install torch torchvision torchaudio
```

**问题**: `CUDA out of memory`

**解决**:
- 减小图像尺寸
- 使用更小的模型
- 关闭其他占用显存的程序

### ComfyGram 无法连接到 ComfyUI

**问题**: `Connection refused`

**解决**:
1. 确认 ComfyUI 正在运行：`curl http://127.0.0.1:8000/system_stats`
2. 检查 `.env` 中的 `COMFYUI_API_URL`
3. 检查防火墙设置

### Telegram Bot 无响应

**问题**: Bot 读取消息但不回复

**解决**:
1. 检查 bot token 是否正确
2. 验证 `TELEGRAM_ALLOWED_USER_ID`
3. 查看日志：`tail -f workspace/tmp/comfygram-bot.log`

---

## 下一步

安装完成后，查看：

- [使用教程](USAGE.md)
- [工作流配置](WORKFLOWS.md)
- [API 文档](API.md)
