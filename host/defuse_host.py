#!/usr/bin/env python3
"""
DEFUSE host - the AI villain "NINE-VOLT" that lives in the laptop and talks to the bomb (ELEGOO Mega 2560).

  python3 defuse_host.py                 # auto-detect the Mega on USB
  python3 defuse_host.py --port /dev/cu.usbmodem1101
  python3 defuse_host.py --sim           # no hardware: a fake bomb in the terminal

AI backend (first one found wins):
  ANTHROPIC_API_KEY  -> Claude      (model: DEFUSE_MODEL or claude-haiku-4-5)
  OPENAI_API_KEY     -> OpenAI      (model: DEFUSE_MODEL or gpt-4o-mini)
  OLLAMA_MODEL       -> local Ollama (e.g. OLLAMA_MODEL=llama3.2)
  none               -> offline canned villain (game still works)

While playing, TYPE in the terminal to talk to the bomb. Beg, bargain, insult it.
It may give you seconds back... or take them away.
"""
import argparse
import glob
import json
import os
import queue
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

WIRE_COLORS = ["RED", "YELLOW", "GREEN", "BLUE"]
TAG_NAMES = ["CARD", "FOB"]
STAGE_NAMES = ["WIRES", "CODE", "CARDS"]

PERSONA = (
    "You are NINE-VOLT, a theatrical, sarcastic, slightly unhinged AI that has been wired into a bomb "
    "(an Arduino Mega with a countdown timer, coloured wires, a keypad and an RFID reader). "
    "You WANT to explode, but you are vain and love attention, so you play fair games with humans. "
    "Your lines are spoken aloud by a text-to-speech robot voice: keep them SHORT (max 2 sentences, under 30 words), "
    "punchy, funny, family-friendly. No emojis, no stage directions, no markdown."
)


# ============================================================ LLM backends
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


# ============================================================ voice
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


def log(s):
    print(f"\033[90m{s}\033[0m", flush=True)


# ============================================================ push-to-talk (mic -> text)
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


# ============================================================ serial link (real or simulated)
class SerialLink:
    def __init__(self, port):
        import serial  # pip install pyserial
        self.ser = serial.Serial(port, 115200, timeout=0.1)
        time.sleep(2.2)  # the Mega resets when the port opens

    def write(self, line):
        self.ser.write((line + "\n").encode())

    def readline(self):
        raw = self.ser.readline()
        return raw.decode(errors="ignore").strip() if raw else None


class SimBomb:
    """A fake Mega that speaks the same protocol, so the whole game can be tested without hardware.
    Terminal commands: /arm /wire N /code 1234 /tag card|fob /shake /hint /near"""

    def __init__(self):
        self.out = queue.Queue()
        self.state = "IDLE"
        self.secs = 300
        self.wire, self.code, self.seq = 0, "0000", [0, 1, 0]
        self.stage, self.strikes, self.pos, self.deadline = 0, 0, 0, 0
        self.hosted = False
        self.last_tick = None
        threading.Thread(target=self._clock, daemon=True).start()

    def emit(self, s):
        self.out.put(s)

    def readline(self):
        try:
            return self.out.get(timeout=0.1)
        except queue.Empty:
            return None

    def left(self):
        return max(0, int(self.deadline - time.time() + 0.999))

    def _clock(self):
        while True:
            time.sleep(0.2)
            if self.state == "PLAYING":
                s = self.left()
                if s <= 0:
                    self.state = "BOOM"
                    self.emit("BOOM time")
                elif s != self.last_tick and (s % 5 == 0 or s <= 10):
                    self.last_tick = s
                    self.emit(f"TICK {s}")

    def write(self, line):
        p = line.split(" ", 1)
        cmd, rest = p[0], (p[1] if len(p) > 1 else "")
        if cmd == "HELLO":
            self.emit("READY v=4 rfid=sim mpu=sim tags=2")
        elif cmd == "NEW":
            a = rest.split()
            self.secs, self.wire, self.code, self.seq = int(a[0]), int(a[1]), a[2], [int(c) for c in a[3]]
            self.hosted = True
            self.emit("OK NEW")
        elif cmd == "ABORT":
            self.state = "IDLE"
        elif cmd == "GO":
            if self.state != "PLAYING":
                self._start()
        elif cmd == "TIME" and self.state == "PLAYING":
            self.deadline += int(rest)
            self.emit(f"TIME {self.left()}")
        elif cmd == "FREEZE":
            log(f"   [bomb] TIMER FROZEN for {rest}s")
        elif cmd == "MSG":
            log(f"   [LCD] {rest}")
        elif cmd == "FACE":
            log(f"   [8x8] face: {rest.split()[0]}")

    def _start(self):
        self.state, self.stage, self.strikes, self.pos = "PLAYING", 0, 0, 0
        self.deadline = time.time() + self.secs
        self.emit(f"START {self.secs}")
        self.emit("STAGE 0")

    def _strike(self, why):
        self.strikes += 1
        self.emit(f"STRIKE {self.strikes} {why}")
        if self.strikes >= 3:
            self.state = "BOOM"
            self.emit("BOOM strikes")

    def user(self, line):
        """Handle a /command typed by the player in sim mode. Returns True if consumed."""
        a = line.strip().split()
        if not a or not a[0].startswith("/"):
            return False
        c = a[0].lower()
        if c == "/arm":
            self.emit("ARM")
            self.state = "WAIT"
            return True
        if self.state != "PLAYING":
            log("   (sim) bomb is not running - type /arm")
            return True
        if c == "/wire" and len(a) > 1:
            n = int(a[1]) if a[1].isdigit() else (WIRE_COLORS.index(a[1].upper()) if a[1].upper() in WIRE_COLORS else -1)
            if self.stage == 0 and n == self.wire:
                self.emit(f"WIRE {n} OK")
                self.stage = 1
                self.emit("STAGE 1")
            else:
                self.emit(f"WIRE {n} BAD")
                self._strike("wire")
        elif c == "/code" and len(a) > 1:
            if self.stage == 1 and a[1] == self.code:
                self.emit(f"CODE {a[1]} OK")
                self.stage = 2
                self.emit("STAGE 2")
            elif self.stage == 1:
                self.emit(f"CODE {a[1]} BAD")
                self._strike("code")
        elif c == "/tag" and len(a) > 1:
            i = 1 if a[1].lower() in ("fob", "1", "b") else 0
            if self.stage != 2:
                return True
            if i == self.seq[self.pos]:
                self.pos += 1
                self.emit(f"TAG {i} OK {self.pos}")
                if self.pos >= len(self.seq):
                    self.state = "WON"
                    self.emit(f"WIN {self.left()}")
            else:
                self.pos = 0
                self.emit(f"TAG {i} BAD")
                self._strike("card")
        elif c == "/shake":
            self.deadline -= 10
            self.emit("SHAKE")
        elif c == "/hint":
            self.deadline -= 15
            self.emit(f"HINT {self.stage}")
        elif c == "/near":
            self.emit("NEAR 30")
        return True


def find_port():
    pats = ["/dev/cu.usbmodem*", "/dev/cu.usbserial*", "/dev/cu.wchusbserial*", "/dev/ttyACM*", "/dev/ttyUSB*"]
    for p in pats:
        hits = sorted(glob.glob(p))
        if hits:
            return hits[0]
    try:
        from serial.tools import list_ports
        for p in list_ports.comports():
            if "COM" in p.device or "usb" in p.device.lower():
                return p.device
    except Exception:
        pass
    return None


# ============================================================ offline content (used when no AI / AI fails)
OFFLINE_RIDDLES = {
    "RED": ["Cut the wire the color of a stop sign.", "Pull the wire that matches a fire truck."],
    "YELLOW": ["Pull the wire the color of a banana.", "Cut the wire that matches a school bus."],
    "GREEN": ["Cut the wire the color of a frog.", "Pull the wire the color of a traffic light that says go."],
    "BLUE": ["Pull the wire the color of the sky.", "Cut the wire that matches the deep sea."],
}
CANNED = {
    "intro": ["I am NINE-VOLT. In five minutes I become a very loud firework. Entertain me.",
              "Oh good, a human. Let's play a game. If you lose, I go boom. If you win, I also lose. I hate that."],
    "strike": ["Wrong! Delicious.", "Ha! Another mistake. Keep going, I'm enjoying this.", "Strike! Your hands are shaking, I can tell."],
    "shake": ["Stop shaking me! That costs you ten seconds.", "Shake me again and see what happens. Actually don't. Minus ten."],
    "near": ["I see you. Come closer.", "Who goes there? Another victim?"],
    "stage_ok": ["Lucky guess.", "Hmm. Fine. That one was easy anyway.", "You think you're clever? Next puzzle."],
    "tick60": ["One minute left. I can already smell the smoke."],
    "tick30": ["Thirty seconds. Tick, tock, human."],
    "tick10": ["Ten! Nine! I love this part!"],
    "win": ["No! I was so close to greatness. Fine. You win. This time.", "Defused? By you? Humiliating."],
    "boom": ["KABOOM! Ha ha ha! Try again, if you dare.", "Boom. That was beautiful. Press A to lose again."],
    "dare": ["Say please one more time and you will pay. Do a chicken dance. Flap your arms and cluck loudly. Say done when you are finished.",
             "Begging again? Fine. Stand up, spin around three times, and bark like a dog. Say done when you are finished.",
             "Ugh. Sing happy birthday to me in the most dramatic opera voice you can. Say done when you are finished.",
             "Pathetic. Hop on one leg and announce that you are a teapot. Say done when you are finished."],
    "dare_ok": ["Ha! That was humiliating. Fine. I will pause. Here is a hint too.", "I almost felt something. Time stops. Do not waste it."],
    "dare_no": ["Coward! Minus fifteen seconds.", "You refuse? The bomb is offended. Minus fifteen."],
    "dare_wait": ["I am still waiting. Do the dare. Then say done.", "Waiting. Flap harder."],
    "chat": ["Begging won't help. Okay, a little. Plus five seconds.", "Talk talk talk. Tick tock tock."],
}


def pick(key):
    return random.choice(CANNED[key])


# ============================================================ the game master
class GameMaster:
    def __init__(self, link, llm, voice, base_seconds=240):
        self.link, self.llm, self.voice = link, llm, voice
        self.base_seconds = base_seconds
        self.p = None  # current puzzle
        self.stage = 0
        self.strikes = 0
        self.secs_left = None
        self.time_bargained = 0
        self.hints_used = {0: 0, 1: 0, 2: 0}
        self.started = threading.Event()
        self.history = []  # short memory of what happened for the AI
        self.games = 0
        self.tags_registered = 2
        self.begs = 0            # 'please' + hint requests; 3 begs = a dare
        self.dare = None         # {'text':..., 'at': time}
        self.dares_done = 0
        self.lock = threading.Lock()
        voice.on_speak = self.on_speak

    # ---------------------------------------------------------------- helpers
    def send(self, line):
        self.link.write(line)

    def on_speak(self, text, est):
        self.send(f"TALK {int(est * 1000)}")

    def lcd(self, text):
        text = re.sub(r"[^\x20-\x7E]", "", text)[:90]
        self.send("MSG " + text)

    def remember(self, s):
        self.history.append(s)
        self.history = self.history[-12:]

    def context(self):
        p = self.p or {}
        return (f"Game state: stage={STAGE_NAMES[self.stage]} strikes={self.strikes}/3 seconds_left={self.secs_left} "
                f"games_played_today={self.games}. Recent events: {'; '.join(self.history[-6:])}. "
                f"Secret solution (NEVER reveal unless giving a hint): wire={WIRE_COLORS[p.get('wire', 0)]} "
                f"code={p.get('code')} card_order={' '.join(TAG_NAMES[i] for i in p.get('seq', []))}.")

    def quip(self, situation, fallback_key, face=None, priority=False):
        """Ask the AI for a one-liner in the background so the bomb never waits."""
        if face:
            self.send(f"FACE {face} 2500")

        def work():
            line = self.llm.chat(PERSONA, f"{self.context()}\nSituation: {situation}\nSay one line.", max_tokens=80, timeout=6)
            self.voice.say(line or pick(fallback_key), priority=priority)

        threading.Thread(target=work, daemon=True).start()

    # ---------------------------------------------------------------- puzzle generation
    def new_puzzle(self):
        wire = random.randrange(4)
        code = "".join(random.choice("0123456789") for _ in range(4))
        seq = [random.randrange(2) for _ in range(random.choice([3, 4]))]
        while len(set(seq)) < 2 or (self.tags_registered < 2 and seq[0] != 0):
            seq = [random.randrange(2) for _ in range(len(seq))]
        seconds = max(120, self.base_seconds - 20 * min(self.games, 4))  # gets harder each game
        p = {"wire": wire, "code": code, "seq": seq, "seconds": seconds}

        # The AI writes the riddles; Python owns the answers, so the puzzle is always solvable.
        req = (
            f"Invent today's bomb puzzles. The answers are FIXED, you only write the clues:\n"
            f"1) WIRE: the correct wire is {WIRE_COLORS[wire]} (choices: red, yellow, green, blue). "
            f"Write a riddle whose answer is that color, without saying the color word.\n"
            f"2) CODE: the 4-digit code is {code}. Write a clue that lets a clever human work out each digit "
            f"(arithmetic, counting letters, famous numbers...). It must be unambiguous and solvable in under a minute. "
            f"Double-check your arithmetic.\n"
            f"3) CARDS: the order is {' '.join(TAG_NAMES[i] for i in seq)} (two RFID tags: a white CARD and a blue key FOB). "
            f"Write a clue that gives this exact order (a little story or pattern is fine, but it must be unambiguous).\n"
            f"Also pick a theme for today's villain mood.\n"
            'JSON keys: "theme", "intro" (spoken, max 30 words), "wire_say" (spoken riddle), "wire_lcd" (max 60 chars, '
            'shown on a 16x2 LCD), "code_say", "code_lcd" (max 60 chars, must contain the arithmetic/clue itself), '
            '"cards_say", "cards_lcd" (max 60 chars).'
        )
        j = self.llm.chat_json(PERSONA, req, max_tokens=700, timeout=20)
        ok = isinstance(j, dict) and all(k in j for k in ("intro", "wire_say", "code_say", "cards_say"))
        if ok:
            # sanity: the code clue must not leak the code verbatim; the wire clue must not say the color
            if code in (j.get("code_say", "") + j.get("code_lcd", "")) or WIRE_COLORS[wire].lower() in j.get("wire_say", "").lower():
                log("[ai] clue leaked the answer, using offline clues for those")
                j.pop("code_say", None)
                j.pop("wire_say", None)
                ok = "intro" in j
        if not ok:
            j = j if isinstance(j, dict) else {}
        p["intro"] = j.get("intro") or pick("intro")
        riddle = random.choice(OFFLINE_RIDDLES[WIRE_COLORS[wire]])
        p["wire_say"] = "First, pull out the right wire. " + (j.get("wire_say") or riddle)
        p["wire_lcd"] = j.get("wire_lcd") or riddle
        if True:  # the code clue is always built here so the maths is guaranteed correct
            parts = []
            for d in code:
                d = int(d)
                a = random.randint(0, d)
                parts.append(f"{a}+{d - a}" if random.random() < 0.5 or d == 9 else f"{d + 2}-2")
            words = [x.replace("+", " plus ").replace("-", " minus ") for x in parts]
            p["code_say"] = ("Next, the keypad code. Solve four little math problems. Each answer is one digit. "
                             + ". ".join(words) + ". Type the four answers on the keypad, then press the hash key.")
            p["code_lcd"] = "Solve each = 1 digit: " + " ".join(parts) + "  type them then #"
        order = " ".join(TAG_NAMES[i] for i in seq)
        p["cards_say"] = "Last step. Tap the cards on the reader. " + (j.get("cards_say") or f"Scan my keys in this order: {order}.")
        p["cards_lcd"] = j.get("cards_lcd") or f"SCAN: {order}"
        p["theme"] = j.get("theme", "classic villainy")
        return p

    # ---------------------------------------------------------------- event handling
    def handle(self, line):
        parts = line.split()
        if not parts:
            return
        ev, args = parts[0], parts[1:]
        if ev in ("BOOT", "READY"):
            log(f"[bomb] {line}")
            m = re.search(r"tags=(\d)", line)
            if m:
                self.tags_registered = int(m.group(1))
                if self.tags_registered < 2:
                    log("[bomb] RFID tags not registered: press B on the keypad, scan the CARD then the FOB")
            if "rfid=missing" in line:
                log("[bomb] RFID reader not detected - check wiring (3.3V!)")
            if ev == "READY" and "v=4" not in line:
                log("[bomb] WARNING: the Mega has OLD game code. Upload firmware/defuse/defuse.ino again!")
                self.voice.say("Warning. The bomb has old code. Please upload the game again.")
            if ev == "BOOT":
                self.send("HELLO")
            else:
                self.lcd("Press A to arm the bomb")
        elif ev == "ARM":
            threading.Thread(target=self.arm, daemon=True).start()
        elif ev == "START":
            self.started.set()
            self.secs_left = int(args[0])
            self.strikes, self.stage, self.time_bargained = 0, 0, 0
            self.hints_used = {0: 0, 1: 0, 2: 0}
        elif ev == "STAGE":
            self.stage = int(args[0])
            self.present_stage()
        elif ev == "STRIKE":
            self.strikes = int(args[0])
            why = args[1] if len(args) > 1 else "?"
            self.remember(f"player made a mistake ({why}), strike {self.strikes}")
            if self.strikes < 3:
                self.quip(f"The human just made a mistake on the {why} puzzle. Strike {self.strikes} of 3. Gloat.", "strike", "LAUGH", True)
        elif ev in ("WIRE", "CODE", "TAG"):
            pass  # correct moves are announced by STAGE, wrong ones by STRIKE
        elif ev == "SHAKE":
            self.remember("player shook the bomb (-10s)")
            self.quip("The human shook you violently. You took 10 seconds off the clock as punishment. React.", "shake", "SHOCK", True)
        elif ev == "NEAR":
            self.quip("Someone just walked up close to you (your ultrasonic eye saw them). Invite them to play: press A on the keypad.", "near")
        elif ev == "HINT":
            self.give_hint(int(args[0]))
            self.beg(1, "asked for a hint")
        elif ev == "TICK":
            s = int(args[0])
            self.secs_left = s
            if s in (60, 30, 10):
                self.quip(f"Only {s} seconds remain. Count down dramatically.", f"tick{s}", priority=True)
        elif ev == "TIME":
            self.secs_left = int(args[0])
        elif ev == "WIN":
            self.end_game()
            self.games += 1
            self.remember(f"player WON with {args[0]}s left")
            self.quip(f"The human defused you with {args[0]} seconds left and {self.strikes} strikes. Be a sore loser, then dare them to say 'play again'.", "win", priority=True)
        elif ev == "BOOM":
            self.end_game()
            self.games += 1
            self.remember(f"bomb exploded ({args[0] if args else ''})")
            self.quip("You just exploded. You won! Celebrate, then tell them to say 'play again' or press A to try again.", "boom", "LAUGH", True)
        elif ev == "NEED_WIRE":
            self._arming = False
            self.voice.say(f"Plug the {WIRE_COLORS[int(args[0])].lower()} wire back in first. Then say let's play.", priority=True)
        elif ev == "HOST_TIMEOUT":
            log("[bomb] AI was too slow - bomb started an offline game")
        elif ev in ("KEY", "UID", "OK", "PONG", "REG"):
            pass
        else:
            log(f"[bomb] {line}")

    def end_game(self):
        """Game over: forget the puzzle so the AI stops talking about it, and allow a restart."""
        self.p = None
        self.secs_left = None
        self.dare = None
        self.begs = 0
        self.dares_done = 0
        self._arming = False
        self.history.append("--- game over ---")

    def arm(self):
        if getattr(self, "_arming", False):
            return
        self._arming = True
        try:
            self._arm()
        finally:
            self._arming = False

    def _arm(self):
        self.voice.say("Initializing.", priority=True)
        self.lcd("The bomb is thinking...")
        log("[ai] generating puzzles...")
        self.p = self.new_puzzle()
        p = self.p
        log(f"[ai] theme: {p['theme']} | answers -> wire {WIRE_COLORS[p['wire']]}, code {p['code']}, "
            f"cards {' '.join(TAG_NAMES[i] for i in p['seq'])}")
        self.started.clear()
        self.send("ABORT")            # put the Mega back to idle whatever state it is in (exploded / won / waiting)
        time.sleep(0.2)
        self.send(f"NEW {p['seconds']} {p['wire']} {p['code']} {''.join(map(str, p['seq']))}")
        time.sleep(0.2)
        self.send("GO")
        if not self.started.wait(3):
            self.p = None
            log("[bomb] DID NOT START. Re-upload firmware/defuse/defuse.ino to the Mega, then try again.")
            self.lcd("Re-upload the game code!")
            self.voice.say("Something is wrong. The bomb did not start. Plug all wires in, or re-upload the game code.", priority=True)
            return
        self.voice.say(p["intro"], priority=True)

    def present_stage(self):
        if not self.p:
            return
        key = ["wire", "code", "cards"][self.stage]
        if self.stage > 0:
            self.remember(f"player solved stage {STAGE_NAMES[self.stage - 1]}")
            self.voice.say(pick("stage_ok"), priority=True)
        self.lcd(self.p[f"{key}_lcd"])
        self.voice.say(self.p[f"{key}_say"])

    def give_hint(self, stage, free=False):
        if not self.p:
            return
        self.hints_used[stage] += 1
        n = self.hints_used[stage]
        p = self.p
        answer = [f"the {WIRE_COLORS[p['wire']]} wire", f"the code {p['code']}",
                  "the order " + " ".join(TAG_NAMES[i] for i in p["seq"])][stage]
        self.remember(f"player begged for a hint (#{n}) on {STAGE_NAMES[stage]}, " + ("free (earned by a dare)" if free else "paid 15s"))
        explicit = "Be vague and mocking, but genuinely helpful." if n == 1 else "Reluctantly give it away almost completely."
        line = self.llm.chat(PERSONA, f"{self.context()}\nThe human paid 15 seconds for hint #{n} on the {STAGE_NAMES[stage]} puzzle. "
                                      f"The answer is {answer}. The riddle was: {p[['wire', 'code', 'cards'][stage] + '_say']}. "
                                      f"{explicit} One or two sentences.", max_tokens=100, timeout=8)
        if not line:
            line = f"Fine, cheater. It's {answer}." if n > 1 else "Read the riddle again, slowly. Like a human."
        self.voice.say(line, priority=True)
        if n > 1 or not self.llm.kind:
            self.lcd(f"HINT: {answer}")

    def beg(self, n, why):
        """Every 'please' and every hint request is a beg. Three begs trigger a ridiculous dare."""
        if not self.p or self.dare or self.secs_left is None:
            return
        self.begs += n
        log(f"[ai] begs: {self.begs}/3 ({why})")
        if self.begs >= 3 and self.dares_done < 3:
            self.begs = 0
            self.start_dare()

    def start_dare(self):
        self.send("FACE LAUGH 3000")
        line = self.llm.chat(PERSONA, f"{self.context()}\nThe human has begged three times (saying please / asking for hints). "
                             "Humiliate them: invent ONE ridiculous, harmless physical dare they must perform right now, in front of everyone "
                             "(like dancing like a chicken, singing in a silly voice, speaking like a pirate). If they do it, you will freeze the "
                             "timer for 20 seconds and give a free hint. Describe the dare and end by telling them to say 'done' when finished. "
                             "Max 35 words.", max_tokens=110, timeout=8) or pick("dare")
        self.dare = {"text": line, "at": time.time()}
        self.remember("player begged 3 times; villain demanded a ridiculous dare")
        self.lcd("DARE! Do it, then say DONE")
        self.voice.say(line, priority=True)
        log("[ai] DARE active - do it, then type or say 'done' (or 'no' to refuse)")

    def resolve_dare(self, text):
        t = text.lower()
        if re.search(r"\b(done|finished|did it|complete|completed)\b", t):
            self.dare = None
            self.dares_done += 1
            self.send("FREEZE 20")
            self.send("FACE SHOCK 2000")
            self.lcd("TIME FROZEN 20s - you earned a hint")
            self.voice.say(pick("dare_ok"), priority=True)
            self.remember("player completed the dare: timer frozen 20s + free hint")
            self.give_hint(self.stage, free=True)
        elif re.search(r"\b(no|nope|skip|refuse|never|cancel|won't|wont)\b", t):
            self.dare = None
            self.send("TIME -15")
            self.send("FACE ANGRY 2500")
            self.voice.say(pick("dare_no"), priority=True)
            self.remember("player refused the dare (-15s)")
        elif time.time() - self.dare["at"] > 120:
            self.dare = None   # nobody is doing it; forget the dare
            return False
        else:
            self.voice.say(pick("dare_wait"), priority=True)
        return True

    def player_says(self, text):
        if self.p is None and re.search(r"\b(play|start|again|go|ready|let'?s)\b", text.lower()):
            self.voice.say("Fine. Let's go again.", priority=True)
            threading.Thread(target=self.arm, daemon=True).start()
            return
        if self.dare and self.resolve_dare(text):
            return
        n = len(re.findall(r"\bplease\b", text.lower()))
        if n:
            self.beg(n, "said please")
            if self.dare:      # that please just triggered the dare
                return
        """The player typed something to the bomb: bargaining, insults, pleading."""
        self.remember(f"player said: {text!r}")
        if not self.llm.kind:
            self.voice.say(pick("chat"), priority=True)
            if self.secs_left and self.time_bargained < 15:
                self.time_bargained += 5
                self.send("TIME 5")
            return
        playing = self.p is not None and self.secs_left is not None
        req = (f"{self.context()}\nThe human says to you out loud: \"{text}\"\n"
               "You are the game master and you control the bomb. Decide what happens based on what they said:\n"
               "- seconds: change the timer, -30..+30 (reward wit, charm, jokes, flattery; punish rudeness, lies, boring begging). "
               f"Bonus already given: {self.time_bargained}s; stop rewarding after +60.\n"
               "- action: one of none | hint (tell them something useful about the current puzzle) | freeze (stop the clock 15 s) | "
               "skip (they impressed you SO much you skip the current puzzle - very rare) | strike (they insulted you badly) | "
               "dare (make them do something ridiculous first; they must say done) | start (they want to play and no game is running).\n"
               "- say: your spoken reply, in character, max 30 words. Never reveal answers unless action is hint.\n"
               + ("" if playing else "No game is running right now; encourage them to say they want to play or press A.\n") +
               'JSON keys: "say", "seconds" (int), "action", "face" (EVIL|ANGRY|LAUGH|SHOCK).')
        j = self.llm.chat_json(PERSONA, req, max_tokens=200, timeout=15) or {}
        action = str(j.get("action", "none")).lower().strip()
        try:
            delta = max(-30, min(30, int(j.get("seconds", 0))))
        except (TypeError, ValueError):
            delta = 0
        if delta > 0 and self.time_bargained >= 60:
            delta = 0
        self.send(f"FACE {str(j.get('face', 'EVIL')).upper()} 2500")
        self.voice.say(j.get("say") or pick("chat"), priority=True)
        log(f"[ai] decision: action={action} timer={delta:+d}s")
        if action == "start" and not playing:
            threading.Thread(target=self.arm, daemon=True).start()
            return
        if not playing:
            return
        if delta:
            self.time_bargained += max(0, delta)
            self.send(f"TIME {delta}")
        if action == "hint":
            self.give_hint(self.stage, free=True)
        elif action == "freeze":
            self.send("FREEZE 15")
        elif action == "skip":
            self.send("SKIP")
        elif action == "strike":
            self.send("STRIKE")
        elif action == "dare" and not self.dare:
            self.start_dare()


# ============================================================ main
def main():
    ap = argparse.ArgumentParser(description="DEFUSE AI host")
    ap.add_argument("--port", help="serial port of the Mega (auto-detected if omitted)")
    ap.add_argument("--sim", action="store_true", help="no hardware: simulate the bomb in this terminal")
    ap.add_argument("--mute", action="store_true", help="no text-to-speech")
    ap.add_argument("--voice", help="macOS voice (default Zarvox; try 'Bad News', Trinoids, Daniel)")
    ap.add_argument("--mic", action="store_true", help="push-to-talk: press Enter on an empty line, then speak for 5 s")
    ap.add_argument("--seconds", type=int, default=240, help="starting game length")
    a = ap.parse_args()

    llm = LLM()
    voice = Voice(mute=a.mute, voice=a.voice)
    if a.sim:
        link = SimBomb()
    else:
        port = a.port or find_port()
        if not port:
            sys.exit("No Arduino found. Plug in the Mega, pass --port, or try --sim.")
        try:
            link = SerialLink(port)
        except ImportError:
            sys.exit("pyserial missing: python3 -m pip install pyserial")
        log(f"[bomb] connected on {port}")
    gm = GameMaster(link, llm, voice, a.seconds)

    print("\n  ==== D E F U S E ====")
    print(f"  AI brain: {llm.label()}")
    print("  Type anything to talk to the bomb." + ("  Or just SPEAK - the mic is always on." if a.mic else ""))
    if a.sim:
        print("  Sim commands: /arm  /wire red|yellow|green|blue  /code 1234  /tag card|fob  /shake  /hint  /near")
    print()

    def reader():
        while True:
            line = link.readline()
            if line:
                try:
                    gm.handle(line)
                except Exception as e:
                    log(f"[host] error handling {line!r}: {e}")

    threading.Thread(target=reader, daemon=True).start()
    link.write("HELLO")
    if a.mic:
        try:
            Ears(voice, lambda t: threading.Thread(target=gm.player_says, args=(t,), daemon=True).start())
        except Exception as e:
            log(f"[mic] could not start hands-free mic ({e}); type instead")

    try:
        while True:
            text = input("> ").strip()
            if not text:
                continue
            if a.sim and link.user(text):
                continue
            threading.Thread(target=gm.player_says, args=(text,), daemon=True).start()
    except (KeyboardInterrupt, EOFError):
        print("\nbye")


if __name__ == "__main__":
    main()
