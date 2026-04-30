#!/bin/bash

# Imagecreator + Hermes Agent 部署脚本
# 使用方法: ./deploy.sh

set -e

echo "🚀 开始部署 Imagecreator..."

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 配置
HERMES_DIR="$HOME/.hermes"
WORKSPACE_DIR="$HOME/Agents/imagecreator-workspace"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}📁 仓库目录: $REPO_DIR${NC}"

# 检查 Hermes 是否已安装
if [ ! -d "$HERMES_DIR" ]; then
    echo -e "${RED}❌ Hermes 未安装，请先安装 Hermes Agent${NC}"
    exit 1
fi

# 创建工作目录
echo -e "${GREEN}📂 创建工作目录...${NC}"
mkdir -p "$WORKSPACE_DIR"
mkdir -p "$WORKSPACE_DIR/inbox"
mkdir -p "$WORKSPACE_DIR/outbox"
mkdir -p "$WORKSPACE_DIR/tmp"

# 复制文件
echo -e "${GREEN}📋 复制配置文件...${NC}"

# Hermes 配置
if [ -f "$REPO_DIR/hermes-config/config.yaml" ]; then
    cp "$REPO_DIR/hermes-config/config.yaml" "$HERMES_DIR/config.yaml"
    echo "✓ 已更新 Hermes 主配置"
fi

# Imagecreator profile
mkdir -p "$HERMES_DIR/profiles/imagecreator"
cp -r "$REPO_DIR/hermes-config/profiles/imagecreator/"* "$HERMES_DIR/profiles/imagecreator/"
echo "✓ 已复制 imagecreator profile"

# 工作区文件
cp -r "$REPO_DIR/imagecreator-workspace/bin" "$WORKSPACE_DIR/"
cp -r "$REPO_DIR/imagecreator-workspace/workflows" "$WORKSPACE_DIR/"
cp "$REPO_DIR/imagecreator-workspace"/*.json "$WORKSPACE_DIR/"
cp "$REPO_DIR/imagecreator-workspace"/*.md "$WORKSPACE_DIR/"
echo "✓ 已复制工作区文件"

# 环境变量配置
if [ ! -f "$HERMES_DIR/profiles/imagecreator/.env" ]; then
    if [ -f "$REPO_DIR/hermes-config/profiles/imagecreator/.env.template" ]; then
        cp "$REPO_DIR/hermes-config/profiles/imagecreator/.env.template" "$HERMES_DIR/profiles/imagecreator/.env"
        echo -e "${YELLOW}⚠️  请编辑 .env 文件填入正确的配置${NC}"
    fi
fi

# LaunchAgent 安装（仅 macOS）
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${GREEN}🔧 安装 LaunchAgent...${NC}"

    # 更新 plist 文件中的路径
    PLIST_FILE="$HOME/Library/LaunchAgents/com.leo.imagecreator-bot.plist"

    if [ -f "$REPO_DIR/scripts/com.leo.imagecreator-bot.plist" ]; then
        # 替换路径
        sed "s|/Users/leo|/Users/$USER|g" "$REPO_DIR/scripts/com.leo.imagecreator-bot.plist" > "$PLIST_FILE"

        # 更新 Python 路径（需要用户确认）
        echo -e "${YELLOW}⚠️  请检查 LaunchAgent 中的 Python 路径是否正确: $PLIST_FILE${NC}"
        echo -e "默认路径: /Users/$USER/Documents/ComfyUI/.venv/bin/python3"

        # 卸载旧的服务（如果存在）
        launchctl unload "$PLIST_FILE" 2>/dev/null || true

        # 加载新服务
        launchctl load "$PLIST_FILE"

        echo -e "${GREEN}✓ LaunchAgent 已安装${NC}"
    fi
fi

# 设置脚本可执行权限
chmod +x "$WORKSPACE_DIR/bin"/*.sh 2>/dev/null || true
chmod +x "$WORKSPACE_DIR/bin"/*.py 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ 部署完成！${NC}"
echo ""
echo -e "${YELLOW}📝 后续步骤:${NC}"
echo "1. 编辑 $HERMES_DIR/profiles/imagecreator/.env 填入正确的配置"
echo "2. 确保已安装 ComfyUI 并运行在 http://127.0.0.1:8000"
echo "3. 更新 LaunchAgent 中的 Python 路径（如需要）"
echo "4. 启动服务：launchctl start com.leo.imagecreator-bot"
echo ""
echo -e "${YELLOW}📚 参考:${NC}"
echo "- Hermes 配置: $HERMES_DIR"
echo "- 工作区: $WORKSPACE_DIR"
echo "- 日志: $WORKSPACE_DIR/tmp/"
