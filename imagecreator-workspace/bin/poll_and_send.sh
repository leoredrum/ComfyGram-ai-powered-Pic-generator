#!/bin/bash
# poll_and_send.sh — Background polling + Telegram delivery
# Usage: bash poll_and_send.sh <task_json_path> <prompt_id> <workflow> <prompt_text>
# Run via: bash -c 'nohup bash poll_and_send.sh ... > /tmp/poll_<id>.log 2>&1 &'

set -euo pipefail

WORKSPACE="/Users/leo/Agents/imagecreator-workspace"
TASK_PATH="${1:-}"
PROMPT_ID="${2:-}"
WORKFLOW="${3:-t2i}"
PROMPT_TEXT="${4:-}"

# 视频workflow需要更多时间
IS_VIDEO=false
case "$WORKFLOW" in i2v|i2v_undress|svd_i2v) IS_VIDEO=true ;; esac

if [[ "$IS_VIDEO" == "true" ]]; then
  MAX_POLLS=60  # 60 × (60s poll + 30s sleep) = ~90 minutes max
else
  MAX_POLLS=20  # 20 × (60s poll + 30s sleep) = ~30 minutes max
fi

# 根据workflow选择媒体类型标签和发送脚本
if [[ "$IS_VIDEO" == "true" ]]; then
  MEDIA_LABEL="视频"
  SEND_MEDIA_SCRIPT="$WORKSPACE/bin/send_video.sh"
else
  MEDIA_LABEL="图片"
  SEND_MEDIA_SCRIPT="$WORKSPACE/bin/send_photo.sh"
fi

if [[ -z "$TASK_PATH" || -z "$PROMPT_ID" ]]; then
  echo "[poll_and_send] ERROR: task_path and prompt_id required" >&2
  exit 1
fi

TASK_ID=$(basename "$TASK_PATH" .json)

# 1. Send "processing" ack immediately
bash "$WORKSPACE/bin/send_text.sh" "🎨 ${MEDIA_LABEL}生成中
agent: imagecreator
workflow: ${WORKFLOW}
prompt_id: ${PROMPT_ID}
prompt: ${PROMPT_TEXT}
status: processing"

echo "[poll_and_send] Starting background poll for $PROMPT_ID"

for i in $(seq 1 $MAX_POLLS); do
  echo "[poll_and_send] Poll attempt $i of $MAX_POLLS..."

  # Capture stdout only (stderr goes to nohup log); take last line = JSON
  result=$(python3 "$WORKSPACE/bin/comfyui_client.py" \
    --task "$TASK_PATH" \
    --poll "$PROMPT_ID" 2>/dev/null | tail -1)
  [[ -z "$result" ]] && result='{"status":"error","error":"no output from client"}'

  echo "[poll_and_send] Poll result: $result"

  status=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','error'))" 2>/dev/null || echo "error")

  if [[ "$status" == "completed" ]]; then
    output_file=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('outputs',[])[0] if d.get('outputs') else '')" 2>/dev/null || echo "")

    if [[ -n "$output_file" && -f "$output_file" ]]; then
      filename=$(basename "$output_file")
      echo "[poll_and_send] Generation complete: $output_file"
      CAPTION="✅ ${MEDIA_LABEL}生成完成
agent: imagecreator
workflow: ${WORKFLOW}
prompt_id: ${PROMPT_ID}
file: ${filename}"
      bash "$SEND_MEDIA_SCRIPT" "$output_file" "$CAPTION"
      echo "[poll_and_send] Done."
      exit 0
    else
      echo "[poll_and_send] ERROR: No output file in result" >&2
      bash "$WORKSPACE/bin/send_text.sh" "❌ ${MEDIA_LABEL}生成失败
agent: imagecreator
workflow: ${WORKFLOW}
prompt_id: ${PROMPT_ID}
error: no output file returned" || true
      exit 1
    fi

  elif [[ "$status" == "pending" ]]; then
    echo "[poll_and_send] Still running, waiting 30s before next poll..."
    sleep 30

  else
    error_msg=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error','unknown error'))" 2>/dev/null || echo "unknown error")
    echo "[poll_and_send] ERROR: status=$status error=$error_msg" >&2
    bash "$WORKSPACE/bin/send_text.sh" "❌ ${MEDIA_LABEL}生成失败
agent: imagecreator
workflow: ${WORKFLOW}
prompt_id: ${PROMPT_ID}
error: ${error_msg}" || true
    exit 1
  fi
done

echo "[poll_and_send] TIMEOUT: $MAX_POLLS polls exhausted" >&2
bash "$WORKSPACE/bin/send_text.sh" "⏰ ${MEDIA_LABEL}生成超时
agent: imagecreator
workflow: ${WORKFLOW}
prompt_id: ${PROMPT_ID}
error: exceeded ${MAX_POLLS} poll attempts" || true
exit 1
