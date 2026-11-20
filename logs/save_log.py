#!/usr/bin/env python3
"""Saves everything the Mega prints to logs/test_results.txt (no extra installs needed).
Usage:  python3 save_log.py            (auto-finds the Mega)   Ctrl-C when done."""
import glob, os, sys, termios, time
ports = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*"))
if not ports:
    sys.exit("No Mega found. Plug it in and close the Arduino Serial Monitor.")
port = sys.argv[1] if len(sys.argv) > 1 else ports[0]
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results.txt")
fd = os.open(port, os.O_RDWR | os.O_NOCTTY)
attr = termios.tcgetattr(fd)
attr[0] = 0; attr[1] = 0; attr[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; attr[3] = 0
attr[4] = attr[5] = termios.B115200
attr[6][termios.VMIN] = 0; attr[6][termios.VTIME] = 5
termios.tcsetattr(fd, termios.TCSANOW, attr)
print(f"Listening on {port}\nSaving to {out}\nNow press every key / pull each wire. Ctrl-C to stop.\n")
buf = b""
with open(out, "w") as f:
    f.write(f"# test started {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    try:
        while True:
            buf += os.read(fd, 256)
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                s = line.decode(errors="ignore").rstrip()
                if s:
                    print(s); f.write(s + "\n"); f.flush()
    except KeyboardInterrupt:
        print("\nSaved:", out)
