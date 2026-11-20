# 💣 DEFUSE: a talking AI bomb you defuse by voice

A physical bomb built from the ELEGOO Mega 2560 kit, run by an AI villain called **NINE-VOLT**. You talk to it out loud, and it talks back and controls the game based on what you say.

Everything runs locally on a Mac: the AI brain (Ollama), speech-to-text (Whisper) and the voice (Piper). It needs no API key and no internet once set up.

## What the AI does
- **Writes new riddles every round.** The program chooses the answers, so every puzzle can be solved.
- **Listens all the time.** Just talk; there's no button to press.
- **Controls the game based on your words.** It can add or remove time (±30 s), give a hint, freeze the clock, skip a puzzle, give you a strike for insults, or demand a dare.
- **Say "please" three times** and it makes you do something ridiculous, like a chicken dance. Say **"done"** afterwards to freeze the clock and get a free hint. Say "no" and you lose 15 seconds.
- **Taunts you** when you make a mistake or shake the bomb, and counts down the final seconds.

## How to play
1. Say **"let's play"** or press **A**. All 4 bomb wires must be plugged in.
2. **WIRES:** solve the riddle and pull the right colored wire.
3. **CODE:** solve 4 small math problems (each answer is one digit), type the digits, then press **#**. Press **\*** to clear.
4. **CARDS** (only if the RFID reader is wired): tap the card and fob in the order the clue gives.
- 3 strikes or running out of time and it explodes. Press **D** to buy a hint. Say **"play again"** to restart.

## Setup (Mac)
```bash
./setup.sh            # one time: Python packages, voice, local AI (~2.5 GB download)
```
1. In the Arduino IDE, install these libraries: **Keypad**, **LiquidCrystal**, **MFRC522**, **LedControl**, **Servo**.
2. Upload `firmware/defuse/defuse.ino` (Board: Arduino Mega 2560).
3. Close the Serial Monitor, then double-click **START.command**. Allow microphone access when asked.

`VOICE=Daniel ./START.command` uses a Mac voice instead of the neural voice. `host/defuse_host.py --sim` runs the whole game with no hardware.

## Files
| Path | What it is |
|---|---|
| `firmware/defuse/defuse.ino` | The Mega game. It also runs a standalone game without a laptop. |
| `host/defuse_host.py` | Entry point: command-line options, wires the modules together. |
| `host/defuse/game_master.py` | **Start here.** Game logic: puzzles, AI decisions, dares, restarts. |
| `host/defuse/llm.py` | AI brain (local Ollama, Claude CLI, Anthropic or OpenAI). |
| `host/defuse/ears.py` | Always-on mic and local speech-to-text (faster-whisper). |
| `host/defuse/voice.py` | Neural voice (Piper), falling back to the macOS `say` command. |
| `host/defuse/bomb_link.py` | USB serial link to the Mega, plus `SimBomb` for testing without hardware. |
| `host/defuse/content.py` | Offline riddles and lines. |
| `host/defuse/config.py` | Constants and the villain's persona. |
| `START.command` | Starts the AI brain and the host. |
| `diagram/WIRING_DIAGRAM.html` | Picture-based wiring guide. |
| `WIRING.md` | Pin-by-pin wiring list. |
| `firmware/hwtest*` | Hardware tests (keypad, LCD, wires, buzzer, LEDs). |

## Hardware used
Mega 2560, LCD1602, 4×4 keypad, active buzzer, 3 red LEDs, 4 jumper "bomb wires", and a 10K potentiometer. Optional parts: 4-digit 7-segment display, MAX7219 8×8 face, RC522 RFID, GY-521, HC-SR04, RGB LED and SG90 servo.

Keypad on this build: rows on pins 36, 22, 24, 26 and columns on pins 28, 30, 32, 34.

## Serial protocol (115200 baud)
- Mega → laptop: `BOOT`, `READY`, `ARM`, `START s`, `STAGE n`, `WIRE i OK|BAD`, `CODE xxxx OK|BAD`, `TAG i OK|BAD`, `STRIKE n why`, `SHAKE`, `NEAR cm`, `HINT n`, `TICK s`, `WIN s`, `BOOM why`, `NEED_WIRE i`
- Laptop → Mega: `HELLO`, `ABORT`, `NEW secs wire code seq`, `GO`, `MSG text`, `TIME ±s`, `FREEZE s`, `SKIP`, `STRIKE`, `FACE name ms`, `TALK ms`
