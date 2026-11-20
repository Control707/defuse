# DEFUSE wiring guide (ELEGOO Mega 2560 kit)

Wire it in this order and test after each step. The bomb plays without the parts you haven't connected yet.

## 0. Power rails (do this first)
- Plug the **power supply module** into the end of the 830-point breadboard and run it from the **9V1A adapter**. Set both jumpers to **5V**.
- Connect a **Mega GND to the breadboard GND rail**. This is required: every part must share ground.
- The **servo** and **LED matrix** use the breadboard 5V rail. Everything else can use the Mega's 5V pin.

## 1. Countdown display: 4-digit 7-segment (5461AS, common cathode)
Display pin numbers: hold it with the decimal points at the bottom. Bottom row, left to right, is 1–6. Top row, right to left, is 7–12.

| Segment | Display pin | Mega pin (through a **220Ω** resistor) |
|---|---|---|
| a | 11 | 23 |
| b | 7 | 25 |
| c | 4 | 27 |
| d | 2 | 29 |
| e | 1 | 31 |
| f | 10 | 33 |
| g | 5 | 35 |
| dp ("colon") | 3 | 37 |

Use the four **PN2222** transistors to switch the digits. The flat side faces you; the legs are E-B-C.

| Digit | Display pin | Transistor wiring |
|---|---|---|
| D1 | 12 | C → pin 12, B → **1kΩ** → Mega **39**, E → GND |
| D2 | 9 | C → pin 9, B → 1kΩ → Mega **41**, E → GND |
| D3 | 8 | C → pin 8, B → 1kΩ → Mega **43**, E → GND |
| D4 | 6 | C → pin 6, B → 1kΩ → Mega **45**, E → GND |

> Shortcut without transistors: wire the digit pins straight to 39/41/43/45 and use **1kΩ** resistors on the segments instead of 220Ω. In `defuse.ino`, set `#define DIGIT_ON LOW`. The display will be dimmer.

## 2. Keypad (membrane 4×4)
The ribbon has 8 pins. With the keypad face up, from left to right: **22, 24, 26, 28, 30, 32, 34, 36**.
(The first 4 are rows and the last 4 are columns. If the keys come out swapped, flip the ribbon around.)

## 3. Buzzer and strike LEDs
- **Active buzzer** (the one with the sticker): + to **8**, − to GND.
- 3 **red LEDs** (strike lights): long leg → 220Ω → **A8, A9, A10**. Short leg to GND.

## 4. The wires to pull (the "bomb wires")
Use 4 **male-to-male jumper wires**, ideally red, yellow, green and blue. Otherwise label them with tape.

| Wire | One end | Other end |
|---|---|---|
| RED | Mega **A0** | GND rail |
| YELLOW | Mega **A1** | GND rail |
| GREEN | Mega **A2** | GND rail |
| BLUE | Mega **A3** | GND rail |

To cut a wire, pull its GND-rail end out. The bomb detects the pull. **All 4 must be plugged in before you can arm.**

## 5. LCD1602
| LCD pin | Connect to |
|---|---|
| VSS | GND |
| VDD | 5V |
| V0 | middle leg of the **10K potentiometer**. The outer legs go to 5V and GND. Turn it until the text appears. |
| RS | **38** |
| RW | GND |
| E | **40** |
| D4, D5, D6, D7 | **42, 44, 46, 48** |
| A (backlight +) | 220Ω → 5V |
| K (backlight −) | GND |

## 6. MAX7219 8×8 matrix (the villain's face)
VCC → breadboard 5V, GND → GND, **DIN → 7**, **CS → 5**, **CLK → 6**.
If the face is upside down, set `#define MATRIX_FLIP 1`.

## 7. RC522 RFID reader. ⚠️ Power it from 3.3V, not 5V.
| RC522 | Mega |
|---|---|
| SDA | **53** |
| SCK | **52** |
| MOSI | **51** |
| MISO | **50** |
| IRQ | (unused) |
| GND | GND |
| RST | **49** |
| 3.3V | **3.3V** |

**Register your tags once:** press **B** on the keypad, then scan the **white card**, then the **blue fob**. They are saved permanently in the board's memory (EEPROM).

## 8. GY-521 (shake detector)
VCC → 5V, GND → GND, **SDA → 20**, **SCL → 21**.

## 9. HC-SR04 ultrasonic (the bomb "sees" people)
VCC → 5V, GND → GND, **Trig → A4**, **Echo → A5**.

## 10. RGB LED (status light: green, then yellow, then flashing red)
The longest leg goes to GND (common cathode). The other legs go through 220Ω: **R → 9, G → 10, B → 11**.

## 11. Servo SG90 (the lid that pops open when you win)
Brown → GND, red → **breadboard 5V** (not the Mega), orange (signal) → **3**.
Tape a cardboard flap to the servo horn so it covers a "prize" or a "DEFUSED" sign.

---

### Pin summary
```
22-36 even : keypad          23-37 odd : 7-seg segments   39,41,43,45 : 7-seg digits
38-48 even : LCD             49-53     : RFID (SPI)       20/21       : GY-521 (I2C)
3 servo | 5,6,7 matrix | 8 buzzer | 9,10,11 RGB | A0-A3 bomb wires | A4/A5 sonar | A8-A10 strike LEDs
```

### Build a case (biggest wow per minute)
Use a shoebox or the kit's own box. Cut windows for the timer, the LCD and the matrix face. Bring the 4 wires out the front, put the keypad on top, and hide the RFID reader under a "SCAN KEYCARD" label. Tape the GY-521 to the inside wall so shaking the box triggers it.
