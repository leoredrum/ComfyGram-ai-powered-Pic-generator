"""
Shared Telegram HTTP client using httpx + subprocess hard-kill for long-poll.

Drop-in replacement for urllib-based Telegram Bot API calls in
crawler / imagecreator / retoucher bots.

Architecture:
  - Short calls (sendMessage, sendPhoto, etc.): httpx.Client directly.
    These complete in <5s on healthy networks; httpx timeout is sufficient.

  - Long-poll calls (getUpdates with timeout > 30s): delegated to a
    subprocess that can be reliably killed if the SSL layer hangs.
    This is the ONLY reliable way to enforce a hard timeout on macOS,
    because CPython's _ssl.c PySSL_select → poll() swallows both
    socket timeouts and SIGALRM (retries on EINTR without checking
    for pending Python exceptions).

Usage:
    from telegram_http import TelegramClient

    tg = TelegramClient("https://api.telegram.org/bot<TOKEN>")
    r  = tg.call("getMe")
    r  = tg.call("getUpdates", {"timeout": 60}, read_timeout=70)
"""

from __future__ import annotations

import httpx
import json
import os
import subprocess
import sys
import threading

# Threshold: calls with read_timeout above this use the subprocess path.
_LONG_POLL_THRESHOLD = 30.0

# Extra seconds added to the subprocess hard-kill deadline.
_HARD_GRACE = 15


class TelegramClient:
    """Telegram Bot API client: httpx for short calls, subprocess for long-poll."""

    def __init__(self, api_base: str, default_timeout: float = 15.0):
        self.api_base = api_base.rstrip("/")
        self.default_timeout = default_timeout
        self._lock = threading.Lock()
        self._client: httpx.Client = self._make_client(default_timeout)
        # Cache the Python interpreter path for subprocess calls
        self._python = sys.executable

    def _make_client(self, default_read: float) -> httpx.Client:
        return httpx.Client(
            timeout=httpx.Timeout(
                connect=10.0, read=default_read, write=15.0, pool=10.0),
            http2=False,
            follow_redirects=False,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                keepalive_expiry=30,
            ),
        )

    def _get_client(self) -> httpx.Client:
        with self._lock:
            return self._client

    # ── Core request ─────────────────────────────────────

    def call(self, method: str,
             params: dict | None = None,
             read_timeout: float | None = None) -> dict:
        """Call a Bot API method.

        Long-poll calls (read_timeout > 30s) use subprocess isolation.
        Short calls use httpx directly.
        """
        timeout_val = read_timeout if read_timeout is not None else self.default_timeout

        if timeout_val > _LONG_POLL_THRESHOLD:
            return self._call_subprocess(method, params, timeout_val)
        return self._call_direct(method, params, timeout_val)

    def _call_direct(self, method: str, params: dict | None,
                     timeout_val: float) -> dict:
        """Fast path: httpx.Client for short-timeout calls."""
        client = self._get_client()
        url = f"{self.api_base}/{method}"
        kw = {"timeout": httpx.Timeout(
            connect=10.0, read=timeout_val, write=15.0, pool=10.0)}
        try:
            if params:
                r = client.post(url, json=params, **kw)
            else:
                r = client.get(url, **kw)
            try:
                return r.json()
            except Exception:
                return {"ok": False, "error": f"HTTP {r.status_code}: non-JSON body"}
        except httpx.TimeoutException as e:
            return {"ok": False, "error": f"Timeout: {e}"}
        except httpx.HTTPError as e:
            return {"ok": False, "error": f"HTTP error: {e}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _call_subprocess(self, method: str, params: dict | None,
                         timeout_val: float) -> dict:
        """Subprocess path for long-poll calls (getUpdates).

        Spawns a short-lived Python process that makes the HTTP call.
        If it hangs in SSL poll, we kill -9 the entire process.
        """
        hard_limit = timeout_val + _HARD_GRACE
        url = f"{self.api_base}/{method}"

        # Minimal inline script — does one HTTP call and writes JSON to stdout
        script = (
            "import httpx,sys,json\n"
            "try:\n"
            f" r=httpx.post({url!r},json=json.loads(sys.stdin.read()),"
            f"timeout=httpx.Timeout(connect=10,read={timeout_val},write=15,pool=10))\n"
            " sys.stdout.write(r.text)\n"
            "except httpx.TimeoutException as e:\n"
            ' sys.stdout.write(json.dumps({"ok":False,"error":f"Timeout: {e}"}))\n'
            "except Exception as e:\n"
            ' sys.stdout.write(json.dumps({"ok":False,"error":str(e)}))\n'
        )

        stdin_data = json.dumps(params or {}).encode()

        try:
            proc = subprocess.Popen(
                [self._python, "-c", script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = proc.communicate(input=stdin_data, timeout=hard_limit)
            if proc.returncode != 0 and not stdout:
                err_msg = stderr.decode(errors="replace")[:200].strip()
                return {"ok": False, "error": f"Subprocess exit {proc.returncode}: {err_msg}"}
            try:
                return json.loads(stdout)
            except Exception:
                return {"ok": False, "error": f"Subprocess non-JSON: {stdout[:200]}"}
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return {"ok": False, "error":
                    f"Hard timeout after {hard_limit:.0f}s (subprocess killed → SSL hang recovery)"}
        except Exception as e:
            return {"ok": False, "error": f"Subprocess error: {e}"}

    # ── File upload (multipart) ──────────────────────────

    def upload(self, method: str,
               files: dict,
               data: dict | None = None,
               read_timeout: float = 30.0) -> dict:
        """Upload a file via multipart/form-data (always direct, not long-poll)."""
        client = self._get_client()
        url = f"{self.api_base}/{method}"
        try:
            r = client.post(
                url, files=files, data=data,
                timeout=httpx.Timeout(
                    connect=10.0, read=read_timeout,
                    write=read_timeout, pool=10.0),
            )
            try:
                return r.json()
            except Exception:
                return {"ok": False, "error": f"HTTP {r.status_code}: non-JSON"}
        except httpx.TimeoutException as e:
            return {"ok": False, "error": f"Upload timeout: {e}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── File download ────────────────────────────────────

    def download_file(self, file_path: str,
                      read_timeout: float = 20.0) -> bytes | None:
        """Download a file from Telegram's file API."""
        file_url = self.api_base.replace("/bot", "/file/bot", 1) + "/" + file_path
        client = self._get_client()
        try:
            r = client.get(
                file_url,
                timeout=httpx.Timeout(
                    connect=10.0, read=read_timeout,
                    write=10.0, pool=10.0),
            )
            return r.content if r.status_code == 200 else None
        except Exception:
            return None

    # ── Lifecycle ────────────────────────────────────────

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass
