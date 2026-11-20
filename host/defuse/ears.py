"""Speech-to-text: always-on mic with local faster-whisper (Ears), or OpenAI Whisper push-to-talk (listen)."""
import json
import os
import queue
import subprocess
import threading
import time
import urllib.request

from .util import log


def listen(seconds=5):
    """Record from the Mac mic with ffmpeg and transcribe with OpenAI Whisper. Returns text or ''."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        log("[mic] needs OPENAI_API_KEY for speech-to-text; type instead")
        return ""
    wav = "/tmp/defuse_mic.wav"
    print(f"  \033[92m* listening for {seconds}s - speak now!\033[0m", flush=True)
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "avfoundation", "-i", ":default",
                        "-t", str(seconds), "-ac", "1", "-ar", "16000", wav], capture_output=True, text=True)
    if r.returncode != 0:
        log("[mic] recording failed (allow Terminal to use the microphone in System Settings > Privacy): " + r.stderr[-200:])
        return ""
    boundary = "----defuse"
    data = open(wav, "rb").read()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\nwhisper-1\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.wav\"\r\nContent-Type: audio/wav\r\n\r\n").encode() \
           + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request("https://api.openai.com/v1/audio/transcriptions", data=body,
                                 headers={"Authorization": "Bearer " + key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = json.loads(resp.read()).get("text", "").strip()
        print(f"  you said: {text}")
        return text
    except Exception as e:
        log(f"[mic] transcription failed: {e}")
        return ""


class Ears:
    """Always-on microphone: waits for you to talk, records until you stop, transcribes locally with Whisper."""

    def __init__(self, voice, on_text):
        import numpy as np, sounddevice as sd
        from faster_whisper import WhisperModel
        self.np, self.sd, self.voice, self.on_text = np, sd, voice, on_text
        log("[mic] loading speech model (first time takes ~15 s)...")
        here = os.path.dirname(os.path.abspath(__file__))
        self.model = WhisperModel("base.en", device="cpu", compute_type="int8", download_root=os.path.join(here, "models"))
        self.q = queue.Queue()
        self.noise = 0.01
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        np, sd = self.np, self.sd
        sr, block = 16000, 1600  # 0.1 s blocks
        talking, chunks, silent, calib = False, [], 0, []
        with sd.InputStream(samplerate=sr, channels=1, dtype="float32", blocksize=block,
                            callback=lambda d, f, t, st: self.q.put(d.copy())):
            log("[mic] listening - just talk to the bomb")
            while True:
                d = self.q.get()[:, 0]
                if time.time() < self.voice.busy_until:   # bomb is speaking: don't listen to ourselves
                    talking, chunks, silent = False, [], 0
                    continue
                rms = float(np.sqrt(np.mean(d * d)))
                if len(calib) < 15:                         # first 1.5 s: learn the room noise
                    calib.append(rms)
                    self.noise = max(0.004, float(np.median(calib)))
                    continue
                loud = rms > self.noise * 3.0
                if not talking:
                    self.noise = 0.98 * self.noise + 0.02 * rms if not loud else self.noise
                    if loud:
                        talking, chunks, silent = True, [d], 0
                else:
                    chunks.append(d)
                    silent = 0 if loud else silent + 1
                    if silent >= 8 or len(chunks) > 120:      # 0.8 s of quiet (or 12 s max) = end of sentence
                        talking = False
                        if len(chunks) >= 6:                  # ignore clicks shorter than 0.6 s
                            audio = np.concatenate(chunks)
                            threading.Thread(target=self._transcribe, args=(audio,), daemon=True).start()
                        chunks = []

    def _transcribe(self, audio):
        try:
            segs, _ = self.model.transcribe(audio, language="en", vad_filter=False)
            text = " ".join(x.text for x in segs).strip()
        except Exception as e:
            log(f"[mic] transcription error: {e}")
            return
        if len(text) < 2 or text.lower().strip(" .!?") in ("you", "thank you", "thanks for watching", "bye"):
            return  # whisper's usual hallucinations on noise
        print(f"\n  \033[92mYOU:\033[0m {text}\n> ", end="", flush=True)
        self.on_text(text)
