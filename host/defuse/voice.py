"""The villain's voice: Piper neural TTS, falling back to the macOS `say` command."""
import os
import queue
import re
import shutil
import subprocess
import threading
import time

from .util import log


class Voice:
    """Speaks lines one at a time in a background thread; drops stale lines so the bomb never lags behind."""

    def __init__(self, mute=False, voice=None):
        self.q = queue.Queue()
        self.mute = mute
        self.voice = voice
        self.on_speak = None  # callback(text, seconds_estimate)
        self.busy_until = 0.0  # mic ignores sound until this time (so it doesn't hear itself)
        self.piper = None
        here = os.path.dirname(os.path.abspath(__file__))
        model = os.path.join(here, "voices", "ryan.onnx")
        if not voice and os.path.exists(model):
            try:
                from piper import PiperVoice
                self.piper = PiperVoice.load(model)
                log("[voice] natural AI voice loaded")
            except Exception as e:
                log(f"[voice] neural voice failed ({e}); using Mac voice")
        if shutil.which("say"):
            self.cmd = ["say", "-v", voice or "Daniel", "-r", "175"]
        elif shutil.which("espeak"):
            self.cmd = ["espeak", "-v", "en", "-p", "20", "-s", "150"]
        else:
            self.cmd = None
        threading.Thread(target=self._run, daemon=True).start()

    def say(self, text, priority=False):
        if not text:
            return
        text = re.sub(r"[*_#`]", "", text).strip()
        if priority:  # drop anything queued
            while not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    break
        self.q.put((time.time(), text))

    def _run(self):
        while True:
            t0, text = self.q.get()
            if time.time() - t0 > 12:  # too stale, skip
                continue
            print(f"\n  \033[91mNINE-VOLT:\033[0m {text}\n> ", end="", flush=True)
            est = max(1.0, len(text.split()) / 2.6)
            if self.on_speak:
                self.on_speak(text, est)
            self.busy_until = time.time() + 60
            if self.piper and not self.mute:
                try:
                    import wave
                    wav = "/tmp/defuse_say.wav"
                    with wave.open(wav, "wb") as w:
                        self.piper.synthesize_wav(text, w)
                    subprocess.run(["afplay", wav], timeout=40)
                except Exception as e:
                    log(f"[voice] {e}")
                    if self.cmd:
                        subprocess.run(self.cmd + [text], timeout=30)
            elif self.cmd and not self.mute:
                try:
                    subprocess.run(self.cmd + [text], timeout=30)
                except Exception:
                    time.sleep(est)
            else:
                time.sleep(est * 0.5)
            self.busy_until = time.time() + 0.6
