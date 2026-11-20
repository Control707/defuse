#!/usr/bin/env python3
"""Builds DEFUSE_presentation.pptx for the IEEE CS Track Game Sprint."""
import os
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "DEFUSE_presentation.pptx")

BG = RGBColor(0x0E, 0x11, 0x16)
PANEL = RGBColor(0x17, 0x1C, 0x24)
CODEBG = RGBColor(0x0A, 0x0D, 0x12)
TEXT = RGBColor(0xE8, 0xEA, 0xED)
MUTED = RGBColor(0x9A, 0xA4, 0xB2)
RED = RGBColor(0xFF, 0x4D, 0x4D)
AMBER = RGBColor(0xFF, 0xB0, 0x20)
GREEN = RGBColor(0x3D, 0xDC, 0x84)
BLUE = RGBColor(0x4D, 0xA3, 0xFF)
PURPLE = RGBColor(0xB3, 0x88, 0xFF)
CMT = RGBColor(0x6A, 0x99, 0x55)
KW = RGBColor(0xC5, 0x86, 0xC0)
STR = RGBColor(0xCE, 0x91, 0x78)

FONT = "Helvetica Neue"
MONO = "Menlo"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
W, H = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]
page = [0]


# ------------------------------------------------------------------ helpers
def new_slide(title=None, kicker=None):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    page[0] += 1
    if title:
        bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(0.52), Inches(0.09), Inches(0.62))
        bar.fill.solid(); bar.fill.fore_color.rgb = RED; bar.line.fill.background()
        if kicker:
            text(s, kicker.upper(), 0.85, 0.32, 10, 0.3, 12, AMBER, bold=True, spacing=2)
        text(s, title, 0.85, 0.5, 11.8, 0.75, 32, TEXT, bold=True)
    # footer
    text(s, "DEFUSE  ·  IEEE CS Track Game Sprint", 0.6, 7.05, 6, 0.3, 10, MUTED)
    text(s, str(page[0]), 12.2, 7.05, 0.55, 0.3, 10, MUTED, align=PP_ALIGN.RIGHT)
    return s


def text(s, t, x, y, w, h, size=18, color=TEXT, bold=False, align=PP_ALIGN.LEFT, font=FONT,
         anchor=MSO_ANCHOR.TOP, spacing=None):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    lines = t.split("\n") if isinstance(t, str) else t
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = ln
        r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(size), bold, color, font
        if spacing:
            r.font._element.set("spc", str(spacing * 100))
    return tb


def rich(s, paras, x, y, w, h, size=17, gap=8):
    """paras: list of lists of (text, color, bold) runs, or ("•", ...) bullets."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, runs in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        for t, c, b in runs:
            r = p.add_run()
            r.text = t
            r.font.size, r.font.color.rgb, r.font.bold, r.font.name = Pt(size), c, b, FONT
    return tb


def bullets(s, items, x, y, w, h, size=17, color=TEXT, dot=RED, gap=9):
    paras = []
    for it in items:
        if isinstance(it, tuple):
            head, body = it
            paras.append([("▸ ", dot, True), (head, color, True), (body, MUTED, False)])
        else:
            paras.append([("▸ ", dot, True), (it, color, False)])
    return rich(s, paras, x, y, w, h, size, gap)


def panel(s, x, y, w, h, color=PANEL, border=None, radius=True):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                             Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shp.adjustments[0] = 0.06
    shp.fill.solid(); shp.fill.fore_color.rgb = color
    if border:
        shp.line.color.rgb = border; shp.line.width = Pt(1.5)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def card(s, x, y, w, h, title, body, accent=RED, tsize=18, bsize=14):
    panel(s, x, y, w, h)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y + 0.18), Inches(0.07), Inches(h - 0.36))
    bar.fill.solid(); bar.fill.fore_color.rgb = accent; bar.line.fill.background()
    text(s, title, x + 0.25, y + 0.18, w - 0.4, 0.4, tsize, accent, bold=True)
    text(s, body, x + 0.25, y + 0.62, w - 0.4, h - 0.75, bsize, TEXT)


def image(s, path, x, y, w=None, h=None):
    kw = {}
    if w: kw["width"] = Inches(w)
    if h: kw["height"] = Inches(h)
    return s.shapes.add_picture(path, Inches(x), Inches(y), **kw)


def code(s, lines, x, y, w, h, size=11.5, label=None):
    """Draws a code panel. Comments green, keywords pink, strings orange."""
    panel(s, x, y, w, h, CODEBG, RGBColor(0x2A, 0x31, 0x3C))
    top = y + 0.12
    if label:
        for i, c in enumerate((RED, AMBER, GREEN)):
            dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.18 + i * 0.2), Inches(y + 0.14), Inches(0.12), Inches(0.12))
            dot.fill.solid(); dot.fill.fore_color.rgb = c; dot.line.fill.background()
        text(s, label, x + 0.85, y + 0.08, w - 1, 0.25, 11, MUTED, font=MONO)
        top = y + 0.42
    tb = s.shapes.add_textbox(Inches(x + 0.2), Inches(top), Inches(w - 0.35), Inches(h - (top - y) - 0.1))
    tf = tb.text_frame
    tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    kws = ("void ", "if ", "else", "for ", "return", "def ", "elif ", "while ", "not ", "and ", "self.", "int ", "long ", "bool ")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.0
        # split comment
        cpos = -1
        for marker in ("//", "#"):
            j = ln.find(marker)
            if j >= 0 and (marker != "#" or not ln.strip().startswith("#include")) and ln[:j].count('"') % 2 == 0:
                cpos = j if cpos < 0 else min(cpos, j)
        body, cmt = (ln[:cpos], ln[cpos:]) if cpos >= 0 else (ln, "")
        # crude highlighting: strings + leading keyword
        segs, cur, instr = [], "", False
        for ch in body:
            if ch == '"':
                if instr:
                    cur += ch; segs.append((cur, STR)); cur = ""; instr = False; continue
                segs.append((cur, TEXT)); cur = ch; instr = True; continue
            cur += ch
        segs.append((cur, STR if instr else TEXT))
        for t, c in segs:
            if not t:
                continue
            if c is TEXT:
                stripped = t.lstrip()
                k = next((k for k in kws if stripped.startswith(k)), None)
                if k:
                    lead = t[: len(t) - len(stripped)]
                    for tt, cc in ((lead, TEXT), (k, KW), (stripped[len(k):], TEXT)):
                        if tt:
                            r = p.add_run(); r.text = tt; r.font.color.rgb = cc; r.font.size = Pt(size); r.font.name = MONO
                    continue
            r = p.add_run(); r.text = t; r.font.color.rgb = c; r.font.size = Pt(size); r.font.name = MONO
        if cmt:
            r = p.add_run(); r.text = cmt; r.font.color.rgb = CMT; r.font.size = Pt(size); r.font.name = MONO; r.font.italic = True
        if not ln:
            r = p.add_run(); r.text = " "; r.font.size = Pt(size); r.font.name = MONO
    return tb


def notes(s, t):
    s.notes_slide.notes_text_frame.text = t


# ================================================================== 1. TITLE
s = new_slide()
glow = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(7.6), Inches(-1.2), Inches(7.5), Inches(7.5))
glow.fill.solid(); glow.fill.fore_color.rgb = RGBColor(0x2A, 0x10, 0x12); glow.line.fill.background()
image(s, os.path.join(HERE, "photo_overview.jpg"), 7.35, 1.05, w=5.4)
text(s, "IEEE CS TRACK  ·  GAME SPRINT", 0.8, 1.35, 6.5, 0.4, 14, AMBER, bold=True, spacing=3)
text(s, "DEFUSE", 0.75, 1.8, 6.5, 1.5, 96, RED, bold=True)
text(s, "A talking AI bomb you defuse with your hands and your voice", 0.8, 3.35, 6.2, 1.0, 24, TEXT)
rich(s, [[("Built on the ", MUTED, False), ("ELEGOO Mega 2560", TEXT, True), (" kit  ·  AI villain ", MUTED, False),
          ("NINE-VOLT", RED, True), (" runs 100% offline", MUTED, False)]], 0.8, 4.55, 6.3, 0.8, 16)
panel(s, 0.8, 5.5, 5.9, 0.75, PANEL, RGBColor(0x2A, 0x31, 0x3C))
text(s, "github.com/Control707/defuse", 1.05, 5.5, 5.5, 0.75, 20, BLUE, bold=True, anchor=MSO_ANCHOR.MIDDLE, font=MONO)
text(s, "Zakaria Sherif", 0.8, 6.45, 6, 0.4, 14, MUTED)
notes(s, "DEFUSE: a physical bomb built from the ELEGOO kit, controlled by an AI villain that you talk to out loud.")

# ================================================================== 2. GAME OVERVIEW
s = new_slide("Game Overview", "what is DEFUSE?")
text(s, "A bomb is ticking on the table. An AI villain named NINE-VOLT lives inside it. "
        "It writes new riddles every round, talks to you out loud, and decides your fate based on what you say to it.",
     0.85, 1.4, 11.8, 0.9, 19, TEXT)
card(s, 0.85, 2.55, 3.8, 1.95, "🎯  Goal", "Defuse the bomb before the timer hits 0:00. Three mistakes and it explodes.", RED)
card(s, 4.77, 2.55, 3.8, 1.95, "🗣️  Talk to it", "Flatter it for extra time. Insult it and lose time. Say \"please\" 3× and it makes you do a dare.", PURPLE)
card(s, 8.69, 2.55, 3.8, 1.95, "🔁  Never the same", "The AI invents new riddles every round, and each round is 20 s shorter (down to 2 min).", AMBER)
text(s, "GENRE", 0.85, 4.85, 3, 0.3, 12, AMBER, bold=True, spacing=2)
text(s, "Escape-room / party game with physical controls", 0.85, 5.15, 5.6, 0.4, 16, TEXT)
text(s, "PLAYERS", 0.85, 5.65, 3, 0.3, 12, AMBER, bold=True, spacing=2)
text(s, "1 defuser, with the crowd shouting advice", 0.85, 5.95, 5.6, 0.4, 16, TEXT)
text(s, "AI ROLE", 6.9, 4.85, 3, 0.3, 12, AMBER, bold=True, spacing=2)
text(s, "AI is part of the game: villain, puzzle writer and game master. AI also helped build it.",
     6.9, 5.15, 5.6, 0.8, 16, TEXT)
text(s, "ROUND LENGTH", 6.9, 5.95, 3, 0.3, 12, AMBER, bold=True, spacing=2)
text(s, "4 minutes, shrinking each round", 6.9, 6.25, 5.6, 0.4, 16, TEXT)

# ================================================================== 3. RULES & MECHANICS
s = new_slide("Rules & Core Mechanics", "how to play")
stages = [("1", "WIRES", "Listen to the riddle (\"the color of the sky\") and pull the matching jumper wire out.", AMBER),
          ("2", "CODE", "Solve 4 tiny math problems (\"9 plus 0, 3 minus 2…\"). Type the 4 digits on the keypad, press #.", AMBER),
          ("3", "CARDS", "Optional stage: tap RFID card and fob in the order the clue gives.", MUTED)]
for i, (n, name, body, col) in enumerate(stages):
    x = 0.85 + i * 4.0
    panel(s, x, 1.45, 3.75, 2.15)
    circ = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.25), Inches(1.65), Inches(0.6), Inches(0.6))
    circ.fill.solid(); circ.fill.fore_color.rgb = col; circ.line.fill.background()
    text(s, n, x + 0.25, 1.65, 0.6, 0.6, 22, BG, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, name, x + 1.0, 1.72, 2.6, 0.5, 22, col, bold=True)
    text(s, body, x + 0.25, 2.45, 3.3, 1.1, 14.5, TEXT)
text(s, "RULES", 0.85, 3.9, 4, 0.3, 12, RED, bold=True, spacing=2)
bullets(s, [("Start: ", "say \"let's play\" or press A. All 4 wires must be plugged in."),
            ("Strikes: ", "a wrong wire or wrong code = 1 strike (red LED + buzzer). 3 strikes = BOOM."),
            ("Timer: ", "ticks faster under 30 s and 10 s. Reaching 0:00 = BOOM."),
            ("Hints: ", "press D to buy a hint for 15 seconds.")], 0.85, 4.25, 5.9, 2.6, 15)
text(s, "AI MECHANICS", 6.95, 3.9, 4, 0.3, 12, PURPLE, bold=True, spacing=2)
bullets(s, [("Bargain: ", "the AI can add or remove up to ±30 s based on what you say."),
            ("Mercy & punishment: ", "it can freeze the clock, give a hint, skip a puzzle or add a strike."),
            ("Dares: ", "say \"please\" 3× → \"do a chicken dance\". Say \"done\" = clock frozen 20 s + free hint. Refuse = −15 s."),
            ("Replay: ", "say \"play again\" after a win or a BOOM.")], 6.95, 4.25, 5.6, 2.6, 15, dot=PURPLE)

# ================================================================== 4. STATE MACHINE
s = new_slide("State Machine", "how the bomb thinks")
image(s, os.path.join(HERE, "state_machine.png"), 0.6, 1.35, w=9.4)
panel(s, 10.2, 1.45, 2.55, 5.1)
text(s, "STATES", 10.42, 1.65, 2.2, 0.3, 12, AMBER, bold=True, spacing=2)
rich(s, [[("IDLE → AI THINKING → PLAYING → DEFUSED or BOOM. ", TEXT, True),
          ("PLAYING has 3 sub-states: WIRES, CODE, CARDS.", MUTED, False)]], 10.42, 2.0, 2.15, 2.0, 13.5)
text(s, "TRANSITIONS", 10.42, 4.0, 2.2, 0.3, 12, AMBER, bold=True, spacing=2)
rich(s, [[("Player moves", TEXT, True), (" and ", MUTED, False), ("AI commands", PURPLE, True),
          (" (TIME, FREEZE, SKIP, STRIKE) both change state. ABORT + GO restarts.", MUTED, False)]], 10.42, 4.35, 2.15, 2.1, 13.5)

# ================================================================== 5. FLOWCHART
s = new_slide("Game Flowchart", "one round, start to finish")
image(s, os.path.join(HERE, "flowchart.png"), 1.55, 1.3, h=5.6)

# ================================================================== 6. ELEGOO KIT
s = new_slide("ELEGOO Kit Integration", "parts used & what each one does")
image(s, os.path.join(HERE, "photo_lcd.jpg"), 0.85, 1.35, h=5.5)
rows = [("Mega 2560", "The bomb's brain: runs the timer, the state machine and the USB link to the AI", RED),
        ("LCD1602 + 10K pot", "Shows the stage, the countdown and the scrolling riddle. The knob sets contrast", BLUE),
        ("4×4 membrane keypad", "Type the code. # = submit, * = clear, A = arm, D = buy a hint", BLUE),
        ("4 jumper wires", "The \"bomb wires\". Each one grounds an analog pin; pulling it = cutting it", AMBER),
        ("Active buzzer", "Ticks every second, faster near the end, screams on BOOM", AMBER),
        ("3 red LEDs + 220Ω", "Strike counter: one LED per mistake", RED),
        ("Breadboard + power module", "Shared 5V / GND rails for every part", MUTED),
        ("USB cable", "Serial link to the laptop AI (115200 baud)", MUTED)]
y = 1.35
for name, what, col in rows:
    panel(s, 5.15, y, 7.5, 0.6)
    dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(5.32), Inches(y + 0.23), Inches(0.14), Inches(0.14))
    dot.fill.solid(); dot.fill.fore_color.rgb = col; dot.line.fill.background()
    text(s, name, 5.6, y, 2.35, 0.6, 14, TEXT, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, what, 7.95, y, 4.6, 0.6, 12.5, MUTED, anchor=MSO_ANCHOR.MIDDLE)
    y += 0.69

# ================================================================== 7. ELEGOO KIT 2 (wiring + optional)
s = new_slide("ELEGOO Kit Integration: Wiring", "how it connects")
image(s, os.path.join(HERE, "architecture.png"), 0.85, 1.3, w=7.4)
text(s, "PIN MAP", 8.55, 1.35, 4, 0.3, 12, AMBER, bold=True, spacing=2)
code(s, ["Keypad rows   36, 22, 24, 26",
         "Keypad cols   28, 30, 32, 34",
         "LCD RS,E      38, 40",
         "LCD D4-D7     42, 44, 46, 48",
         "Bomb wires    A0 A1 A2 A3 -> GND",
         "Strike LEDs   A8 A9 A10",
         "Buzzer        8"], 8.55, 1.7, 4.1, 2.35, 12.5)
text(s, "BUILT IN, READY TO PLUG IN", 8.55, 4.45, 4.2, 0.3, 12, PURPLE, bold=True, spacing=2)
text(s, "Firmware already supports these. They're detected at boot and skipped if missing:", 8.55, 4.78, 4.1, 0.6, 12.5, MUTED)
bullets(s, ["4-digit 7-segment timer", "MAX7219 8×8 villain face", "RC522 RFID card stage",
            "GY-521 shake = −10 s", "HC-SR04 sees people walk up", "RGB status light · SG90 lid servo"],
        8.55, 5.4, 4.1, 1.6, 12.5, dot=PURPLE, gap=2)
text(s, "Bomb wires use INPUT_PULLUP: plugged into GND = LOW; pulled out = HIGH = \"cut\".", 0.85, 5.35, 7.4, 0.6, 13, MUTED)
text(s, "The laptop never touches pins. It only sends text commands; the Mega decides what's legal.", 0.85, 5.8, 7.4, 0.6, 13, MUTED)

# ================================================================== 8. CODE OVERVIEW
s = new_slide("Code Overview", "two programs talking over USB")
card(s, 0.85, 1.4, 5.8, 2.1, "firmware/defuse/defuse.ino  ·  C++ · 756 lines",
     "Runs on the Mega. Owns the timer and the state machine, reads the keypad, wires and sensors, "
     "drives the LCD, buzzer and LEDs. Plays a full offline game if the laptop is unplugged.", RED, 16, 14)
card(s, 6.85, 1.4, 5.8, 2.1, "host/defuse_host.py  ·  Python · 912 lines",
     "Runs on the laptop. Ears (Whisper), brain (Llama 3.2 via Ollama) and voice (Piper). "
     "The GameMaster turns AI decisions into bomb commands, and clamps them so the AI can't break the game.", PURPLE, 16, 14)
text(s, "THE PROTOCOL (plain text lines, 115200 baud)", 0.85, 3.85, 8, 0.3, 12, AMBER, bold=True, spacing=2)
code(s, ["Mega -> laptop:  START 240 | STAGE 1 | WIRE 2 BAD | STRIKE 1 wire | TICK 30 | BOOM time",
         "laptop -> Mega:  NEW 240 3 9519 101 | GO | MSG <riddle> | TIME +20 | FREEZE 20 | SKIP | ABORT"],
     0.85, 4.2, 11.8, 0.85, 13.5)
bullets(s, [("Safety rule: ", "Python picks every answer (wire, code), then the AI only writes the clues. So an AI mistake can never make a puzzle impossible."),
            ("Clamping: ", "AI time changes are capped at ±30 s and +60 s total per round."),
            ("Fallback: ", "if the AI is too slow (>20 s) or unplugged, the Mega runs its own offline puzzle.")], 0.85, 5.35, 11.8, 1.6, 15)

# ================================================================== 9. CODE: firmware
s = new_slide("Commented Code: Firmware (C++)", "defuse.ino")
code(s, ["// Main loop: never blocks, so everything",
         "// (timer, keypad, LCD) stays responsive",
         "void loop() {",
         "  pollSerial();   // AI commands: TIME, FREEZE...",
         "  pollKeypad();   // A=arm, digits+#=code, D=hint",
         "  pollWires();    // was a bomb wire pulled?",
         "  pollRfid(); pollMpu(); pollSonar(); // optional",
         "",
         "  // AI too slow? play an offline puzzle instead",
         "  if (state == G_WAIT_HOST &&",
         "      millis() - waitHostSince > 20000) {",
         "    randomPuzzle(); startGame();",
         "  }",
         "  updateTimerAndSound(); // countdown + BOOM at 0",
         "  updateFace();",
         "  if (lcdDirty) drawLcd();",
         "}"], 0.85, 1.35, 5.85, 5.55, 12, label="loop()")
code(s, ["// A wire is 'cut' when its pin reads HIGH",
         "// for 20 loops in a row (debounce)",
         "void pollWires() {",
         "  for (int i = 0; i < 4; i++) {",
         "    if (wireCut[i]) continue;",
         "    if (digitalRead(WIRE_PINS[i]) == HIGH)",
         "      wireStable[i]++;",
         "    else wireStable[i] = 0;",
         "    if (wireStable[i] >= 20) {",
         "      wireCut[i] = true;",
         "      if (stage == S_WIRES && i == solWire) {",
         "        evt(\"WIRE OK\");       // tell the AI",
         "        enterStage(S_CODE);   // next puzzle",
         "      } else strike(\"wire\");  // wrong wire!",
         "    }",
         "  }",
         "}"], 6.9, 1.35, 5.75, 3.95, 11, label="pollWires()")
code(s, ["// AI command FREEZE <s>: stop the clock",
         "if (!strcmp(cmd, \"FREEZE\") && rest) {",
         "  freezeUntil = millis() + atol(rest) * 1000UL;",
         "  rgb(0, 80, 255);       // status light: blue",
         "}"], 6.9, 5.45, 5.75, 1.45, 11, label="handleCommand()")

# ================================================================== 10. CODE: AI
s = new_slide("Commented Code: AI Game Master (Python)", "defuse_host.py")
code(s, ["# Everything the player says goes through here",
         "def player_says(self, text):",
         "    # 'please' x3 -> the AI demands a ridiculous dare",
         "    n = len(re.findall(r\"\\bplease\\b\", text.lower()))",
         "    if n: self.beg(n, \"said please\")",
         "",
         "    # Ask the local LLM to act as game master; reply is JSON",
         "    j = self.llm.chat_json(PERSONA, f\"{self.context()} ...\")",
         "    action = j.get(\"action\", \"none\")",
         "    delta = max(-30, min(30, int(j.get(\"seconds\", 0))))  # clamp",
         "",
         "    self.voice.say(j[\"say\"])          # speak the reply out loud",
         "    if delta: self.send(f\"TIME {delta}\")   # change the bomb timer",
         "    if action == \"hint\":   self.give_hint(self.stage, free=True)",
         "    elif action == \"freeze\": self.send(\"FREEZE 15\")",
         "    elif action == \"skip\":   self.send(\"SKIP\")",
         "    elif action == \"strike\": self.send(\"STRIKE\")",
         "    elif action == \"dare\":   self.start_dare()"], 0.85, 1.35, 7.0, 5.55, 12, label="GameMaster.player_says()")
code(s, ["# Python picks the answers; AI only",
         "# writes the riddles -> always solvable",
         "def new_puzzle(self):",
         "    wire = random.randrange(4)",
         "    code = four_random_digits()",
         "    req = f\"The answer is {code}.",
         "           Write a clue for it...\"",
         "    j = self.llm.chat_json(PERSONA, req)",
         "    # reject clues that leak the answer",
         "    if code in j[\"code_say\"]: use offline"], 8.05, 1.35, 4.6, 3.55, 11.5, label="new_puzzle()  (simplified)")
code(s, ["# Dare done -> reward the player",
         "if \"done\" in text:",
         "    self.send(\"FREEZE 20\")",
         "    self.give_hint(stage, free=True)",
         "elif \"no\" in text:",
         "    self.send(\"TIME -15\")  # coward!"], 8.05, 5.05, 4.6, 1.85, 11.5, label="resolve_dare()  (simplified)")

# ================================================================== 11. GITHUB
s = new_slide("GitHub Repository", "all code, diagrams and tests")
panel(s, 0.85, 1.45, 11.8, 1.05, PANEL, RGBColor(0x2A, 0x31, 0x3C))
text(s, "https://github.com/Control707/defuse", 1.15, 1.45, 8.6, 1.05, 26, BLUE, bold=True, font=MONO, anchor=MSO_ANCHOR.MIDDLE)
text(s, "public  ·  branch main", 9.2, 1.45, 3.2, 1.05, 15, MUTED, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
code(s, ["defuse/",
         "├── firmware/defuse/defuse.ino   # Mega game",
         "├── firmware/hwtest*/            # hardware tests",
         "├── host/defuse_host.py          # AI villain",
         "├── host/requirements.txt        # Python deps",
         "├── diagram/WIRING_DIAGRAM.html  # wiring guide",
         "├── WIRING.md                    # pin list",
         "├── setup.sh                     # one-time install",
         "├── START.command                # double-click",
         "└── README.md"], 0.85, 2.75, 7.2, 3.75, 13, label="repo layout")
text(s, "HOW TO RUN IT", 8.35, 2.8, 4.3, 0.3, 12, AMBER, bold=True, spacing=2)
rich(s, [[("1  ", RED, True), ("./setup.sh", BLUE, True), (" downloads the AI model, speech model and voice (big files are not in git)", MUTED, False)],
         [("2  ", RED, True), ("Upload ", TEXT, False), ("defuse.ino", BLUE, True), (" to the Mega with the Arduino IDE", MUTED, False)],
         [("3  ", RED, True), ("Double-click ", TEXT, False), ("START.command", BLUE, True), (" and say \"let's play\"", MUTED, False)],
         [("No hardware? ", AMBER, True), ("defuse_host.py --sim", BLUE, True), (" plays the whole game in the terminal.", MUTED, False)]],
     8.35, 3.2, 4.3, 3.3, 14, 12)

# ================================================================== 12. LIMITATIONS & CHALLENGES
s = new_slide("Limitations & Challenges", "what was hard and what we'd improve")
text(s, "CHALLENGES WE SOLVED", 0.85, 1.35, 6, 0.3, 12, AMBER, bold=True, spacing=2)
for i, (t, b) in enumerate([
        ("Keypad top row was dead", "1, 2, 3, A did nothing. We wrote a pin-scanner sketch that logged which pins touched, and found the 8th ribbon wire sitting on a 5V pin instead of pin 36."),
        ("Bomb couldn't restart after BOOM", "The AI said \"Initializing\" but the timer never started. Fix: the host sends ABORT before every new game, then waits for a START confirmation."),
        ("Small local AI is bad at math", "Llama 3.2 3B wrote wrong arithmetic clues. Fix: Python generates the math and the answers; the AI only writes the flavor text.")]):
    card(s, 0.85, 1.7 + i * 1.75, 6.0, 1.6, t, b, AMBER, 16, 12.5)
text(s, "LIMITATIONS", 7.1, 1.35, 6, 0.3, 12, RED, bold=True, spacing=2)
for i, (t, b) in enumerate([
        ("AI response delay", "Each AI reply takes 3–5 s on a laptop CPU, so conversation has pauses."),
        ("Not all kit parts wired yet", "Firmware supports the RFID, 8×8 face, servo and 7-segment display, but they weren't connected in time."),
        ("Noisy rooms", "The mic can mishear in a loud room; typing to the bomb still works as a backup."),
        ("Needs a laptop for AI", "The Mega has no Wi-Fi. Unplugged, it falls back to a simpler offline game.")]):
    card(s, 7.1, 1.7 + i * 1.31, 5.55, 1.2, t, b, RED, 15, 12)

# ================================================================== 13. TOOLS & RESOURCES (last)
s = new_slide("Tools & Resources", "everything used to build DEFUSE")
cols = [
    ("HARDWARE", RED, ["ELEGOO Mega 2560 Most Complete Starter Kit", "LCD1602, 4×4 keypad, active buzzer", "LEDs, resistors, 10K potentiometer", "830-point breadboard + power module", "Jumper wires, USB cable"]),
    ("ARDUINO / C++", AMBER, ["Arduino IDE 2 + arduino-cli", "LiquidCrystal (LCD)", "Keypad (Mark Stanley)", "MFRC522 (RFID) · LedControl (MAX7219)", "Servo · Wire · SPI · EEPROM"]),
    ("AI & PYTHON", PURPLE, ["Python 3 · pyserial", "Ollama + Meta Llama 3.2 3B (local LLM)", "faster-whisper (speech → text)", "Piper TTS, en_US-ryan voice", "sounddevice · numpy · ffmpeg"]),
    ("DEV & DESIGN", BLUE, ["Claude Code (AI coding assistant)", "Git + GitHub (Control707/defuse)", "SVG wiring & state diagrams", "python-pptx (these slides)", "macOS Terminal"])]
for i, (h, c, items) in enumerate(cols):
    x = 0.85 + i * 3.0
    panel(s, x, 1.4, 2.8, 4.45)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(1.4), Inches(2.8), Inches(0.08))
    bar.fill.solid(); bar.fill.fore_color.rgb = c; bar.line.fill.background()
    text(s, h, x + 0.22, 1.65, 2.4, 0.35, 14, c, bold=True, spacing=2)
    bullets(s, items, x + 0.22, 2.15, 2.45, 4.5, 13, dot=c, gap=10)

text(s, "AI was used in two ways: inside the game (local LLM villain, speech-to-text, neural voice) and to help build it (Claude Code for code, wiring diagrams and debugging).",
     0.85, 6.1, 11.8, 0.7, 14, MUTED)

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides))
