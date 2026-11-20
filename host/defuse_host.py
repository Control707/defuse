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
import sys
import threading

from defuse.bomb_link import SerialLink, SimBomb, find_port
from defuse.ears import Ears
from defuse.game_master import GameMaster
from defuse.llm import LLM
from defuse.util import log
from defuse.voice import Voice


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
