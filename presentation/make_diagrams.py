#!/usr/bin/env python3
"""Draws the DEFUSE state machine, flowchart and architecture diagrams as SVG (dark slide theme)."""
import html, os

OUT = os.path.dirname(os.path.abspath(__file__))
BG, PANEL, TEXT, MUTED = "#0E1116", "#171C24", "#E8EAED", "#9AA4B2"
RED, AMBER, GREEN, BLUE, PURPLE = "#FF4D4D", "#FFB020", "#3DDC84", "#4DA3FF", "#B388FF"


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.p = w, h, []

    def add(self, s):
        self.p.append(s)

    def text(self, x, y, s, size=20, color=TEXT, weight="normal", anchor="middle", italic=False):
        lines = s.split("\n")
        y0 = y - (len(lines) - 1) * size * 0.62
        for i, ln in enumerate(lines):
            w = weight if i == 0 else "normal"
            sz = size if i == 0 else size * 0.78
            col = color if i == 0 else MUTED
            self.add(f'<text x="{x}" y="{y0 + i * size * 1.24 + size * 0.35}" font-size="{sz:.0f}" fill="{col}" '
                     f'font-weight="{w}" text-anchor="{anchor}"{" font-style=\"italic\"" if italic else ""}>{html.escape(ln)}</text>')

    def label(self, x, y, s, color=AMBER, size=16, anchor="middle"):
        for i, ln in enumerate(s.split("\n")):
            self.add(f'<text x="{x}" y="{y + i * size * 1.2}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
                     f'font-weight="bold">{html.escape(ln)}</text>')

    def box(self, x, y, w, h, s, color=BLUE, size=22, dashed=False, fill=PANEL, rx=16):
        d = ' stroke-dasharray="10 7"' if dashed else ""
        self.add(f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                 f'stroke="{color}" stroke-width="3"{d}/>')
        self.text(x, y, s, size, color, "bold")

    def diamond(self, x, y, w, h, s, color=AMBER, size=19):
        pts = f"{x},{y - h / 2} {x + w / 2},{y} {x},{y + h / 2} {x - w / 2},{y}"
        self.add(f'<polygon points="{pts}" fill="{PANEL}" stroke="{color}" stroke-width="3"/>')
        self.text(x, y, s, size, color, "bold")

    def arrow(self, pts, color=MUTED, dashed=False, width=3):
        d = ' stroke-dasharray="9 7"' if dashed else ""
        mk = {MUTED: "m", GREEN: "g", RED: "r", AMBER: "a", BLUE: "b", PURPLE: "p"}.get(color, "m")
        path = "M" + " L".join(f"{a},{b}" for a, b in pts)
        self.add(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}"{d} marker-end="url(#{mk})"/>')

    def save(self, name):
        markers = "".join(
            f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            for k, c in (("m", MUTED), ("g", GREEN), ("r", RED), ("a", AMBER), ("b", BLUE), ("p", PURPLE)))
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
               f'font-family="Helvetica, Arial, sans-serif"><defs>{markers}</defs>'
               f'<rect width="100%" height="100%" fill="{BG}"/>' + "".join(self.p) + "</svg>")
        path = os.path.join(OUT, name)
        open(path, "w").write(svg)
        return path


# ---------------------------------------------------------------- state machine
def state_machine():
    s = Svg(1600, 900)
    # initial pseudo-state
    s.add(f'<circle cx="40" cy="450" r="14" fill="{TEXT}"/>')
    s.arrow([(56, 450), (98, 450)])
    s.label(60, 418, "power on", MUTED, 13)
    s.box(210, 450, 220, 120, "IDLE\nLCD: \"Press A\"", BLUE)
    s.box(530, 450, 240, 130, "AI THINKING\nLLM writes riddles\nPython picks answers", PURPLE, 22)
    # PLAYING super-state
    s.add(f'<rect x="740" y="150" width="490" height="610" rx="24" fill="#12161D" stroke="{AMBER}" stroke-width="3"/>')
    s.label(985, 188, "PLAYING  ·  timer running", AMBER, 22)
    s.box(985, 290, 320, 96, "1 · WIRES\npull the right wire", AMBER, 22)
    s.box(985, 455, 320, 96, "2 · CODE\nsolve math, type 4 digits + #", AMBER, 22)
    s.box(985, 620, 320, 96, "3 · CARDS\nscan RFID tags in order", AMBER, 22, dashed=True)
    s.arrow([(985, 338), (985, 404)], AMBER)
    s.label(1000, 378, "right wire", AMBER, 15, "start")
    s.arrow([(985, 503), (985, 569)], AMBER)
    s.label(1000, 543, "right code", AMBER, 15, "start")
    s.label(985, 712, "any stage: wrong move = strike +1\nAI can send TIME ±30 · FREEZE · SKIP · STRIKE", MUTED, 15)
    # end states
    s.box(1440, 260, 240, 120, "DEFUSED\nservo lid opens\nAI sulks", GREEN, 24)
    s.box(1440, 690, 240, 120, "BOOM\nbuzzer + skull face\nAI gloats", RED, 24)
    # transitions
    s.arrow([(320, 450), (406, 450)], BLUE)
    s.label(363, 420, "press A or", BLUE, 15)
    s.label(363, 488, "\"let's play\"", BLUE, 15)
    s.arrow([(650, 450), (700, 450), (700, 290), (822, 290)], PURPLE)
    s.label(695, 254, "NEW + GO", PURPLE, 16, "end")
    s.label(560, 553, "AI too slow (>20 s)", MUTED, 13, "start"); s.label(560, 571, "→ offline puzzle", MUTED, 13, "start")
    s.arrow([(1145, 620), (1265, 620), (1265, 260), (1316, 260)], GREEN)
    s.add(f'<path d="M1145,455 L1265,455" stroke="{GREEN}" stroke-width="3" stroke-dasharray="9 7" fill="none"/>')
    s.label(1278, 410, "solved", GREEN, 16, "start")
    s.label(1278, 480, "(no RFID:\ncode is last)", MUTED, 13, "start")
    s.arrow([(1230, 700), (1316, 700)], RED)
    s.label(1273, 744, "3rd strike\nor 0:00", RED, 15)
    s.arrow([(1440, 198), (1440, 85), (530, 85), (530, 383)], GREEN, dashed=True)
    s.label(985, 72, "say \"play again\" or press A  →  ABORT + new puzzle", GREEN, 17)
    s.arrow([(1440, 752), (1440, 840), (530, 840), (530, 517)], RED, dashed=True)
    s.label(985, 870, "say \"play again\" or press A  →  ABORT + new puzzle", RED, 17)
    return s.save("state_machine.svg")


# ---------------------------------------------------------------- flowchart
def flowchart():
    s = Svg(1600, 940)
    s.box(150, 110, 230, 100, "START\nsay \"let's play\"\nor press A", BLUE, 22, rx=50)
    s.diamond(450, 110, 230, 150, "All 4 wires\nplugged in?", AMBER, 20)
    s.box(450, 300, 240, 80, "AI: \"Plug the red\nwire back in\"", MUTED, 18)
    s.box(790, 110, 300, 110, "AI writes riddles\nPython picks the answers\n(always solvable)", PURPLE, 21)
    s.box(1180, 110, 330, 110, "Timer starts\nAI speaks the clue\nLCD shows it", AMBER, 22)
    s.diamond(1180, 370, 320, 170, "What does the\nplayer do?", AMBER, 21)
    s.box(1460, 370, 240, 150, "AI GAME MASTER\n±30 s · hint · freeze\nskip · strike · dare", PURPLE, 20)
    s.diamond(1180, 620, 260, 140, "Correct?", AMBER, 22)
    s.diamond(790, 620, 260, 140, "Last stage?", AMBER, 22)
    s.box(1460, 620, 230, 100, "STRIKE +1\nbuzzer · red LED\nAI taunts", RED, 21)
    s.box(790, 820, 260, 100, "DEFUSED\nlid opens", GREEN, 24)
    s.box(1460, 820, 230, 100, "BOOM\n3 strikes or 0:00", RED, 24)
    s.box(150, 820, 230, 100, "Play again?", BLUE, 22, rx=50)
    s.arrow([(265, 110), (333, 110)], BLUE)
    s.arrow([(566, 110), (638, 110)], GREEN); s.label(600, 96, "yes", GREEN, 15)
    s.arrow([(450, 186), (450, 258)], RED); s.label(465, 226, "no", RED, 15, "start")
    s.arrow([(330, 300), (200, 300), (200, 162)], MUTED)
    s.arrow([(941, 110), (1013, 110)], PURPLE)
    s.arrow([(1180, 166), (1180, 283)], AMBER)
    s.add(f'<path d="M1340,370 L1340,370" />')
    s.label(1340, 300, "talks", PURPLE, 15)
    s.arrow([(1460, 294), (1460, 110), (1347, 110)], PURPLE)
    s.label(1472, 210, "speaks reply,\nchanges the bomb", PURPLE, 14, "start")
    s.arrow([(1180, 456), (1180, 548)], AMBER)
    s.label(1195, 510, "pulls wire / types code / scans card", AMBER, 15, "start")
    s.arrow([(1050, 620), (922, 620)], GREEN); s.label(985, 606, "yes", GREEN, 15)
    s.arrow([(1310, 620), (1343, 620)], RED); s.label(1326, 606, "no", RED, 15)
    s.arrow([(790, 550), (790, 370), (1018, 370)], AMBER)
    s.label(805, 460, "no: next stage,\nAI reads new clue", AMBER, 15, "start")
    s.arrow([(790, 690), (790, 768)], GREEN); s.label(805, 735, "yes", GREEN, 15, "start")
    s.arrow([(1460, 670), (1460, 768)], RED); s.label(1475, 725, "3rd strike", RED, 15, "start")
    s.arrow([(1575, 600), (1590, 600), (1590, 470), (1560, 450)], RED, dashed=True)
    s.label(1588, 540, "< 3", RED, 14, "end")
    s.label(1120, 920, "timer reaches 0:00 at any time  →  BOOM", RED, 16)
    s.arrow([(658, 820), (267, 820)], GREEN)
    s.arrow([(1345, 820), (1300, 880), (300, 880), (240, 860)], RED, dashed=True)
    s.arrow([(100, 768), (100, 162)], BLUE)
    s.label(88, 470, "yes", BLUE, 15, "end")
    return s.save("flowchart.svg")


# ---------------------------------------------------------------- architecture
def architecture():
    s = Svg(1600, 760)
    s.box(130, 380, 200, 150, "PLAYER\ntalks, pulls wires,\ntypes the code", BLUE, 24)
    s.add(f'<rect x="290" y="70" width="820" height="620" rx="24" fill="#12161D" stroke="{PURPLE}" stroke-width="3"/>')
    s.label(705, 112, "LAPTOP  ·  Python host  ·  runs 100% offline", PURPLE, 22)
    s.box(460, 240, 250, 120, "EARS\nfaster-whisper\nspeech → text", BLUE, 23)
    s.box(460, 540, 250, 120, "VOICE\nPiper neural TTS\ntext → speech", GREEN, 23)
    s.box(755, 390, 230, 160, "BRAIN\nLlama 3.2 3B\n(Ollama, local)\nwrites riddles\ndecides actions", PURPLE, 23)
    s.box(980, 390, 190, 200, "GAME\nMASTER\npicks answers\nclamps AI output\nruns the dares", AMBER, 22)
    s.box(1265, 390, 210, 190, "ELEGOO\nMEGA 2560\nC++ firmware\ntimer +\nstate machine", RED, 23)
    parts = ["LCD 1602", "4x4 keypad", "4 bomb wires", "active buzzer", "3 strike LEDs"]
    for i, p in enumerate(parts):
        y = 190 + i * 100
        s.box(1495, y, 170, 70, p, MUTED, 20, rx=12)
        s.add(f'<path d="M1370,390 L1392,390 L1392,{y} L1410,{y}" stroke="{MUTED}" stroke-width="2" fill="none"/>')
    s.arrow([(230, 340), (333, 270)], BLUE); s.label(262, 285, "speaks", BLUE, 16)
    s.arrow([(333, 520), (230, 430)], GREEN); s.label(262, 508, "hears", GREEN, 16)
    s.arrow([(586, 270), (638, 340)], BLUE); s.label(632, 285, "text", BLUE, 15)
    s.arrow([(638, 440), (586, 510)], GREEN); s.label(632, 505, "reply", GREEN, 15)
    s.arrow([(871, 365), (884, 365)], AMBER)
    s.arrow([(884, 415), (871, 415)], PURPLE)
    s.arrow([(1076, 360), (1158, 360)], AMBER)
    s.arrow([(1158, 420), (1076, 420)], RED)
    s.label(1265, 230, "USB serial · 115200 baud", MUTED, 15)
    s.label(1265, 258, "commands: TIME · FREEZE · SKIP", AMBER, 14)
    s.label(1265, 535, "events: WIRE · CODE · BOOM", RED, 14)
    return s.save("architecture.svg")


if __name__ == "__main__":
    for f in (state_machine, flowchart, architecture):
        print(f())
