#!/bin/bash
# send_text.sh — 发送纯文本消息到 Telegram
# 用法: bash send_text.sh <message>
#
# 环境变量（优先）或硬编码 fallback：
#   TG_BOT_TOKEN  — Telegram bot token
#   TG_CHAT_ID    — 目标 chat id

set -euo pipefail

MESSAGE="${1:-}"

if [[ -z "$MESSAGE" ]]; then
  echo "[send_text] ERROR: no message provided" >&2
  exit 1
fi

BOT_TOKEN="${TG_BOT_TOKEN:?Error: TG_BOT_TOKEN not set}"
CHAT_ID="${TG_CHAT_ID:-650773030}"

RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${MESSAGE}")

OK=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ok','false'))" 2>/dev/null || echo "false")

if [[ "$OK" == "True" ]] || [[ "$OK" == "true" ]]; then
  MSG_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['message_id'])" 2>/dev/null || echo "?")
  echo "[send_text] OK — message_id: $MSG_ID"
else
  echo "[send_text] FAILED — response: $RESPONSE" >&2
  exit 1
fi
