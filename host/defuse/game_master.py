"""GameMaster: turns bomb events and player speech into AI decisions and bomb commands."""
import random
import re
import threading
import time

from .config import PERSONA, STAGE_NAMES, TAG_NAMES, WIRE_COLORS
from .content import OFFLINE_RIDDLES, pick
from .util import log


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
