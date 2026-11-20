"""The AI brain: Ollama, Claude CLI, Anthropic or OpenAI, whichever is available."""
import json
import os
import re
import shutil
import subprocess
import urllib.request

from .util import log


class LLM:
    def __init__(self):
        self.kind = None
        if os.environ.get("ANTHROPIC_API_KEY"):
            self.kind, self.model = "anthropic", os.environ.get("DEFUSE_MODEL", "claude-haiku-4-5")
        elif os.environ.get("OPENAI_API_KEY"):
            self.kind, self.model = "openai", os.environ.get("DEFUSE_MODEL", "gpt-4o-mini")
        elif os.environ.get("OLLAMA_MODEL"):
            self.kind, self.model = "ollama", os.environ["OLLAMA_MODEL"]
        else:
            exe = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
            if os.path.exists(exe) and self._claude_ok(exe):
                self.kind, self.model, self.exe = "claude-cli", os.environ.get("DEFUSE_MODEL", "haiku"), exe

    @staticmethod
    def _claude_ok(exe):
        try:
            r = subprocess.run([exe, "-p", "Reply with: ok", "--model", "haiku"], capture_output=True, text=True, timeout=40)
            return r.returncode == 0 and "login" not in r.stdout.lower()[:80]
        except Exception:
            return False

    def label(self):
        return f"{self.kind}:{self.model}" if self.kind else "offline (no API key found)"

    def _post(self, url, headers, body, timeout):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **headers})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def chat(self, system, user, max_tokens=200, timeout=12):
        """Return text or None on any failure."""
        if not self.kind:
            return None
        try:
            if self.kind == "claude-cli":
                r = subprocess.run([self.exe, "-p", user, "--model", self.model, "--system-prompt", system],
                                   capture_output=True, text=True, timeout=timeout + 20, cwd="/tmp")
                out = r.stdout.strip()
                if r.returncode != 0 or not out:
                    log(f"[ai] claude cli failed: {(r.stderr or out)[:120]}")
                    return None
                return out
            if self.kind == "anthropic":
                d = self._post("https://api.anthropic.com/v1/messages",
                               {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
                               {"model": self.model, "max_tokens": max_tokens, "system": system,
                                "messages": [{"role": "user", "content": user}]}, timeout)
                return "".join(b.get("text", "") for b in d["content"]).strip()
            if self.kind == "openai":
                d = self._post("https://api.openai.com/v1/chat/completions",
                               {"authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
                               {"model": self.model, "max_tokens": max_tokens,
                                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout)
                return d["choices"][0]["message"]["content"].strip()
            if self.kind == "ollama":
                host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
                d = self._post(host + "/api/chat", {},
                               {"model": self.model, "stream": False,
                                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout * 3)
                return d["message"]["content"].strip()
        except Exception as e:  # network, quota, bad key...
            log(f"[ai] request failed: {e}")
        return None

    def chat_json(self, system, user, max_tokens=500, timeout=15):
        txt = self.chat(system + "\nReply with ONE JSON object only, no prose, no code fences.", user, max_tokens, timeout)
        if not txt:
            return None
        m = re.search(r"\{.*\}", txt, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
