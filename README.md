# ComfyGram

> Telegram Bot for ComfyUI - AI-Powered Image Generation

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-azure.svg)](https://telegram.org/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-Support-orange.svg)](https://github.com/comfyanonymous/ComfyUI)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**[🇨🇳 中文文档](README_zh.md)** | [English](README.md)

ComfyGram is a powerful Telegram bot that provides a convenient interface to ComfyUI, enabling AI-powered image generation through intuitive Telegram commands. With support for multiple generation modes, advanced workflows, and seamless model management, ComfyGram brings professional-grade AI image generation to your fingertips.

## ✨ Key Features

### 🎨 Generation Modes
- **Text-to-Image**: Generate stunning images from text prompts using Flux models
- **Image-to-Image**: Transform existing images with style transfer and enhancement
- **Image-to-Video**: Convert images to animated videos using Wan models
- **IP-Adapter Integration**: Precise control over image composition and style

### 🤖 Advanced Workflows
- **Style Transfer**: Apply artistic styles to your images
- **Outfit Transfer**: Change clothing while maintaining pose and composition
- **Pose Transfer**: Apply poses from reference images
- **Multiple LoRA Support**: Blend multiple specialized models

### 📦 Model Management
- **Built-in LoRA Library**: Pre-configured LoRA models for various styles
- **Prompt Library**: Saved prompts for consistent results
- **Dynamic Loading**: Load models on-demand for efficiency
- **Version Control**: Track and manage model iterations

### ⚡ Performance
- **Asynchronous Processing**: Non-blocking image generation
- **Background Task Queue**: Process multiple requests simultaneously
- **Smart Polling**: Efficient monitoring of ComfyUI completion
- **Error Recovery**: Automatic retry mechanisms

### 🔧 Configuration
- **Environment-based Configuration**: Flexible setup with environment variables
- **macOS Integration**: LaunchAgent for automatic startup
- **Workspace Management**: Organized file structure
- **API Endpoints**: Configurable ComfyUI integration

## 🚀 Quick Start

### Prerequisites

Before installing ComfyGram, ensure you have:

- **Python 3.8+** with pip installed
- **ComfyUI** installed and running (default: `http://127.0.0.1:8000`)
- **Telegram Bot Token** from [@BotFather](https://t.me/botfather)
- **Telegram User ID** (get from [@userinfobot](https://t.me/userinfobot))

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/leoredrum/comfygram.git
   cd comfygram
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and fill in your configuration
   nano .env
   ```

   **Required variables:**
   ```env
   TG_BOT_TOKEN=your_telegram_bot_token_here
   TELEGRAM_ALLOWED_USER_ID=your_telegram_user_id_here
   IMAGECREATOR_WORKSPACE=/path/to/workspace
   COMFYUI_BASE_DIR=/path/to/comfyui
   COMFYUI_API_URL=http://127.0.0.1:8000
   ```

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

This creates a LaunchAgent that starts the bot on login and restarts it if it crashes.

## 📖 Detailed Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Telegram Configuration
TG_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALLOWED_USER_ID=123456789

# Paths Configuration
IMAGECREATOR_WORKSPACE=/Users/username/comfygram-workspace
COMFYUI_BASE_DIR=/Users/username/ComfyUI
COMFYUI_API_URL=http://127.0.0.1:8000

# Optional Settings
LOG_LEVEL=INFO
MAX_CONCURRENT_TASKS=3
ENABLE_NOTIFICATIONS=true
```

### ComfyUI Workflows

The bot includes pre-configured workflows in `workspace/workflows/`:

- **Text-to-Image (Flux)**: High-quality text-to-image generation
- **Image-to-Image with IP-Adapter**: Style transfer and enhancement
- **Style Transfer**: Apply artistic styles
- **Outfit Transfer**: Change clothing while maintaining pose
- **Image-to-Video (Wan)**: Convert images to animations

**Custom Workflows**: Add your own workflows to `workspace/workflows/` directory. Each workflow should be a JSON file compatible with ComfyUI.

## 🏗️ Architecture

### System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │───▶│  Task Queue    │───▶│  ComfyUI       │
│                 │    │                 │    │                 │
│ • Receives      │    │ • Stores tasks  │    │ • Executes      │
│ • Validates     │    │ • Manages state │    │ • Processes     │
│ • Notifies      │    │ • Handles retry │    │ • Generates     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │              ┌─────────────────┐    ┌─────────────────┐
         │              │   Polling      │    │   Output        │
         │              │   Service      │    │   Delivery      │
         │              │                 │    │                 │
         │              │ • Monitors     │    │ • Saves images  │
         │              │ • Collects     │    │ • Sends results │
         │              │ • Updates      │    │ • Cleanup       │
         │              └─────────────────┘    └─────────────────┘
```

### File Structure

```
comfygram/
├── README.md                    # This file
├── README_zh.md                 # Chinese documentation
├── LICENSE                      # MIT License
├── .env.example                 # Configuration template
├── requirements.txt             # Python dependencies
├── deploy.sh                    # Deployment script
├── workspace/                   # Main workspace
│   ├── bot/                     # Bot Python scripts
│   │   ├── tg_bot.py           # Main bot logic
│   │   ├── task_processor.py   # Task processing
│   │   └── polling_service.py  # Background polling
│   ├── workflows/               # ComfyUI workflow JSONs
│   │   ├── text_to_image.json  # Text-to-image workflow
│   │   ├── image_to_image.json # Image-to-image workflow
│   │   ├── style_transfer.json # Style transfer workflow
│   │   ├── outfit_transfer.json # Outfit transfer workflow
│   │   └── image_to_video.json # Image-to-video workflow
│   ├── configs/                 # Configuration files
│   │   ├── models.json         # Model configurations
│   │   ├── prompts.json        # Saved prompts
│   │   └── settings.json       # Bot settings
│   ├── docs/                    # Documentation
│   │   ├── INSTALLATION.md     # Installation guide
│   │   ├── USAGE.md           # Usage guide
│   │   ├── WORKFLOWS.md       # Workflow documentation
│   │   └── PIPELINE.md        # Architecture details
│   ├── inbox/                   # Input task queue
│   ├── outbox/                  # Generated images
│   ├── tmp/                     # Temporary files
│   └── logs/                    # Log files
├── config/                      # System configuration
│   └── *.plist.template         # macOS LaunchAgent templates
└── scripts/                     # Utility scripts
    ├── install-launchagent.sh   # Install macOS LaunchAgent
    ├── upgrade.sh               # Upgrade script
    └── backup.sh                # Backup script
```

## 📚 Usage Guide

### Basic Commands

Start a chat with your bot and use these commands:

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Show welcome message | `/start` |
| `/help` | Show help menu | `/help` |
| `/generate` | Generate image from text | `/generate beautiful landscape` |
| `/transform` | Transform existing image | `/transform style:anime` |
| `/video` | Create video from image | `/video duration:5` |
| `/models` | Show available LoRA models | `/models` |
| `/prompts` | Show saved prompts | `/prompts` |
| `/status` | Check bot status | `/status` |
| `/settings` | Show current settings | `/settings` |

### Advanced Usage

#### Text-to-Image Generation
```
/generate [prompt] [style] [quality] [steps]
```
- `prompt`: Text description of desired image
- `style`: Optional style (e.g., `anime`, `realistic`, `artistic`)
- `quality`: Quality setting (low, medium, high)
- `steps`: Number of inference steps (default: 20)

**Examples:**
```
/generate a beautiful sunset over mountains
/generate cyberpunk city style:anime quality:high
/generate portrait of woman steps:30
```

#### Image-to-Image Transformation
```
/transform [image] [type] [style] [strength]
```
- `image`: Send image or use reply
- `type`: Transformation type (`style`, `outfit`, `pose`)
- `style`: Style or target description
- `strength`: Transformation strength (0.1-1.0)

**Examples:**
```
/transform style:impressionist strength:0.7
/transform outfit:casual wear strength:0.5
```

#### Video Creation
```
/video [image] [duration] [style]
```
- `image`: Send image or use reply
- `duration`: Video duration in seconds
- `style`: Animation style (`smooth`, `dynamic`, `artistic`)

## 🔧 Installation Guide

### System Requirements

- **Operating System**: macOS 10.15+, Ubuntu 20.04+, or Windows 10+
- **Python**: 3.8 or higher
- **Memory**: 8GB RAM minimum (16GB recommended)
- **Storage**: 5GB free space
- **GPU**: Optional (NVIDIA recommended for faster generation)

### ComfyUI Installation

1. **Clone ComfyUI**
   ```bash
   git clone https://github.com/comfyanonymous/ComfyUI.git
   cd ComfyUI
   ```

2. **Install dependencies**
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   pip install -r requirements.txt
   ```

3. **Download models**
   ```bash
   # Create models directory
   mkdir models checkpoints
   
   # Download flux model
   wget https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev-fp8.safetensors -P checkpoints/
   ```

4. **Start ComfyUI**
   ```bash
   python server.py
   ```

### ComfyGram Installation

1. **Install ComfyGram**
   ```bash
   git clone https://github.com/leoredrum/comfygram.git
   cd comfygram
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Test installation**
   ```bash
   python workspace/bot/tg_bot.py --test
   ```

## 🚨 Troubleshooting

### Common Issues

#### Bot won't start
**Problem**: Bot fails to start with import errors
**Solution**: Ensure all dependencies are installed
```bash
pip install -r requirements.txt
```

#### ComfyUI connection fails
**Problem**: Cannot connect to ComfyUI
**Solution**: Check ComfyUI is running and URL is correct
```bash
curl http://127.0.0.1:8000
```

#### Image generation fails
**Problem**: Tasks fail to complete
**Solution**: Check logs and model availability
```bash
tail -f workspace/logs/bot.log
```

#### Permission denied
**Problem**: Cannot access workspace directories
**Solution**: Check directory permissions
```bash
chmod 755 workspace
chmod 644 workspace/inbox/*
```

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
./workspace/bot/tg_bot.py
```

### Performance Optimization

1. **Concurrent Tasks**: Adjust `MAX_CONCURRENT_TASKS` in environment
2. **Memory Management**: Monitor RAM usage during generation
3. **GPU Acceleration**: Ensure proper CUDA drivers are installed
4. **Model Caching**: Use SSD for faster model loading

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Add tests** if applicable
5. **Commit your changes** (`git commit -m 'Add amazing feature'`)
6. **Push to the branch** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

### Development Setup

```bash
# Clone the repository
git clone https://github.com/leoredrum/comfygram.git
cd comfygram

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to public functions
- Write unit tests for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - Powerful UI for Stable Diffusion
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [Black Forest Labs](https://huggingface.co/black-forest-labs) - Flux model development
- [Wan](https://github.com/modelscope/Wan) - Image-to-video technology

## 📮 Support

### Documentation
- [Installation Guide](workspace/docs/INSTALLATION.md)
- [Usage Guide](workspace/docs/USAGE.md)
- [Workflows Documentation](workspace/docs/WORKFLOWS.md)

### Getting Help
- **GitHub Issues**: [Report bugs and request features](https://github.com/leoredrum/comfygram/issues)
- **Discussions**: [Join community discussions](https://github.com/leoredrum/comfygram/discussions)
- **Telegram**: [Join our support group](https://t.me/comfygram_support)

### Community
- **Twitter**: [@comfygram_bot](https://twitter.com/comfygram_bot)
- **Discord**: [ComfyUI Community Server](https://discord.gg/comfyui)
- **YouTube**: [ComfyUI Tutorials](https://youtube.com/c/comfyui)

---

**Made with ❤️ by the ComfyGram team**