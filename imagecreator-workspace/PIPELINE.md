# ImageCreator Pipeline — Fixed Protocol

## Overview

```
Telegram 入站 → main → imagecreator subagent → ComfyUI → background poller → Telegram 出站
```

All generation is asynchronous. imagecreator returns in < 30 seconds; the image arrives on Telegram 3–10 minutes later.

---

## Step-by-Step Protocol

### Step 0 — Health check (optional, skip if ComfyUI known online)
```bash
curl -s http://localhost:8000/system_stats
```

### Step 1 — Write task JSON to inbox
```bash
write: /Users/leo/Agents/imagecreator-workspace/inbox/<task_id>.json
content: {"task_id":"<task_id>","workflow":"t2i","params":{"prompt":"<user prompt>","seed":<int>}}
```
- `task_id` format: `ic-YYYYMMDDHHMMSS` (e.g. `ic-20260325171300`)
- `workflow`: `t2i` (text-to-image), `i2v` (image-to-video), `i2i_style`, `i2i_undress`
- `seed`: any integer; omit for random

### Step 2 — Submit to ComfyUI (submit-only, exits < 5s)
```bash
python3 /Users/leo/Agents/imagecreator-workspace/bin/comfyui_client.py \
  --task /Users/leo/Agents/imagecreator-workspace/inbox/<task_id>.json \
  --submit-only
```
Output line: `[submit] prompt_id=<uuid>` — capture this UUID.

**prompt_id is the canonical job identifier.** Store it; it is used for all subsequent steps.

### Step 3 — Launch background poller (returns < 1s)
```bash
bash -c 'nohup bash /Users/leo/Agents/imagecreator-workspace/bin/poll_and_send.sh \
  /Users/leo/Agents/imagecreator-workspace/inbox/<task_id>.json \
  <prompt_id> \
  <workflow> \
  "<user prompt>" \
  > /tmp/poll_<task_id>.log 2>&1 & echo "background PID=$!"'
```
- Returns immediately with `background PID=XXXXX`
- Background script sends Telegram "processing" ack, then polls every ~90s until done

### Step 4 — Return to main
```json
{"status": "submitted", "prompt_id": "<uuid>", "message": "图片生成已提交，预计3-10分钟完成并自动发送至 Telegram"}
```

---

## Script Responsibilities

### `comfyui_client.py`
| Mode | Flag | Behavior |
|------|------|----------|
| Submit | `--submit-only` | Submit workflow to ComfyUI, print `[submit] prompt_id=<uuid>`, exit immediately |
| Poll | `--poll <prompt_id>` | Poll queue+history for max 60s; print JSON result to stdout, exit |
| Full (legacy) | _(no flag)_ | Submit + poll until done (blocking, not used in current pipeline) |

Output paths:
- Outbox: `/Users/leo/Agents/imagecreator-workspace/outbox/<task_id>.json`
- Media output: `/Users/leo/Agents/imagecreator-workspace/media/output/<filename>.png`

### `poll_and_send.sh`
```
Arguments: <task_json_path> <prompt_id> <workflow> <prompt_text>
```
Responsibilities:
1. Send Telegram "processing" ack immediately (via `send_text.sh`)
2. Loop up to 20 times: run `comfyui_client.py --poll <prompt_id>` (60s window)
3. On `completed`: call `send_photo.sh` with output file + caption → image to Telegram
4. On `pending`: sleep 30s, retry
5. On `error`: send Telegram failure message, exit 1
6. On exhausted polls (20×): send Telegram timeout message, exit 1

Max wall time: 20 × (60s + 30s) ≈ 30 minutes.

### `send_photo.sh`
```
Arguments: <file_path> <caption>
```
Sends image file to Telegram via `sendPhoto` API. Prints `[send_photo] OK — message_id: N` on success.

### `send_text.sh`
```
Arguments: <message>
```
Sends plain text message to Telegram via `sendMessage` API. Prints `[send_text] OK — message_id: N` on success.

---

## prompt_id Lifecycle

| Stage | Where stored |
|-------|-------------|
| After submit | stdout: `[submit] prompt_id=<uuid>` |
| During poll | `--poll <prompt_id>` arg to comfyui_client.py |
| In outbox | `outbox/<task_id>.json` → `"prompt_id"` field |
| In Telegram acks | Embedded in processing/success/failure message text |
| In poll log | `/tmp/poll_<task_id>.log` |

---

## Output File Location

Generated images land at:
```
/Users/leo/Agents/imagecreator-workspace/media/output/<filename>.png
```
Filename is assigned by ComfyUI (e.g. `flux_t2i_00024_.png`). Also mirrored at:
```
/Users/leo/Documents/ComfyUI/output/<filename>.png
```

---

## Return Status

| Condition | Telegram message | Exit code |
|-----------|-----------------|-----------|
| Submit accepted | 🎨 图片生成中 (processing ack) | — |
| Generation complete | ✅ 图片生成完成 + photo | 0 |
| ComfyUI error | ❌ 图片生成失败 + error text | 1 |
| No output file | ❌ 图片生成失败 + "no output file returned" | 1 |
| 20 polls exhausted | ⏰ 图片生成超时 | 1 |

---

## Telegram Message Templates

### Processing ack (sent immediately after submit)
```
🎨 图片生成中
agent: imagecreator
workflow: t2i
prompt_id: <uuid>
prompt: <user prompt>
status: processing
```

### Success (sent with image)
```
✅ 图片生成完成
agent: imagecreator
workflow: t2i
prompt_id: <uuid>
file: <filename>.png
```

### Failure
```
❌ 图片生成失败
agent: imagecreator
workflow: t2i
prompt_id: <uuid>
error: <error message>
```

### Timeout
```
⏰ 图片生成超时
agent: imagecreator
workflow: t2i
prompt_id: <uuid>
error: exceeded 20 poll attempts (~30 min)
```
