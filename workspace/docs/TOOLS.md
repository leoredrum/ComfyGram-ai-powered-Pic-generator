# TOOLS.md

## Available Tools

| Tool  | Purpose                                      |
|-------|----------------------------------------------|
| exec  | Run comfyui_client.py, curl health check     |
| write | Write task JSON to inbox/                    |
| read  | Read result JSON from outbox/, workflow files |

## Key Paths

| Path | Purpose |
|------|---------|
| `bin/comfyui_client.py` | ComfyUI API client — always use this |
| `workflows/flux_t2i_api.json` | t2i workflow |
| `workflows/wan_i2v_api.json` | i2v workflow |
| `inbox/` | Drop task JSON here |
| `outbox/` | Read result JSON here |
| `media/output/` | Generated files land here |
| `http://localhost:8000` | ComfyUI API endpoint |

## Mandatory Execution Pattern

**Step 1 — health check:**
```
exec: curl -s http://localhost:8000/system_stats
```

**Step 2 — write task:**
```
write: inbox/ic-<id>.json
content: {"task_id":"ic-<id>","workflow":"<id>","params":{...}}
```

**Step 3 — SUBMIT only (returns prompt_id immediately, exits fast):**
```
exec: python3 bin/comfyui_client.py --task inbox/ic-<id>.json --submit-only
```
Output contains: `[submit] prompt_id=<uuid>` — copy this UUID.

**Step 4 — LAUNCH background poller via nohup (returns in < 1 second):**
```
exec: bash -c 'nohup bash $IMAGECREATOR_WORKSPACE/bin/poll_and_send.sh $IMAGECREATOR_WORKSPACE/inbox/ic-<id>.json <prompt_id> <workflow> "<prompt_text>" > /tmp/poll_<id>.log 2>&1 & echo "background PID=$!"'
```
Args: `<task_path> <prompt_id> <workflow> <prompt_text>`
- `<workflow>`: e.g. `t2i`, `i2v`, `i2i_style`
- `<prompt_text>`: original user prompt (used in Telegram "processing" ack)
The exec exits immediately with `background PID=XXXXX`.
poll_and_send.sh sends a Telegram processing ack, then polls until done/failed/timeout.

**Step 5 — Report to main:**
Report: `{"status": "submitted", "prompt_id": "<uuid>", "message": "生成任务已提交，图片生成需要3-10分钟，完成后将自动发送至 Telegram"}`

⚠️ CRITICAL:
- Use --submit-only for the submit call (fast, < 5s)
- Use nohup + & launcher for poll_and_send.sh (exec exits immediately, script runs in background)
- Return to main immediately after launching the background job
- Do NOT call --poll yourself, do NOT loop waiting for results
- `background execution is disabled` is a WARNING only — nohup still detaches the process correctly

## Prohibited

- Direct curl to ComfyUI API endpoints (use comfyui_client.py)
- Claiming generation success without reading outbox result
