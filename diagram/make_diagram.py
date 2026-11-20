#!/usr/bin/env python3
"""Generates WIRING_DIAGRAM.html (+ one SVG per step). Each part is drawn with its pins in
physical order; every pin has a colored tag saying exactly where it goes on the Mega."""
import html, os

OUT = os.path.dirname(os.path.abspath(__file__))

# tag kinds -> colors
C = {
    "5V": ("#e53935", "white"), "GND": ("#212121", "white"), "3.3V": ("#fb8c00", "white"),
    "pin": ("#1e88e5", "white"), "none": ("#e0e0e0", "#777"), "other": ("#8e24aa", "white"),
}
R220 = ["#c62828", "#c62828", "#111", "#111", "#8d6e63"]      # red red black black brown
R1K = ["#8d6e63", "#111", "#111", "#8d6e63", "#8d6e63"]       # brown black black brown brown


def kind(t):
    if t in ("5V", "GND", "3.3V"):
        return t
    if t == "-":
        return "none"
    if t.startswith("pot") or t.startswith("GND rail"):
        return "other"
    return "pin"


def resistor(x, y, bands, label):
    s = f'<rect x="{x-22}" y="{y-8}" width="44" height="16" rx="7" fill="#e8d5a8" stroke="#a1887f"/>'
    for i, b in enumerate(bands):
        s += f'<rect x="{x-15+i*7}" y="{y-8}" width="4" height="16" fill="{b}"/>'
    s += f'<text x="{x+28}" y="{y+5}" font-size="13" fill="#555">{label}</text>'
    return s


def part_card(title, subtitle, pins, body_color="#37474f", note=None, pin_w=74):
    """pins: list of (pin_label, destination, resistor) where resistor in (None,'220','1k')."""
    n = len(pins)
    w = max(560, n * pin_w + 60)
    x0 = (w - n * pin_w) / 2 + pin_w / 2
    body_h = 70
    h = 330 if any(p[2] for p in pins) else 280
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" font-family="Helvetica,Arial,sans-serif">',
         f'<rect x="20" y="20" width="{w-40}" height="{body_h}" rx="10" fill="{body_color}"/>',
         f'<text x="{w/2}" y="52" font-size="24" font-weight="bold" fill="white" text-anchor="middle">{html.escape(title)}</text>',
         f'<text x="{w/2}" y="76" font-size="14" fill="#cfd8dc" text-anchor="middle">{html.escape(subtitle)}</text>']
    for i, (lab, dest, res) in enumerate(pins):
        x = x0 + i * pin_w
        k = kind(dest)
        bg, fg = C[k]
        # pin leg
        s.append(f'<rect x="{x-4}" y="{20+body_h}" width="8" height="26" fill="#b0bec5"/>')
        s.append(f'<text x="{x}" y="{20+body_h+46}" font-size="14" font-weight="bold" fill="#263238" text-anchor="middle">{html.escape(lab)}</text>')
        top = 20 + body_h + 56
        if k == "none":
            s.append(f'<text x="{x}" y="{top+40}" font-size="13" fill="#999" text-anchor="middle">empty</text>')
            continue
        y_tag = top + (70 if res else 26)
        s.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{y_tag}" stroke="{bg}" stroke-width="4"/>')
        if res:
            s.append(resistor(x, top + 30, R220 if res == "220" else R1K, ""))
            s.append(f'<text x="{x}" y="{top+56}" font-size="12" fill="#6d4c41" text-anchor="middle">{res}Ω</text>')
        big = len(dest) <= 4
        tw = max(58, len(dest) * (13 if big else 8) + 16)
        s.append(f'<rect x="{x-tw/2}" y="{y_tag}" width="{tw}" height="40" rx="8" fill="{bg}"/>')
        s.append(f'<text x="{x}" y="{y_tag+27}" font-size="{22 if big else 13}" font-weight="bold" fill="{fg}" text-anchor="middle">{html.escape(dest)}</text>')
    if note:
        s.append(f'<text x="{w/2}" y="{h-12}" font-size="15" fill="#c62828" text-anchor="middle" font-weight="bold">{html.escape(note)}</text>')
    s.append("</svg>")
    return "\n".join(s)


def seven_seg():
    """The display drawn from the front with its 12 pins in their real positions."""
    top = [(12, "39", None), (11, "23", "1k"), (10, "33", "1k"), (9, "41", None), (8, "43", None), (7, "25", "1k")]
    bot = [(1, "31", "1k"), (2, "29", "1k"), (3, "37", "1k"), (4, "27", "1k"), (5, "35", "1k"), (6, "45", None)]
    w, h = 760, 590
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" font-family="Helvetica,Arial,sans-serif">']
    bx, by, bw, bh = 170, 190, 420, 180
    s.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="8" fill="#263238"/>')
    s.append(f'<text x="{bx+bw/2}" y="{by+100}" font-size="80" fill="#ef5350" text-anchor="middle" font-family="monospace" font-weight="bold">8.8.8.8.</text>')
    s.append(f'<text x="{bx+bw/2}" y="{by+150}" font-size="14" fill="#90a4ae" text-anchor="middle">FRONT VIEW - decimal dots at the BOTTOM</text>')
    step = bw / 6
    for row, pins in (("top", top), ("bot", bot)):
        for i, (num, dest, res) in enumerate(pins):
            x = bx + step / 2 + i * step
            if row == "top":
                s.append(f'<rect x="{x-4}" y="{by-22}" width="8" height="22" fill="#b0bec5"/>')
                s.append(f'<text x="{x}" y="{by-28}" font-size="12" fill="#546e7a" text-anchor="middle">pin {num}</text>')
                y1, y2 = by - 40, 20
            else:
                s.append(f'<rect x="{x-4}" y="{by+bh}" width="8" height="22" fill="#b0bec5"/>')
                s.append(f'<text x="{x}" y="{by+bh+38}" font-size="12" fill="#546e7a" text-anchor="middle">pin {num}</text>')
                y1, y2 = by + bh + 44, h - 90
            col = "#1e88e5" if not res else "#43a047"
            s.append(f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 + (40 if row=="top" else 0)}" stroke="{col}" stroke-width="4"/>')
            if res:
                ry = (y1 + y2 + 40) / 2 if row == "top" else (y1 + y2) / 2
                s.append(resistor(x, ry, R1K, ""))
            ty = y2 if row == "top" else y2
            s.append(f'<rect x="{x-29}" y="{ty}" width="58" height="40" rx="8" fill="{col}"/>')
            s.append(f'<text x="{x}" y="{ty+28}" font-size="22" font-weight="bold" fill="white" text-anchor="middle">{dest}</text>')
    s.append(f'<text x="{w/2}" y="{h-12}" font-size="15" fill="#2e7d32" text-anchor="middle" font-weight="bold">GREEN line = goes through a 1kΩ resistor (8 of them).  BLUE line = plain jumper wire.</text>')
    s.append("</svg>")
    return "\n".join(s)


def keypad():
    pins = [(str(i + 1), str(22 + 2 * i), None) for i in range(8)]
    return part_card("4x4 KEYPAD", "ribbon cable, keys facing you, pin 1 = leftmost", pins, "#1565c0",
                     note="If keys come out wrong, flip the ribbon around.")


def bomb_wires():
    w, h = 640, 300
    cols = [("RED", "#e53935", "A0"), ("YELLOW", "#fdd835", "A1"), ("GREEN", "#43a047", "A2"), ("BLUE", "#1e88e5", "A3")]
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" font-family="Helvetica,Arial,sans-serif">']
    s.append(f'<rect x="40" y="220" width="{w-80}" height="30" rx="6" fill="#212121"/>')
    s.append(f'<text x="{w/2}" y="241" font-size="16" fill="white" text-anchor="middle" font-weight="bold">BREADBOARD BLUE (−) RAIL = GND</text>')
    for i, (name, col, pin) in enumerate(cols):
        x = 110 + i * 140
        s.append(f'<rect x="{x-32}" y="20" width="64" height="44" rx="8" fill="#1e88e5"/>')
        s.append(f'<text x="{x}" y="50" font-size="22" font-weight="bold" fill="white" text-anchor="middle">{pin}</text>')
        s.append(f'<path d="M{x} 64 C {x+50} 120, {x-50} 160, {x} 220" stroke="{col}" stroke-width="8" fill="none"/>')
        s.append(f'<text x="{x+38}" y="140" font-size="14" font-weight="bold" fill="#333">{name}</text>')
    s.append(f'<text x="{w/2}" y="285" font-size="15" fill="#c62828" text-anchor="middle" font-weight="bold">4 jumper wires. Pulling one out of the rail = "cutting" it. All 4 plugged in to start.</text>')
    s.append("</svg>")
    return "\n".join(s)


def leds():
    pins = [("LED1 long", "A8", "220"), ("LED2 long", "A9", "220"), ("LED3 long", "A10", "220"),
            ("all short", "GND", None)]
    return part_card("3 RED LEDs (strikes)", "long leg = +   short leg = −", pins, "#c62828", pin_w=110)


def mega_map():
    """Top-down Mega 2560 with every used pin highlighted by color group."""
    groups = {
        "keypad": ("#1565c0", [str(p) for p in range(22, 37, 2)]),
        "7seg": ("#2e7d32", [str(p) for p in range(23, 38, 2)] + ["39", "41", "43", "45"]),
        "lcd": ("#00897b", ["38", "40", "42", "44", "46", "48"]),
        "rfid": ("#6a1b9a", ["49", "50", "51", "52", "53"]),
        "i2c": ("#5d4037", ["20", "21"]),
        "misc": ("#ef6c00", ["3", "5", "6", "7", "8", "9", "10", "11"]),
        "analog": ("#c62828", ["A0", "A1", "A2", "A3", "A4", "A5", "A8", "A9", "A10"]),
    }
    pin_color = {}
    for col, plist in groups.values():
        for p in plist:
            pin_color[p] = col
    W, H = 1180, 560
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" font-family="Helvetica,Arial,sans-serif">']
    s.append('<rect x="20" y="70" width="1140" height="400" rx="18" fill="#0d47a1"/>')
    s.append('<rect x="0" y="120" width="70" height="80" rx="4" fill="#bdbdbd"/><text x="35" y="166" font-size="13" text-anchor="middle">USB</text>')
    s.append('<rect x="0" y="330" width="60" height="70" rx="4" fill="#424242"/><text x="30" y="370" font-size="11" fill="white" text-anchor="middle">DC jack</text>')
    s.append('<text x="460" y="280" font-size="36" fill="#90caf9" font-weight="bold" text-anchor="middle">MEGA 2560</text>')
    s.append('<text x="460" y="312" font-size="15" fill="#bbdefb" text-anchor="middle">USB on the LEFT. Colored = a wire goes here.</text>')

    def pin(x, y, label, lab_above):
        col = pin_color.get(label)
        fill = col or "#1a237e"
        s.append(f'<rect x="{x-11}" y="{y-11}" width="22" height="22" rx="3" fill="{fill}" stroke="{"white" if col else "#3949ab"}" stroke-width="{2 if col else 1}"/>')
        ty = y - 18 if lab_above else y + 28
        s.append(f'<text x="{x}" y="{ty}" font-size="{13 if col else 10}" font-weight="{"bold" if col else "normal"}" fill="{col or "#9fa8da"}" text-anchor="middle">{label}</text>')

    # top digital header: (right to left on real board 0..13) -> draw 13..0 then 14..21
    top = ["AREF", "GND", "13", "12", "11", "10", "9", "8", None, "7", "6", "5", "4", "3", "2", "1", "0", None,
           "14", "15", "16", "17", "18", "19", "20", "21"]
    x = 260
    for p in top:
        if p is None:
            x += 14
            continue
        pin(x, 82, p, True)
        x += 28
    # bottom header: power + analog
    bot = ["IOREF", "RST", "3.3V", "5V", "GND", "GND", "Vin", None] + [f"A{i}" for i in range(8)] + [None] + [f"A{i}" for i in range(8, 16)]
    x = 290
    for p in bot:
        if p is None:
            x += 14
            continue
        if p in ("3.3V", "5V", "GND"):
            col = {"3.3V": "#fb8c00", "5V": "#e53935", "GND": "#212121"}[p]
            s.append(f'<rect x="{x-11}" y="447" width="22" height="22" rx="3" fill="{col}" stroke="white" stroke-width="2"/>')
            s.append(f'<text x="{x}" y="490" font-size="12" font-weight="bold" fill="{col}" text-anchor="middle">{p}</text>')
        else:
            pin(x, 458, p, False)
        x += 28
    # right double header 22..53 drawn as two columns
    s.append('<text x="1050" y="105" font-size="11" fill="#e53935" text-anchor="middle" font-weight="bold">5V 5V</text>')
    for i in range(16):
        y = 128 + i * 20.5
        for j, xx in enumerate((1035, 1075)):
            p = str(22 + 2 * i + j)
            col = pin_color.get(p)
            s.append(f'<rect x="{xx-9}" y="{y-9}" width="18" height="18" rx="3" fill="{col or "#1a237e"}" stroke="{"white" if col else "#3949ab"}"/>')
            tx = xx - 18 if j == 0 else xx + 18
            s.append(f'<text x="{tx}" y="{y+5}" font-size="13" font-weight="bold" fill="{"white" if col else "#7986cb"}" text-anchor="{"end" if j == 0 else "start"}">{p}</text>')
    s.append('<text x="1055" y="462" font-size="11" fill="white" text-anchor="middle" font-weight="bold">GND GND</text>')
    # legend
    leg = [("Keypad", "#1565c0"), ("Timer display", "#2e7d32"), ("LCD", "#00897b"), ("RFID", "#6a1b9a"),
           ("Shake sensor", "#5d4037"), ("Servo/face/buzzer/RGB", "#ef6c00"), ("Wires/sonar/LEDs", "#c62828")]
    x = 30
    for name, col in leg:
        s.append(f'<rect x="{x}" y="520" width="18" height="18" rx="3" fill="{col}"/><text x="{x+24}" y="534" font-size="14" fill="#333">{name}</text>')
        x += 24 + len(name) * 8 + 22
    s.append('<text x="1050" y="40" font-size="13" fill="#555" text-anchor="middle">big double header</text>')
    s.append("</svg>")
    return "\n".join(s)


def power():
    w, h = 760, 300
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" font-family="Helvetica,Arial,sans-serif">']
    s.append('<rect x="30" y="40" width="200" height="200" rx="14" fill="#0d47a1"/><text x="130" y="130" font-size="24" fill="white" text-anchor="middle" font-weight="bold">MEGA</text>')
    s.append('<rect x="190" y="160" width="40" height="22" fill="#e53935"/><text x="210" y="176" font-size="13" fill="white" text-anchor="middle">5V</text>')
    s.append('<rect x="190" y="195" width="40" height="22" fill="#212121"/><text x="210" y="211" font-size="12" fill="white" text-anchor="middle">GND</text>')
    s.append('<rect x="330" y="60" width="400" height="180" rx="8" fill="#f5f5f5" stroke="#bbb"/>')
    s.append('<text x="530" y="150" font-size="18" fill="#999" text-anchor="middle">BREADBOARD</text>')
    s.append('<rect x="340" y="190" width="380" height="12" fill="#e53935"/><text x="530" y="186" font-size="13" fill="#e53935" text-anchor="middle" font-weight="bold">+ (red line) rail = 5V</text>')
    s.append('<rect x="340" y="214" width="380" height="12" fill="#212121"/><text x="530" y="250" font-size="13" fill="#212121" text-anchor="middle" font-weight="bold">− (blue line) rail = GND</text>')
    s.append('<path d="M230 171 H 300 V 196 H 340" stroke="#e53935" stroke-width="6" fill="none"/>')
    s.append('<path d="M230 206 H 290 V 220 H 340" stroke="#212121" stroke-width="6" fill="none"/>')
    s.append(f'<text x="{w/2}" y="25" font-size="17" text-anchor="middle" font-weight="bold" fill="#333">Every "5V" tag = plug into the red rail.  Every "GND" tag = plug into the blue rail.</text>')
    s.append('<text x="380" y="285" font-size="14" text-anchor="middle" fill="#c62828" font-weight="bold">Only exception: RFID "3.3V" goes straight to the Mega 3.3V pin.</text>')
    s.append("</svg>")
    return "\n".join(s)


STEPS = [
    ("Power rails", "2 wires", power(), True),
    ("Timer display (4-digit)", "12 wires + 8 resistors", seven_seg(), True),
    ("Keypad", "8 wires", keypad(), True),
    ("Buzzer", "2 wires", part_card("ACTIVE BUZZER", "the one with a sticker on top", [("+ (long)", "8", None), ("−", "GND", None)], "#424242"), True),
    ("The 4 bomb wires", "4 wires", bomb_wires(), True),
    ("Strike LEDs", "3 LEDs + 3 resistors", leds(), False),
    ("LCD screen", "12 wires + knob", part_card("LCD1602", "16 pins, left to right, screen facing you",
        [("VSS", "GND", None), ("VDD", "5V", None), ("V0", "pot mid", None), ("RS", "38", None), ("RW", "GND", None),
         ("E", "40", None), ("D0", "-", None), ("D1", "-", None), ("D2", "-", None), ("D3", "-", None),
         ("D4", "42", None), ("D5", "44", None), ("D6", "46", None), ("D7", "48", None), ("A", "5V", "220"), ("K", "GND", None)],
        "#00695c", pin_w=62) + part_card("10K KNOB (potentiometer)", "turn it until text appears on the LCD",
        [("left", "5V", None), ("middle", "pot→V0", None), ("right", "GND", None)], "#455a64", pin_w=120), False),
    ("Evil face (8x8 matrix)", "5 wires", part_card("MAX7219 8x8 MATRIX", "use the 5-pin header on the IN side",
        [("VCC", "5V", None), ("GND", "GND", None), ("DIN", "7", None), ("CS", "5", None), ("CLK", "6", None)], "#b71c1c", pin_w=96), False),
    ("RFID reader", "7 wires", part_card("RC522 RFID", "pins left to right, chip side up",
        [("SDA", "53", None), ("SCK", "52", None), ("MOSI", "51", None), ("MISO", "50", None), ("IRQ", "-", None),
         ("GND", "GND", None), ("RST", "49", None), ("3.3V", "3.3V", None)], "#4a148c",
        note="3.3V ONLY - 5V will kill it. Then press B, scan the white card, then the blue fob."), False),
    ("Shake sensor", "4 wires", part_card("GY-521", "only the first 4 pins",
        [("VCC", "5V", None), ("GND", "GND", None), ("SCL", "21", None), ("SDA", "20", None),
         ("XDA", "-", None), ("XCL", "-", None), ("AD0", "-", None), ("INT", "-", None)], "#4e342e"), False),
    ("Ultrasonic eyes", "4 wires", part_card("HC-SR04 ULTRASONIC", "the two 'eyes' facing you",
        [("VCC", "5V", None), ("Trig", "A4", None), ("Echo", "A5", None), ("GND", "GND", None)], "#0277bd", pin_w=110), False),
    ("RGB status light", "4 legs, 3 resistors", part_card("RGB LED", "longest leg is 2nd from the left",
        [("R", "9", "220"), ("longest", "GND", None), ("G", "10", "220"), ("B", "11", "220")], "#6d4c41", pin_w=110), False),
    ("Lid servo", "3 wires", part_card("SG90 SERVO", "its own 3-wire plug",
        [("brown", "GND", None), ("red", "5V", None), ("orange", "3", None)], "#e65100", pin_w=120), False),
]

css = """
body{font-family:Helvetica,Arial,sans-serif;background:#eceff1;margin:0;padding:20px;color:#263238}
h1{margin:0 0 4px;font-size:34px} .sub{color:#555;margin-bottom:18px;font-size:17px}
.card{background:white;border-radius:14px;padding:16px 20px;margin:0 auto 22px;max-width:1220px;box-shadow:0 2px 8px #0002}
.card h2{margin:0 0 10px;font-size:24px} .n{display:inline-block;background:#263238;color:white;border-radius:50%;width:36px;height:36px;
text-align:center;line-height:36px;margin-right:10px} .tag{font-size:14px;color:#777;font-weight:normal;margin-left:8px}
.must{background:#c62828;color:white;font-size:13px;padding:3px 9px;border-radius:12px;margin-left:8px;vertical-align:middle}
.nice{background:#90a4ae;color:white;font-size:13px;padding:3px 9px;border-radius:12px;margin-left:8px;vertical-align:middle}
svg{max-width:100%;height:auto;display:block;margin:6px auto}
.key{display:flex;gap:18px;flex-wrap:wrap;font-size:16px;align-items:center}
.chip{padding:5px 12px;border-radius:8px;color:white;font-weight:bold}
label{cursor:pointer;user-select:none} input[type=checkbox]{transform:scale(1.6);margin-right:10px}
@media print{.card{break-inside:avoid;box-shadow:none}}
"""

parts = [f"<!doctype html><html><head><meta charset='utf-8'><title>DEFUSE wiring diagram</title><style>{css}</style></head><body>",
         "<div class='card'><h1>💣 DEFUSE: wiring diagram</h1>",
         "<div class='sub'>Each picture shows a part with its pins. <b>Follow the line from each pin to the colored tag</b>, "
         "then plug a jumper wire from that pin into the tag's spot. Do the red <b>MUST</b> steps first, then upload the code. "
         "<b>The game already plays with just those.</b></div>",
         "<div class='key'><span class='chip' style='background:#1e88e5'>23</span> = Mega pin 23 "
         "<span class='chip' style='background:#e53935'>5V</span> = red + rail "
         "<span class='chip' style='background:#212121'>GND</span> = blue − rail "
         "<span class='chip' style='background:#fb8c00'>3.3V</span> = Mega 3.3V pin "
         f"<svg width='70' height='24' viewBox='-35 -12 70 24' style='display:inline;margin:0'>{resistor(0, 0, R220, '')}</svg> 220Ω "
         f"<svg width='70' height='24' viewBox='-35 -12 70 24' style='display:inline;margin:0'>{resistor(0, 0, R1K, '')}</svg> 1kΩ "
         "(check the color stripes; the kit's resistor bags are labeled)</div></div>",
         "<div class='card'><h2>🗺️ Where everything lands on the Mega</h2>" + mega_map() + "</div>"]
for i, (title, count, svg, must) in enumerate(STEPS, 1):
    badge = "<span class='must'>MUST</span>" if must else "<span class='nice'>extra wow</span>"
    parts.append(f"<div class='card'><h2><label><input type='checkbox'><span class='n'>{i}</span>{html.escape(title)}</label>"
                 f"{badge}<span class='tag'>{count}</span></h2>{svg}</div>")
    for k, chunk in enumerate(svg.split("</svg>")[:-1]):
        with open(os.path.join(OUT, f"step{i:02d}{'' if k == 0 else chr(97 + k)}.svg"), "w") as f:
            f.write(chunk.strip() + "</svg>")
parts.append("<div class='card'><h2>✅ Then</h2><div class='sub' style='margin:0'>Upload <b>firmware/defuse/defuse.ino</b> "
             "(Board: Arduino Mega 2560) → close Serial Monitor → <code>python3 host/defuse_host.py</code> → press <b>A</b>.<br>"
             "Timer shows garbage/dark? Swap <code>DIGIT_ON</code> to HIGH in the code. LCD blank? Turn the knob.</div></div>")
parts.append("</body></html>")
with open(os.path.join(OUT, "WIRING_DIAGRAM.html"), "w") as f:
    f.write("\n".join(parts))
with open(os.path.join(OUT, "mega_map.svg"), "w") as f:
    f.write(mega_map())
print("ok")
