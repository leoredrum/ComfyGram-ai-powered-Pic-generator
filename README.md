# Imagecreator + Hermes Agent 备份

这是 `imagecreator` Telegram Bot 和 `Hermes Agent` 配置的完整备份，包含所有配置、脚本和工作流。

## 项目结构

```
imagecreator-backup/
├── deploy.sh                    # 一键部署脚本
├── scripts/
│   └── com.leo.imagecreator-bot.plist  # macOS LaunchAgent 配置
├── hermes-config/
│   ├── config.yaml              # Hermes 主配置
│   └── profiles/
│       └── imagecreator/       # Imagecreator Hermes profile
│           ├── config.yaml     # Profile 配置
│           ├── .env.template   # 环境变量模板（需要填入实际值）
│           ├── SOUL.md         # Agent 人设
│           ├── skills/         # Agent 技能
│           ├── platforms/      # 平台配置
│           └── ...             # 其他配置
└── imagecreator-workspace/
    ├── bin/                    # Python 脚本
    │   ├── tg_bot.py          # Telegram Bot 主程序
    │   ├── comfyui_client.py  # ComfyUI 客户端
    │   ├── convert_flux_lora.py  # LoRA 转换工具
    │   ├── poll_and_send.sh   # 轮询发送脚本
    │   ├── send_*.sh          # 发送脚本
    │   └── ...                # 其他工具脚本
    ├── workflows/              # ComfyUI API 工作流配置
    │   ├── flux_*.json        # Flux 模型工作流
    │   ├── wan_*.json         # Wan 模型工作流
    │   └── registry.json      # 工作流注册表
    ├── material_registry.json  # 材质注册表
    ├── lora_registry.json      # LoRA 注册表
    ├── *.md                    # 文档
    └── ...                     # 其他配置文件
```

## 快速部署

### 前提条件

1. **Hermes Agent** 已安装并配置
2. **ComfyUI** 已安装并运行在 `http://127.0.0.1:8000`
3. **Python 3** 和必要的依赖已安装

### 部署步骤

```bash
# 1. 克隆或解压此备份
git clone https://github.com/yourusername/imagecreator-backup.git
cd imagecreator-backup

# 2. 运行部署脚本
./deploy.sh
```

部署脚本会自动：
- 复制 Hermes 配置到 `~/.hermes/`
- 创建工作目录结构
- 复制所有脚本和配置文件
- 安装 LaunchAgent（macOS）

### 手动配置

部署完成后，需要手动配置：

1. **编辑环境变量**
   ```bash
   nano ~/.hermes/profiles/imagecreator/.env
   ```
   填入：
   - `IMAGECREATOR_BOT_TOKEN`: Telegram Bot Token
   - `IMAGECREATOR_SEND_TOKEN`: 辅助发送 Token
   - `TELEGRAM_ALLOWED_USERS`: 允许的 Telegram 用户 ID
   - `COMFYUI_BASE`: ComfyUI 地址
   - `COMFYUI_VENV`: ComfyUI 虚拟环境路径
   - `COMFYUI_BASE_DIR`: ComfyUI 根目录

2. **检查 LaunchAgent 配置**（macOS）
   ```bash
   nano ~/Library/LaunchAgents/com.leo.imagecreator-bot.plist
   ```
   确认 Python 路径正确：
   ```xml
   <string>/Users/YOUR_USER/Documents/ComfyUI/.venv/bin/python3</string>
   ```

3. **启动服务**
   ```bash
   # macOS
   launchctl start com.leo.imagecreator-bot

   # 或手动运行（用于调试）
   cd ~/Agents/imagecreator-workspace
   python3 bin/tg_bot.py
   ```

## 目录说明

### Hermes 配置 (`hermes-config/`)

- **config.yaml**: Hermes 主配置，包含模型、终端、内存等设置
- **profiles/imagecreator/**: Imagecreator 专用的 Hermes profile
  - 包含 Agent 人设（SOUL.md）
  - 技能（skills/）
  - 平台配置（platforms/）
  - 环境变量（.env）

### 工作区 (`imagecreator-workspace/`)

#### `bin/` - 核心脚本

- **tg_bot.py**: Telegram Bot 主程序，处理消息和任务调度
- **comfyui_client.py**: ComfyUI API 客户端
- **convert_flux_lora.py**: Flux LoRA 格式转换工具
- **poll_and_send.sh**: 轮询并发送结果的 shell 脚本
- **send_photo.sh / send_video.sh / send_text.sh**: 发送不同类型内容的脚本
- **update_prompts.py**: 更新提示词库
- **rebuild_material_registry.py**: 重建材质注册表
- **lora_scan.py**: 扫描 LoRA 文件
- **auto_mask.py**: 自动生成掩码
- **wd14_standalone.py**: WD14 标注工具

#### `workflows/` - ComfyUI 工作流

- **Flux 工作流**:
  - `flux_t2i_api.json`: 文本生图
  - `flux_i2i_*.json`: 各种图像到图像任务（人像、风格、调色、水印等）
  - `flux_anime_t2i_api.json`: 动漫风格文生图
- **Wan 工作流**:
  - `wan_i2v.json`: 图像生视频
  - `wan_i2v_undress_api.json`: 特殊应用
- **Dual Transfer**:
  - `dual_transfer_pose_api.json`: 双图迁移 - 姿态步骤
- **registry.json**: 工作流注册表，定义可用的工作流

#### 配置文件

- **material_registry.json**: 材质库，包含各种标签和权重
- **lora_registry.json**: LoRA 模型注册表
- **preset_prompt_templates.json**: 预设提示词模板
- **curated_prompt_banks.json**: 精选提示词库
- **qpipi_tags.json**: Qpipi 标签字库
- **prompt_library.json**: 提示词库
- **user_custom_prompts.json**: 用户自定义提示词

#### 文档

- **AGENTS.md**: Agent 说明文档
- **PIPELINE.md**: 处理流水线说明
- **TOOLS.md**: 工具说明
- **IDENTITY.md / SOUL.md / USER.md / HEARTBEAT.md**: Agent 人设相关
- **HANDOFF-*.md**: 交接文档
- **BOOTSTRAP.md**: 启动说明

## 运行时目录（不包含在备份中）

以下目录会在首次运行时自动创建：

- `inbox/`: 待处理的输入文件
- `outbox/`: 已处理的输出文件
- `tmp/`: 临时文件和日志
- `logs/`: 运行日志
- `media/`: 媒体文件缓存

## 运维命令

### 查看日志

```bash
# Bot 日志
tail -f ~/Agents/imagecreator-workspace/tmp/imagecreator-bot.log

# 错误日志
tail -f ~/Agents/imagecreator-workspace/tmp/imagecreator-bot.err.log
```

### 服务管理

```bash
# macOS LaunchAgent
launchctl start com.leo.imagecreator-bot    # 启动
launchctl stop com.leo.imagecreator-bot     # 停止
launchctl unload ~/Library/LaunchAgents/com.leo.imagecreator-bot.plist  # 卸载
launchctl load ~/Library/LaunchAgents/com.leo.imagecreator-bot.plist    # 重新加载
```

### 手动测试

```bash
# 直接运行 Bot（调试模式）
cd ~/Agents/imagecreator-workspace
python3 bin/tg_bot.py

# 测试发送脚本
./bin/send_text.sh "Hello World"
./bin/send_photo.sh /path/to/image.jpg
```

## 技术栈

- **Hermes Agent**: AI Agent 框架
- **Python 3**: 主要编程语言
- **ComfyUI**: 图像生成和视频生成后端
- **Telegram Bot API**: 消息接收和发送
- **Flux / Wan**: AI 模型（通过 ComfyUI）
- **macOS LaunchAgent**: 服务守护进程

## 注意事项

1. **敏感信息**: `.env` 文件包含 API Token，已替换为 `.env.template`，部署后需要填入实际值
2. **路径依赖**: 部署脚本会替换路径中的 `/Users/leo` 为当前用户，但 Python 路径需要手动确认
3. **ComfyUI 依赖**: 确保 ComfyUI 已安装并正常运行
4. **权限**: 部署后可能需要设置脚本可执行权限：`chmod +x ~/Agents/imagecreator-workspace/bin/*.sh`

## 备份说明

此备份包含：
- ✅ 所有配置文件
- ✅ 所有脚本代码
- ✅ 所有工作流定义
- ✅ 所有注册表和库文件
- ✅ 文档和说明

不包含（会在运行时自动生成）：
- ❌ 运行时数据
- ❌ 日志文件
- ❌ 临时文件
- ❌ 缓存文件
- ❌ Session 数据
- ❌ API Token（需要手动配置）

## 故障排查

### Bot 无法启动

```bash
# 检查 ComfyUI 是否运行
curl http://127.0.0.1:8000/system_stats

# 检查 Python 环境
which python3
python3 --version

# 手动运行查看错误
cd ~/Agents/imagecreator-workspace
python3 bin/tg_bot.py
```

### LaunchAgent 问题

```bash
# 查看服务状态
launchctl list | grep imagecreator

# 查看服务日志
log show --predicate 'process == "imagecreator-bot"' --last 1h
```

### 权限问题

```bash
# 确保脚本可执行
chmod +x ~/Agents/imagecreator-workspace/bin/*.sh

# 确保目录可写
chmod -R 755 ~/Agents/imagecreator-workspace
```

## License

MIT

## 联系方式

如有问题，请联系 leoredrum
