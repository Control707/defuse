"""Connection to the bomb: real Mega over USB serial, or a simulated bomb for testing."""
import glob
import queue
import threading
import time

from .config import WIRE_COLORS
from .util import log


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
