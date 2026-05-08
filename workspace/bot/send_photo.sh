#!/bin/bash
# send_photo.sh — 把生成图片回传给 Telegram
# 用法: bash send_photo.sh <file_path> <caption>
#
# 环境变量（优先）或硬编码 fallback：
#   TG_BOT_TOKEN  — Telegram bot token
#   TG_CHAT_ID    — 目标 chat id

set -euo pipefail

FILE="${1:-}"
CAPTION="${2:-imagecreator output}"

if [[ -z "$FILE" ]]; then
  echo "[send_photo] ERROR: no file path provided" >&2
  exit 1
fi

if [[ ! -f "$FILE" ]]; then
  echo "[send_photo] ERROR: file not found: $FILE" >&2
  exit 1
fi

BOT_TOKEN="${TG_BOT_TOKEN:?Error: TG_BOT_TOKEN not set}"
CHAT_ID="${TG_CHAT_ID:-650773030}"

RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto" \
  -F "chat_id=${CHAT_ID}" \
  -F "photo=@${FILE}" \
  -F "caption=${CAPTION}")

OK=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ok','false'))" 2>/dev/null || echo "false")

if [[ "$OK" == "True" ]] || [[ "$OK" == "true" ]]; then
  MSG_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['message_id'])" 2>/dev/null || echo "?")
  echo "[send_photo] OK — message_id: $MSG_ID"
else
  echo "[send_photo] FAILED — response: $RESPONSE" >&2
  exit 1
fi
