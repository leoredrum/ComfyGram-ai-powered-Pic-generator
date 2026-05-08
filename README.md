# ComfyGram

> Telegram Bot for ComfyUI - AI-Powered Image Generation

ComfyGram is a Telegram bot that provides a convenient interface to ComfyUI, 
enabling AI-powered image generation through Telegram messages.

## ✨ Features

- 🎨 **Multiple Generation Modes**: Text-to-Image, Image-to-Image, Image-to-Video
- 🤖 **Advanced Workflows**: IP-Adapter, style transfer, outfit transfer
- 📦 **Model Management**: Built-in LoRA and prompt library management
- ⚡ **Asynchronous Processing**: Non-blocking image generation
- 🔧 **Flexible Configuration**: Environment-based configuration

## 🚀 Quick Start

### Prerequisites

- **ComfyUI** installed and running (default: `http://127.0.0.1:8000`)
- **Python 3.8+** with required dependencies
- **Telegram Bot Token** from [@BotFather](https://t.me/botfather)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/leoredrum/comfygram.git
   cd comfygram
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and fill in your configuration
   ```

   Required variables:
   - `TG_BOT_TOKEN`: Your Telegram bot token
   - `TELEGRAM_ALLOWED_USER_ID`: Your Telegram user ID
   - `IMAGECREATOR_WORKSPACE`: Workspace directory path
   - `COMFYUI_BASE_DIR`: ComfyUI installation path

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the bot**
   ```bash
   ./workspace/bot/tg_bot.py
   ```

### macOS LaunchAgent Setup

For automatic startup on macOS:

```bash
./scripts/install-launchagent.sh
```

## 📖 Configuration

### Environment Variables

See [.env.example](.env.example) for all available configuration options.

Key variables:
- `TG_BOT_TOKEN`: Telegram bot authentication token
- `TELEGRAM_ALLOWED_USER_ID`: Authorized user ID (get from [@userinfobot](https://t.me/userinfobot))
- `IMAGECREATOR_WORKSPACE`: Path to workspace directory
- `COMFYUI_BASE_DIR`: Path to ComfyUI installation
- `COMFYUI_API_URL`: ComfyUI API endpoint

### ComfyUI Workflows

The bot includes pre-configured workflows for:
- Text-to-Image (Flux)
- Image-to-Image with IP-Adapter
- Style Transfer
- Outfit Transfer
- Image-to-Video (Wan)

Custom workflows can be added to `workspace/workflows/`.

## 🏗️ Architecture

ComfyGram uses an asynchronous task pipeline:

1. **Task Reception**: Telegram messages → inbox/
2. **Processing**: ComfyUI executes workflows
3. **Polling**: Background script monitors completion
4. **Delivery**: Results sent via Telegram

See [workspace/docs/PIPELINE.md](workspace/docs/PIPELINE.md) for details.

## 📁 Project Structure

```
comfygram/
├── README.md              # This file
├── .env.example           # Configuration template
├── deploy.sh              # Deployment script
├── workspace/             # Main workspace
│   ├── bot/              # Bot Python scripts
│   ├── workflows/        # ComfyUI workflow JSONs
│   ├── configs/          # Configuration files
│   ├── docs/             # Documentation
│   ├── inbox/            # Input task queue
│   ├── outbox/           # Generated images
│   └── tmp/              # Temporary files
├── config/               # System configuration
│   └── *.plist.template  # macOS LaunchAgent templates
└── scripts/              # Utility scripts
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - Powerful UI for Stable Diffusion
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper

## 📮 Support

For issues and questions, please use [GitHub Issues](https://github.com/leoredrum/comfygram/issues).
