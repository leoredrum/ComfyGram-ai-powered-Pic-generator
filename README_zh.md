# ComfyGram - ComfyUI AI 图像生成 Telegram 机器人

<div align="center">

[![许可协议: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Telegram 机器人](https://img.shields.io/badge/telegram-bot-blue.svg)](https://core.telegram.org/bots)

**强大的 Telegram 机器人，将 ComfyUI 的 AI 图像生成功能带到你的聊天中**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [安装指南](#-安装指南) • [使用教程](#-使用教程) • [配置说明](#-配置说明)

[English](README.md) | [获取支持](https://github.com/leoredrum/ComfyGram-ai-powered-Pic-generator/issues)

</div>

---

## ✨ 功能特性

### 🎨 多种生成模式
- **文生图**：使用 Flux、SDXL 等模型从文字描述生成图像
- **图生图**：转换和增强现有图像
- **图生视频**：使用 Wan 模型将图像转换为视频
- **风格迁移**：为图像应用艺术风格
- **IP-Adapter**：参考图像引导，实现精确控制
- **换装**：改变图像中人物的服装

### 🤖 高级工作流
- 预配置的 ComfyUI 工作流
- 通过 JSON 配置自定义工作流
- 批处理功能
- 异步任务队列，非阻塞操作

### 📦 资产管理
- 内置 LoRA 模型注册表
- 精选提示词库
- 材质注册表，组织有序
- 动态模型加载和缓存

### ⚡ 性能优化
- 异步处理架构
- 智能任务队列管理
- 后台轮询结果交付
- 自动清理临时文件

### 🔧 灵活配置
- 基于环境变量的配置
- 支持多个 ComfyUI 实例
- 可自定义机器人命令和响应
- macOS LaunchAgent 集成，自动启动

---

## 🚀 快速开始

### 前置要求

1. **已安装并运行 ComfyUI** - 访问 http://127.0.0.1:8000
2. **Python 3.8+**
3. **Telegram Bot Token** - 从 [@BotFather](https://t.me/botfather) 获取
4. **你的 Telegram User ID** - 从 [@userinfobot](https://t.me/userinfobot) 获取

### 5 分钟快速安装

```bash
# 1. 克隆仓库
git clone https://github.com/leoredrum/ComfyGram-ai-powered-Pic-generator.git
cd ComfyGram-ai-powered-Pic-generator

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
nano .env  # 填写你的 token 和 user ID

# 4. 创建工作区
mkdir -p workspace/{inbox,outbox,tmp}

# 5. 运行机器人
./workspace/bot/tg_bot.py

# 6. 在 Telegram 中测试
# 打开你的机器人，发送 /start
```

**就这么简单！** 🎉

---

## 📖 详细安装指南

### 方法 1：手动安装（推荐新手）

<details>
<summary><b>点击展开详细步骤</b></summary>

#### 步骤 1：安装 ComfyUI

```bash
# 下载 ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 下载模型（可选）
# 将模型文件放在 models/checkpoints/ 目录

# 启动 ComfyUI
python main.py --listen 127.0.0.1 --port 8000
```

#### 步骤 2：安装 ComfyGram

```bash
# 克隆 ComfyGram
git clone https://github.com/leoredrum/ComfyGram-ai-powered-Pic-generator.git
cd ComfyGram-ai-powered-Pic-generator

# 安装 Python 依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 必需配置
TG_BOT_TOKEN=你的_bot_token_从BotFather获取
TELEGRAM_ALLOWED_USER_ID=你的数字用户ID

# 可选配置（使用默认值）
IMAGECREATOR_WORKSPACE=./workspace
COMFYUI_BASE_DIR=/path/to/ComfyUI
COMFYUI_API_URL=http://127.0.0.1:8000
```

#### 步骤 3：验证安装

```bash
# 检查 ComfyUI 是否运行
curl http://127.0.0.1:8000/system_stats

# 运行 ComfyGram
./workspace/bot/tg_bot.py
```

</details>

### 方法 2：macOS 自动启动（LaunchAgent）

<details>
<summary><b>点击展开 macOS 配置</b></summary>

```bash
# 复制配置文件
cp config/com.github.comfygram.bot.plist.template \
   ~/Library/LaunchAgents/com.github.comftygram.bot.plist

# 编辑路径（如果需要）
nano ~/Library/LaunchAgents/com.github.comftygram.bot.plist

# 加载服务
launchctl load ~/Library/LaunchAgents/com.github.comftygram.bot.plist

# 启动服务
launchctl start com.github.comftygram.bot

# 查看日志
tail -f ~/comfygram/workspace/tmp/comfygram-bot.log
```

</details>

---

## 📚 使用教程

### 基础命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/start` | 初始化机器人 | `/start` |
| `/help` | 显示帮助 | `/help` |
| `/t2i <提示词>` | 文生图 | `/t2i 一只可爱的猫` |
| `/i2i` | 图生图 | 发图 + `/i2i` |
| `/style <风格>` | 风格迁移 | `/style 油画` |
| `/status` | 查看状态 | `/status` |

### 使用示例

**示例 1：简单文生图**
```
你: /t2i 美丽日落，山峦，温暖阳光，写实照片
Bot: [生成图像]
Bot: ✅ 完成！[发送图像]
```

**示例 2：风格迁移**
```
你: [发送照片]
你: /style 动漫风格
Bot: [转换为动漫风格]
```

**示例 3：批量生成**
```
你: /t2i 赛博朋克城市
你: --batch 4
Bot: [生成 4 张不同变体]
```

---

## ⚙️ 配置说明

### 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `TG_BOT_TOKEN` | ✅ | Telegram bot token |
| `TELEGRAM_ALLOWED_USER_ID` | ✅ | 允许使用的用户 ID |
| `COMFYUI_API_URL` | 否 | ComfyUI 地址（默认：http://127.0.0.1:8000） |
| `IMAGECREATOR_WORKSPACE` | 否 | 工作区路径（默认：./workspace） |

### 模型下载

**Flux 模型（推荐）：**
```bash
cd ComfyUI/models
mkdir -p flux clip

# 下载 Flux
wget https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors \
  -O flux/flux1-dev.safetensors

# 下载 CLIP
wget https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors \
  -O clip/clip_l.safetensors
```

---

## 🔧 常见问题

<details>
<summary><b>机器人无响应？</b></summary>

**检查清单：**
1. ComfyUI 是否正在运行？
   ```bash
   curl http://127.0.0.1:8000/system_stats
   ```

2. Bot token 是否正确？
   ```bash
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
   ```

3. 查看日志
   ```bash
   tail -f workspace/tmp/comfygram-bot.log
   ```
</details>

<details>
<summary><b>生成失败或很慢？</b></summary>

**解决方案：**
- 减少图像尺寸
- 减少生成步数
- 关闭其他占用显存的程序
- 检查模型是否正确下载
</details>

---

## 📖 更多文档

- [完整安装教程](workspace/docs/INSTALLATION.md)
- [详细使用指南](workspace/docs/USAGE.md)
- [工作流配置](workspace/docs/WORKFLOWS.md)

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- 所有贡献者

---

<div align="center">

**用 ❤️ 制作**

[⬆ 返回顶部](#comfygram---comfyui-ai-图像生成-telegram-机器人)

</div>
