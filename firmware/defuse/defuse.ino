/*
  DEFUSE  -  an AI-hosted bomb defusal game for the ELEGOO Mega 2560 kit
  ---------------------------------------------------------------------
  The Mega runs the physical bomb: countdown, wires, keypad, RFID keycards,
  shake sensor, proximity sensor, LED-matrix face, buzzer, lid servo.
  A laptop (host/defuse_host.py) plays the AI villain "NINE-VOLT" over USB serial:
  it invents the puzzles, talks, taunts, gives hints and haggles over time.
  With no laptop attached the bomb still plays a standalone game.

  Stages:  1) WIRES  - pull the correct jumper wire
           2) CODE   - type the 4-digit code on the keypad, '#' to submit
           3) CARDS  - scan the RFID tags in the right order
  3 strikes or time-out = BOOM.  Shake the bomb = -10 s.  Keypad 'D' = beg for a hint (-15 s).

  Libraries (Library Manager): LiquidCrystal, Keypad (Mark Stanley), MFRC522 (GithubCommunity),
                                LedControl (Eberhard Fahle), Servo.
  See WIRING.md for every connection.
*/
#include <Wire.h>
#include <SPI.h>
#include <LiquidCrystal.h>
#include <Keypad.h>
#include <MFRC522.h>
#include <LedControl.h>
#include <Servo.h>
#include <EEPROM.h>

// ------------------------------------------------------------------ config
#define GAME_SECONDS_DEFAULT 300      // standalone game length
#define SEG_ON      HIGH              // 5461AS is common-cathode: segment HIGH = lit
#define DIGIT_ON    LOW               // digit pins wired straight to the display (1k resistors on segments).
                                      // If you add PN2222 transistors on the digits, set HIGH.
#define MATRIX_FLIP 0                 // set 1 if the face is upside down
#define SHAKE_G     0.65              // |accel - 1g| above this counts as a shake
#define NEAR_CM     45                // proximity "someone is here" distance
#define SERVO_CLOSED 10
#define SERVO_OPEN   100

// ------------------------------------------------------------------ pins
const uint8_t SEG_PINS[8]   = {23, 25, 27, 29, 31, 33, 35, 37}; // a b c d e f g dp
const uint8_t DIGIT_PINS[4] = {39, 41, 43, 45};                  // D1..D4 (via transistors)
const uint8_t WIRE_PINS[4]  = {A0, A1, A2, A3};                  // bomb wires -> GND
const uint8_t STRIKE_LEDS[3] = {A8, A9, A10};
const uint8_t PIN_BUZZER = 8;
const uint8_t PIN_SERVO  = 3;
const uint8_t PIN_R = 9, PIN_G = 10, PIN_B = 11;                 // RGB LED (common cathode)
const uint8_t PIN_TRIG = A4, PIN_ECHO = A5;                      // HC-SR04
const uint8_t RFID_SS = 53, RFID_RST = 49;                       // + SPI 50..52
// LCD: RS, E, D4, D5, D6, D7
LiquidCrystal lcd(38, 40, 42, 44, 46, 48);
// MAX7219: DIN, CLK, CS
LedControl matrix(7, 6, 5, 1);

const byte ROWS = 4, COLS = 4;
char KEYS[ROWS][COLS] = {
  {'1', '2', '3', 'A'},
  {'4', '5', '6', 'B'},
  {'7', '8', '9', 'C'},
  {'*', '0', '#', 'D'}
};
// Measured on this keypad: top row (1 2 3 A) = pin 36, then 22, 24, 26 ; columns = 28, 30, 32, 34
byte rowPins[ROWS] = {36, 22, 24, 26};
byte colPins[COLS] = {28, 30, 32, 34};
Keypad keypad = Keypad(makeKeymap(KEYS), rowPins, colPins, ROWS, COLS);

MFRC522 rfid(RFID_SS, RFID_RST);
Servo lid;

// ------------------------------------------------------------------ faces (8x8, MSB = left)
const byte F_EVIL[8]   = {0x81, 0x42, 0x00, 0x66, 0x66, 0x00, 0x81, 0x7E};
const byte F_BLINK[8]  = {0x81, 0x42, 0x00, 0x00, 0x66, 0x00, 0x81, 0x7E};
const byte F_LOOKL[8]  = {0x81, 0x42, 0x00, 0xCC, 0xCC, 0x00, 0x81, 0x7E};
const byte F_LOOKR[8]  = {0x81, 0x42, 0x00, 0x33, 0x33, 0x00, 0x81, 0x7E};
const byte F_TALK1[8]  = {0x81, 0x42, 0x00, 0x66, 0x66, 0x00, 0x00, 0x7E};
const byte F_TALK2[8]  = {0x81, 0x42, 0x00, 0x66, 0x66, 0x3C, 0x42, 0x3C};
const byte F_ANGRY[8]  = {0xC3, 0x66, 0x00, 0x66, 0x66, 0x00, 0x3C, 0x42};
const byte F_LAUGH1[8] = {0x00, 0x00, 0x42, 0xA5, 0x00, 0x7E, 0x42, 0x3C};
const byte F_LAUGH2[8] = {0x00, 0x00, 0x42, 0xA5, 0x00, 0x7E, 0x7E, 0x3C};
const byte F_SHOCK[8]  = {0x00, 0x66, 0x66, 0x66, 0x00, 0x18, 0x24, 0x18};
const byte F_DEAD[8]   = {0x00, 0xA5, 0x42, 0xA5, 0x00, 0x00, 0x3C, 0x42};
const byte F_SKULL[8]  = {0x3C, 0x7E, 0xDB, 0xFF, 0xE7, 0x7E, 0x5A, 0x3C};
const byte BOOM_F[4][8] = {
  {0, 0, 0, 0x18, 0x18, 0, 0, 0},
  {0, 0, 0x3C, 0x24, 0x24, 0x3C, 0, 0},
  {0, 0x7E, 0x42, 0x42, 0x42, 0x42, 0x7E, 0},
  {0xFF, 0x81, 0x81, 0x81, 0x81, 0x81, 0x81, 0xFF}
};

// ------------------------------------------------------------------ 7-segment (Timer0 COMPB ISR)
const uint8_t SEG_DIGITS[10] = {0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F};
const uint8_t SEG_DASH = 0x40;
volatile uint8_t segBuf[4] = {SEG_DASH, SEG_DASH, SEG_DASH, SEG_DASH};
volatile uint8_t segIdx = 0;

ISR(TIMER0_COMPB_vect) {
  digitalWrite(DIGIT_PINS[segIdx], !DIGIT_ON);
  segIdx = (segIdx + 1) & 3;
  uint8_t s = segBuf[segIdx];
  for (uint8_t i = 0; i < 8; i++) digitalWrite(SEG_PINS[i], (s >> i) & 1 ? SEG_ON : !SEG_ON);
  digitalWrite(DIGIT_PINS[segIdx], DIGIT_ON);
}

void startDisplayTimer() {
  // Timer0 already runs millis(); its compare-B interrupt fires ~976 Hz -> ~244 Hz per digit.
  // (All 16-bit timers are claimed by the Servo library on the Mega.)  Pin 4 PWM is unused.
  OCR0B = 128;
  TIMSK0 |= (1 << OCIE0B);
}

void showTime(long secs, bool colon) {
  if (secs < 0) secs = 0;
  int m = secs / 60, s = secs % 60;
  if (m > 99) m = 99;
  uint8_t b[4] = {SEG_DIGITS[m / 10], SEG_DIGITS[m % 10], SEG_DIGITS[s / 10], SEG_DIGITS[s % 10]};
  if (colon) b[1] |= 0x80;               // decimal point after minutes acts as the colon
  noInterrupts(); for (int i = 0; i < 4; i++) segBuf[i] = b[i]; interrupts();
}
void showDashes() { noInterrupts(); for (int i = 0; i < 4; i++) segBuf[i] = SEG_DASH; interrupts(); }
void showBlank()  { noInterrupts(); for (int i = 0; i < 4; i++) segBuf[i] = 0; interrupts(); }

// ------------------------------------------------------------------ game state
enum State { G_IDLE, G_WAIT_HOST, G_PLAYING, G_WON, G_BOOMED, G_REGISTER };
enum Stage { S_WIRES = 0, S_CODE = 1, S_CARDS = 2 };
State state = G_IDLE;
Stage stage = S_WIRES;
bool hostConnected = false;
bool hostPuzzle = false;               // true when the puzzle came from the AI host

long gameSeconds = GAME_SECONDS_DEFAULT;
unsigned long deadline = 0;            // millis() at which the bomb goes off
long frozenSecs = 0;
uint8_t solWire = 0;
char solCode[5] = "0000";
uint8_t seq[6]; uint8_t seqLen = 3; uint8_t seqPos = 0;
uint8_t strikes = 0;
char entry[5] = ""; uint8_t entryLen = 0;

bool wireCut[4];
uint8_t wireStable[4];                 // debounce counters

String tagUid[2]; uint8_t tagCount = 0;   // tag 0 = "CARD", tag 1 = "FOB" (saved in EEPROM, press B to register)
uint8_t regStep = 0;
String lastUid = ""; unsigned long lastUidAt = 0;

bool rfidOk = false, mpuOk = false;
unsigned long lastShake = 0, lastMpu = 0, lastSonar = 0, lastNearEvt = 0;
bool someoneNear = false;
unsigned long waitHostSince = 0;
long lastTickSent = -1, lastBeepSec = -1;
unsigned long buzzOffAt = 0;
unsigned long freezeUntil = 0, lastFreezeTick = 0;   // FREEZE: timer stops while the player does a dare

// LCD message (line 2) with scrolling
char msg[97] = "";
uint8_t msgScroll = 0; unsigned long lastScroll = 0;
bool lcdDirty = true;
unsigned long entryShowUntil = 0;

// Face animation
const byte* faceOverride = NULL; unsigned long faceUntil = 0;
unsigned long talkUntil = 0;
unsigned long lastFaceFrame = 0; uint8_t faceFrame = 0;
const byte* lastDrawn = NULL;

// Serial input
char inBuf[128]; uint8_t inLen = 0;

// ------------------------------------------------------------------ helpers
void drawFace(const byte* f) {
  if (f == lastDrawn) return;
  lastDrawn = f;
  for (int r = 0; r < 8; r++) {
    byte row = f[MATRIX_FLIP ? 7 - r : r];
    if (MATRIX_FLIP) { byte rev = 0; for (int i = 0; i < 8; i++) if (row & (1 << i)) rev |= 0x80 >> i; row = rev; }
    matrix.setRow(0, r, row);
  }
}
void setFace(const byte* f, unsigned long ms) { faceOverride = f; faceUntil = millis() + ms; }
const byte* faceByName(const char* n) {
  if (!strcmp(n, "ANGRY")) return F_ANGRY;
  if (!strcmp(n, "LAUGH")) return F_LAUGH1;
  if (!strcmp(n, "SHOCK")) return F_SHOCK;
  if (!strcmp(n, "DEAD"))  return F_DEAD;
  if (!strcmp(n, "SKULL")) return F_SKULL;
  return F_EVIL;
}

void rgb(uint8_t r, uint8_t g, uint8_t b) { analogWrite(PIN_R, r); analogWrite(PIN_G, g); analogWrite(PIN_B, b); }
void beep(unsigned int ms) { digitalWrite(PIN_BUZZER, HIGH); buzzOffAt = millis() + ms; }

void setMsg(const char* m) {
  strncpy(msg, m, sizeof(msg) - 1); msg[sizeof(msg) - 1] = 0;
  msgScroll = 0; lastScroll = millis(); lcdDirty = true;
}

long secsLeft() {
  if (state != G_PLAYING) return frozenSecs;
  long ms = (long)(deadline - millis());
  if (ms <= 0) return 0;
  return (ms + 999) / 1000;
}

void updateStrikeLeds() { for (int i = 0; i < 3; i++) digitalWrite(STRIKE_LEDS[i], i < strikes ? HIGH : LOW); }

void evt(const String& s) { Serial.println(s); }

// ------------------------------------------------------------------ RFID tag storage (EEPROM)
// layout: [0]=0xD5 magic, then 2 x 16 bytes of zero-terminated UID hex strings
void saveTags() {
  EEPROM.update(0, 0xD5);
  for (int t = 0; t < 2; t++)
    for (int i = 0; i < 16; i++) EEPROM.update(1 + t * 16 + i, i < (int)tagUid[t].length() ? tagUid[t][i] : 0);
}
void loadTags() {
  tagCount = 0;
  if (EEPROM.read(0) != 0xD5) return;
  for (int t = 0; t < 2; t++) {
    String u = "";
    for (int i = 0; i < 16; i++) { char c = EEPROM.read(1 + t * 16 + i); if (!c) break; u += c; }
    tagUid[t] = u;
  }
  if (tagUid[0].length() && tagUid[1].length()) tagCount = 2;
}

// ------------------------------------------------------------------ LCD
void drawLcd() {
  char l1[17];
  if (state == G_IDLE)          snprintf(l1, 17, "%-16s", "  D E F U S E");
  else if (state == G_WAIT_HOST)snprintf(l1, 17, "%-16s", "WAKING UP...");
  else if (state == G_WON)      snprintf(l1, 17, "%-16s", "*** DEFUSED ***");
  else if (state == G_BOOMED)   snprintf(l1, 17, "%-16s", "### BOOM ###");
  else if (state == G_REGISTER) snprintf(l1, 17, "%-16s", "REGISTER TAGS");
  else {
    char x[4] = "   ";
    for (int i = 0; i < 3; i++) x[i] = i < strikes ? 'X' : ' ';
    long sl = secsLeft();
    char t[6]; snprintf(t, 6, "%02d:%02d", (int)(sl / 60), (int)(sl % 60));
    if (stage == S_WIRES)      snprintf(l1, 17, "WIRES %s  %s", t, x);
    else if (stage == S_CODE) {
      char e[5]; for (int i = 0; i < 4; i++) e[i] = i < entryLen ? entry[i] : '_'; e[4] = 0;
      snprintf(l1, 17, "%s %s %s", e, t, x);
    } else {
      snprintf(l1, 17, "CARD%d/%d %s %s", seqPos, seqLen, t, x);
    }
  }
  lcd.setCursor(0, 0); lcd.print(l1);

  char l2[17];
  int len = strlen(msg);
  if (len <= 16) snprintf(l2, 17, "%-16s", msg);
  else {
    int total = len + 4;                 // 4 spaces gap before wrap
    for (int i = 0; i < 16; i++) {
      int p = (msgScroll + i) % total;
      l2[i] = p < len ? msg[p] : ' ';
    }
    l2[16] = 0;
  }
  lcd.setCursor(0, 1); lcd.print(l2);
  lcdDirty = false;
}

// ------------------------------------------------------------------ standalone puzzle text
const char* COLOR_NAMES[4] = {"RED", "YELLOW", "GREEN", "BLUE"};
const char* COLOR_RIDDLES[4] = {"the color of blood", "the color of a coward", "the color of envy", "the color of a sad song"};

void standaloneClue() {
  char b[97];
  if (stage == S_WIRES) {
    snprintf(b, sizeof(b), "Cut the wire that is %s", COLOR_RIDDLES[solWire]);
  } else if (stage == S_CODE) {
    String s = "CODE: ";
    for (int i = 0; i < 4; i++) {
      int d = solCode[i] - '0';
      int a = random(0, d + 1);
      if (random(2) || d == 9) { s += String(a) + "+" + String(d - a); }
      else { int k = random(1, 10 - d); s += String(d + k) + "-" + String(k); }
      if (i < 3) s += " ";
    }
    s.toCharArray(b, sizeof(b));
  } else {
    String s = "SCAN:";
    for (int i = 0; i < seqLen; i++) s += seq[i] ? " FOB" : " CARD";
    s.toCharArray(b, sizeof(b));
  }
  setMsg(b);
}

// ------------------------------------------------------------------ game flow
void resetRound() {
  strikes = 0; entryLen = 0; entry[0] = 0; seqPos = 0; stage = S_WIRES;
  updateStrikeLeds();
  lid.write(SERVO_CLOSED);
}

void randomPuzzle() {
  gameSeconds = GAME_SECONDS_DEFAULT;
  solWire = random(4);
  for (int i = 0; i < 4; i++) solCode[i] = '0' + random(10);
  solCode[4] = 0;
  seqLen = 3;
  do { for (int i = 0; i < seqLen; i++) seq[i] = random(2); } while (seq[0] == seq[1] && seq[1] == seq[2]);
  if (tagCount < 2) seq[0] = 0;          // unregistered tags: the first tag scanned becomes CARD
  hostPuzzle = false;
}

void enterStage(int s) {
  stage = (Stage)s;
  entryLen = 0; entry[0] = 0; seqPos = 0;
  evt(String("STAGE ") + (int)s);
  if (hostPuzzle) setMsg("Listen to me...");
  else standaloneClue();
  lcdDirty = true;
}

void startGame() {
  resetRound();
  state = G_PLAYING;
  deadline = millis() + (unsigned long)gameSeconds * 1000UL;
  lastTickSent = -1; lastBeepSec = -1;
  evt(String("START ") + gameSeconds);
  enterStage(S_WIRES);
}

void strike(const char* why) {
  strikes++;
  updateStrikeLeds();
  setFace(F_ANGRY, 2000);
  beep(400);
  evt(String("STRIKE ") + strikes + " " + why);
  lcdDirty = true;
  if (strikes >= 3) boom("strikes");
}

void win() {
  frozenSecs = secsLeft();
  state = G_WON;
  showTime(frozenSecs, true);
  evt(String("WIN ") + frozenSecs);
  setMsg("You got lucky. Press A to play again");
  lid.write(SERVO_OPEN);
  rgb(0, 255, 0);
  faceOverride = NULL;
  drawFace(F_DEAD);
  for (int i = 0; i < 3; i++) { digitalWrite(PIN_BUZZER, HIGH); delay(80); digitalWrite(PIN_BUZZER, LOW); delay(80); }
  digitalWrite(PIN_BUZZER, HIGH); delay(400); digitalWrite(PIN_BUZZER, LOW);
  lcdDirty = true;
}

void boom(const char* why) {
  frozenSecs = 0;
  state = G_BOOMED;
  evt(String("BOOM ") + why);
  setMsg("KA-BOOM! Press A to try again");
  drawLcd();
  digitalWrite(PIN_BUZZER, HIGH);
  for (int rep = 0; rep < 3; rep++) {
    for (int f = 0; f < 4; f++) {
      lastDrawn = NULL; drawFace(BOOM_F[f]);
      rgb(255, f * 40, 0);
      if (f % 2) showDashes(); else showBlank();
      delay(90);
    }
  }
  digitalWrite(PIN_BUZZER, LOW);
  for (int i = 0; i < 6; i++) { rgb(i % 2 ? 255 : 0, 0, 0); delay(120); }
  rgb(255, 0, 0);
  showDashes();
  lastDrawn = NULL; drawFace(F_SKULL);
  faceOverride = NULL;
  lcdDirty = true;
}

void tryArm() {
  for (int i = 0; i < 4; i++) {
    if (digitalRead(WIRE_PINS[i]) == HIGH) {
      char b[40]; snprintf(b, sizeof(b), "Plug in wire %d (%s) first!", i + 1, COLOR_NAMES[i]);
      setMsg(b); beep(150);
      evt(String("NEED_WIRE ") + i);
      return;
    }
  }
  for (int i = 0; i < 4; i++) { wireCut[i] = false; wireStable[i] = 0; }
  resetRound();
  rgb(0, 0, 0);
  if (hostConnected) {
    state = G_WAIT_HOST; waitHostSince = millis();
    hostPuzzle = false;
    evt("ARM");
    setMsg("The bomb is thinking...");
    showDashes();
  } else {
    randomPuzzle();
    startGame();
  }
}

// ------------------------------------------------------------------ inputs
void pollWires() {
  for (int i = 0; i < 4; i++) {
    if (wireCut[i]) continue;
    if (digitalRead(WIRE_PINS[i]) == HIGH) { if (wireStable[i] < 255) wireStable[i]++; }
    else wireStable[i] = 0;
    if (wireStable[i] >= 20) {           // ~20 loop passes of HIGH = really pulled
      wireCut[i] = true;
      if (state != G_PLAYING) continue;
      if (stage == S_WIRES && i == solWire) {
        evt(String("WIRE ") + i + " OK");
        beep(60);
        enterStage(S_CODE);
      } else {
        evt(String("WIRE ") + i + " BAD");
        strike("wire");
      }
    }
  }
}

void requestHint() {
  if (state != G_PLAYING) return;
  deadline -= 15000UL;
  evt(String("HINT ") + (int)stage);
  setFace(F_LAUGH1, 2000);
  if (!hostPuzzle) {
    char b[97];
    if (stage == S_WIRES) snprintf(b, sizeof(b), "Fine. Pull the %s wire. (-15s)", COLOR_NAMES[solWire]);
    else if (stage == S_CODE) snprintf(b, sizeof(b), "Ugh. The code is %s (-15s)", solCode);
    else { standaloneClue(); return; }
    setMsg(b);
  }
}

void pollKeypad() {
  char k = keypad.getKey();
  if (!k) return;
  beep(25);
  evt(String("KEY ") + k);
  if (state == G_IDLE || state == G_WON || state == G_BOOMED || state == G_REGISTER) {
    if (k == 'A' && state != G_REGISTER) tryArm();
    else if (k == 'B') { state = G_REGISTER; regStep = 0; setMsg("Scan the CARD"); }
    return;
  }
  if (state == G_REGISTER) {
    if (k == '*') { state = G_IDLE; loadTags(); setMsg("Press A to arm the bomb"); }
    return;
  }
  if (state != G_PLAYING) return;
  if (k == 'D') { requestHint(); return; }
  if (stage != S_CODE) {
    if (k >= '0' && k <= '9') { setFace(F_LAUGH1, 1200); }
    return;
  }
  if (k >= '0' && k <= '9' && entryLen < 4) { entry[entryLen++] = k; entry[entryLen] = 0; lcdDirty = true; }
  else if (k == '*') { entryLen = 0; entry[0] = 0; lcdDirty = true; }
  else if (k == '#' && entryLen == 4) {
    if (!strcmp(entry, solCode)) {
      evt(String("CODE ") + entry + " OK");
      beep(60);
      if (rfidOk) enterStage(S_CARDS); else win();   // no RFID reader wired yet: code stage is the last one
    } else {
      evt(String("CODE ") + entry + " BAD");
      entryLen = 0; entry[0] = 0;
      strike("code");
    }
  }
}

String readUid() {
  String s = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) s += "0";
    s += String(rfid.uid.uidByte[i], HEX);
  }
  s.toUpperCase();
  return s;
}

void pollRfid() {
  if (!rfidOk) return;
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;
  String uid = readUid();
  rfid.PICC_HaltA(); rfid.PCD_StopCrypto1();
  if (uid == lastUid && millis() - lastUidAt < 1500) { lastUidAt = millis(); return; }
  lastUid = uid; lastUidAt = millis();

  if (state == G_REGISTER) {
    if (regStep == 1 && uid == tagUid[0]) { setMsg("That's the CARD. Scan the FOB"); return; }
    tagUid[regStep] = uid; beep(60);
    evt(String("REG ") + regStep + " " + uid);
    if (++regStep == 1) setMsg("Now scan the FOB");
    else { tagCount = 2; saveTags(); state = G_IDLE; setMsg("Tags saved! Press A to arm"); }
    lcdDirty = true;
    return;
  }
  if (state != G_PLAYING || stage != S_CARDS) { evt("UID " + uid); return; }

  int idx = -1;
  for (int i = 0; i < tagCount; i++) if (tagUid[i] == uid) idx = i;
  if (idx < 0 && tagCount < 2) { tagUid[tagCount] = uid; idx = tagCount++; }   // learn unregistered tags
  if (idx < 0) { evt("UID " + uid); setMsg("Unknown card. Nice try."); return; }

  if (idx == seq[seqPos]) {
    seqPos++;
    beep(60);
    evt(String("TAG ") + idx + " OK " + seqPos);
    lcdDirty = true;
    if (seqPos >= seqLen) win();
  } else {
    evt(String("TAG ") + idx + " BAD");
    seqPos = 0;
    strike("card");
  }
}

void mpuInit() {
  Wire.begin();
  Wire.setWireTimeout(3000, true);
  Wire.beginTransmission(0x68); Wire.write(0x6B); Wire.write(0);
  mpuOk = Wire.endTransmission() == 0;
}

void pollMpu() {
  if (!mpuOk || millis() - lastMpu < 20) return;
  lastMpu = millis();
  Wire.beginTransmission(0x68); Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return;
  if (Wire.requestFrom(0x68, 6) != 6) return;
  int16_t ax = (Wire.read() << 8) | Wire.read();
  int16_t ay = (Wire.read() << 8) | Wire.read();
  int16_t az = (Wire.read() << 8) | Wire.read();
  float g = sqrt((float)ax * ax + (float)ay * ay + (float)az * az) / 16384.0;
  if (fabs(g - 1.0) > SHAKE_G && state == G_PLAYING && millis() - lastShake > 2000) {
    lastShake = millis();
    deadline -= 10000UL;
    setFace(F_SHOCK, 1500);
    beep(200);
    evt("SHAKE");
  }
}

void pollSonar() {
  if (millis() - lastSonar < 250) return;
  lastSonar = millis();
  digitalWrite(PIN_TRIG, LOW); delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long us = pulseIn(PIN_ECHO, HIGH, 20000UL);
  if (us == 0) { someoneNear = false; return; }
  int cm = us / 58;
  bool near = cm < NEAR_CM;
  if (near && !someoneNear && millis() - lastNearEvt > 8000) {
    lastNearEvt = millis();
    evt(String("NEAR ") + cm);
    if (state == G_IDLE) { setFace(F_LOOKL, 800); if (!hostConnected) setMsg("Come closer... press A if you dare"); }
  }
  someoneNear = near;
}

// ------------------------------------------------------------------ host commands
void handleCommand(char* line) {
  char* cmd = strtok(line, " ");
  if (!cmd) return;
  char* rest = strtok(NULL, "");
  if (!strcmp(cmd, "HELLO")) {
    hostConnected = true;
    evt(String("READY v=4 rfid=") + (rfidOk ? "ok" : "missing") + " mpu=" + (mpuOk ? "ok" : "missing") + " tags=" + tagCount);
  } else if (!strcmp(cmd, "PING")) {
    evt("PONG");
  } else if (!strcmp(cmd, "TAG") && rest) {           // TAG <index> <UIDHEX>
    int i = atoi(strtok(rest, " ")); char* u = strtok(NULL, " ");
    if (i >= 0 && i < 2 && u) { tagUid[i] = String(u); tagUid[i].toUpperCase(); if (i + 1 > tagCount) tagCount = i + 1; }
  } else if (!strcmp(cmd, "NEW") && rest) {           // NEW <secs> <wire> <code> <seq e.g. 101>
    char* a = strtok(rest, " "); char* b = strtok(NULL, " "); char* c = strtok(NULL, " "); char* d = strtok(NULL, " ");
    if (a && b && c && d && strlen(c) == 4) {
      gameSeconds = atol(a); solWire = atoi(b) & 3;
      strncpy(solCode, c, 4); solCode[4] = 0;
      seqLen = min((int)strlen(d), 6);
      for (int i = 0; i < seqLen; i++) seq[i] = d[i] - '0';
      hostPuzzle = true;
      evt("OK NEW");
    }
  } else if (!strcmp(cmd, "GO")) {                     // start (also restarts after BOOM / WIN)
    if (state != G_PLAYING) {
      for (int i = 0; i < 4; i++) if (digitalRead(WIRE_PINS[i]) == HIGH) {
        char b[40]; snprintf(b, sizeof(b), "Plug in wire %d (%s) first!", i + 1, COLOR_NAMES[i]);
        setMsg(b); evt(String("NEED_WIRE ") + i); return;
      }
      for (int i = 0; i < 4; i++) { wireCut[i] = false; wireStable[i] = 0; }
      rgb(0, 0, 0);
      if (!hostPuzzle) randomPuzzle();
      startGame();
    }
  } else if (!strcmp(cmd, "MSG")) {
    setMsg(rest ? rest : "");
  } else if (!strcmp(cmd, "TIME") && rest) {          // TIME +20 / TIME -15
    long d = atol(rest);
    if (state == G_PLAYING) {
      deadline += d * 1000L;
      if (d < 0) setFace(F_LAUGH1, 1500);
      evt(String("TIME ") + secsLeft());
    }
  } else if (!strcmp(cmd, "FACE") && rest) {          // FACE LAUGH 2000
    char* n = strtok(rest, " "); char* ms = strtok(NULL, " ");
    setFace(faceByName(n), ms ? atol(ms) : 2000);
  } else if (!strcmp(cmd, "TALK") && rest) {          // TALK <ms>  -> mouth animates
    talkUntil = millis() + atol(rest);
  } else if (!strcmp(cmd, "SKIP")) {                   // AI mercy: jump past the current puzzle
    if (state == G_PLAYING) {
      evt("SKIPPED");
      if (stage == S_WIRES) enterStage(S_CODE);
      else if (stage == S_CODE && rfidOk) enterStage(S_CARDS);
      else win();
    }
  } else if (!strcmp(cmd, "STRIKE")) {                 // AI punishment
    if (state == G_PLAYING) strike("ai");
  } else if (!strcmp(cmd, "FREEZE") && rest) {          // FREEZE <secs>
    if (state == G_PLAYING) { freezeUntil = millis() + atol(rest) * 1000UL; lastFreezeTick = millis(); rgb(0, 80, 255); evt("FROZEN"); }
  } else if (!strcmp(cmd, "ABORT")) {
    for (int i = 0; i < 4; i++) { wireCut[i] = false; wireStable[i] = 0; }
    freezeUntil = 0;
    lid.write(SERVO_CLOSED);
    state = G_IDLE; showDashes(); rgb(0, 0, 0); setMsg("Press A to arm"); lcdDirty = true;
  }
}

void pollSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') { inBuf[inLen] = 0; if (inLen) handleCommand(inBuf); inLen = 0; }
    else if (inLen < sizeof(inBuf) - 1) inBuf[inLen++] = c;
  }
}

// ------------------------------------------------------------------ outputs that tick
void updateFace() {
  unsigned long now = millis();
  if (faceOverride && now < faceUntil) {
    if (faceOverride == F_LAUGH1 || faceOverride == F_LAUGH2) {
      if (now - lastFaceFrame > 150) { lastFaceFrame = now; faceFrame ^= 1; }
      drawFace(faceFrame ? F_LAUGH2 : F_LAUGH1);
    } else drawFace(faceOverride);
    return;
  }
  faceOverride = NULL;
  if (state == G_BOOMED) { drawFace(F_SKULL); return; }
  if (state == G_WON) { drawFace(F_DEAD); return; }
  if (now < talkUntil) {
    if (now - lastFaceFrame > 140) { lastFaceFrame = now; faceFrame = random(3) ? !faceFrame : faceFrame; }
    drawFace(faceFrame ? F_TALK2 : F_TALK1);
    return;
  }
  // idle animation: mostly staring, sometimes blink / glance
  unsigned long t = now % 6000;
  if (t < 150) drawFace(F_BLINK);
  else if (t > 3000 && t < 3600) drawFace(F_LOOKL);
  else if (t > 4200 && t < 4800) drawFace(F_LOOKR);
  else drawFace(F_EVIL);
}

void updateTimerAndSound() {
  unsigned long now = millis();
  if (buzzOffAt && now > buzzOffAt) { digitalWrite(PIN_BUZZER, LOW); buzzOffAt = 0; }

  if (state == G_IDLE || state == G_REGISTER) {
    // slow purple breathing
    float p = (sin(now / 700.0) + 1) / 2;
    rgb(80 * p, 0, 120 * p);
    showTime(gameSeconds, (now / 500) % 2);
    return;
  }
  if (state != G_PLAYING) return;

  if (freezeUntil) {                       // time is frozen: push the deadline forward by the time that passed
    if (now < freezeUntil) {
      deadline += now - lastFreezeTick; lastFreezeTick = now;
      showTime(secsLeft(), true);
      return;
    }
    deadline += freezeUntil - lastFreezeTick; freezeUntil = 0; evt("THAWED");
  }
  long ms = (long)(deadline - now);
  if (ms <= 0) { showTime(0, true); boom("time"); return; }
  long s = (ms + 999) / 1000;
  showTime(s, (ms % 1000) > 500);

  // ticking: 1/s, 2/s under 30s, 4/s under 10s
  int perSec = s <= 10 ? 4 : (s <= 30 ? 2 : 1);
  long slot = (ms / (1000 / perSec));
  if (slot != lastBeepSec) { lastBeepSec = slot; if (!buzzOffAt) beep(s <= 10 ? 20 : 30); }

  // status light
  if (s > 60) rgb(0, 120, 0);
  else if (s > 20) rgb(160, 90, 0);
  else rgb(((ms / 125) % 2) ? 255 : 0, 0, 0);

  // tell the host the time every 5 s (and every second near the end)
  if (s != lastTickSent && (s % 5 == 0 || s <= 10)) { lastTickSent = s; evt(String("TICK ") + s); }
}

// ------------------------------------------------------------------ setup / loop
void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 8; i++) pinMode(SEG_PINS[i], OUTPUT);
  for (int i = 0; i < 4; i++) { pinMode(DIGIT_PINS[i], OUTPUT); digitalWrite(DIGIT_PINS[i], !DIGIT_ON); }
  for (int i = 0; i < 4; i++) pinMode(WIRE_PINS[i], INPUT_PULLUP);
  for (int i = 0; i < 3; i++) pinMode(STRIKE_LEDS[i], OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_R, OUTPUT); pinMode(PIN_G, OUTPUT); pinMode(PIN_B, OUTPUT);
  pinMode(PIN_TRIG, OUTPUT); pinMode(PIN_ECHO, INPUT);
  randomSeed(analogRead(A15) ^ micros());

  lcd.begin(16, 2);
  matrix.shutdown(0, false); matrix.setIntensity(0, 6); matrix.clearDisplay(0);
  lid.attach(PIN_SERVO); lid.write(SERVO_CLOSED);

  SPI.begin();
  rfid.PCD_Init();
  byte v = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  rfidOk = !(v == 0x00 || v == 0xFF);
  mpuInit();
  loadTags();

  startDisplayTimer();
  // boot self-test: all LEDs flash
  for (int i = 0; i < 3; i++) digitalWrite(STRIKE_LEDS[i], HIGH);
  rgb(255, 255, 255); beep(80);
  noInterrupts(); for (int i = 0; i < 4; i++) segBuf[i] = 0xFF; interrupts();   // 88:88
  delay(400);
  updateStrikeLeds(); rgb(0, 0, 0);

  setMsg("Press A to arm the bomb");
  evt(String("BOOT tags=") + tagCount + " rfid=" + (rfidOk ? "ok" : "missing") + " mpu=" + (mpuOk ? "ok" : "missing"));
}

void loop() {
  pollSerial();
  pollKeypad();
  pollWires();
  pollRfid();
  pollMpu();
  pollSonar();

  if (state == G_WAIT_HOST && millis() - waitHostSince > 20000) {   // host too slow -> standalone
    evt("HOST_TIMEOUT");
    randomPuzzle(); startGame();
  }

  updateTimerAndSound();
  updateFace();

  unsigned long now = millis();
  if (strlen(msg) > 16 && now - lastScroll > 320) { lastScroll = now; msgScroll++; lcdDirty = true; }
  static long lastLcdSec = -1; long nowSec = secsLeft(); if (nowSec != lastLcdSec) { lastLcdSec = nowSec; lcdDirty = true; }
  if (lcdDirty) drawLcd();
}
