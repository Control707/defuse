// DEFUSE hardware test v2 - prints results over USB so they can be saved to a file.
// Tests: keypad (pin by pin), bomb wires, buzzer, strike LEDs, LCD.
#include <LiquidCrystal.h>
LiquidCrystal lcd(38, 40, 42, 44, 46, 48);
const uint8_t KP[8] = {22, 24, 26, 28, 30, 32, 34, 36};   // ribbon wire 1..8 -> these Mega pins
const char KEYS[4][4] = {{'1','2','3','A'},{'4','5','6','B'},{'7','8','9','C'},{'*','0','#','D'}};
const uint8_t W[4] = {A0, A1, A2, A3};
const uint8_t L[3] = {A8, A9, A10};
bool seen[4][4];
bool lastW[4] = {true, true, true, true};
int lastA = -1, lastB = -1;
unsigned long lastSummary = 0;

void summary() {
  Serial.print("SEEN: ");
  for (int r = 0; r < 4; r++) for (int c = 0; c < 4; c++) if (seen[r][c]) { Serial.print(KEYS[r][c]); Serial.print(' '); }
  Serial.print("| MISSING: ");
  int n = 0;
  for (int r = 0; r < 4; r++) for (int c = 0; c < 4; c++) if (!seen[r][c]) { Serial.print(KEYS[r][c]); Serial.print(' '); n++; }
  Serial.println(n == 0 ? "none - KEYPAD OK" : "");
}

void setup() {
  Serial.begin(115200);
  lcd.begin(16, 2);
  lcd.print("TEST v2 running");
  pinMode(8, OUTPUT);
  for (int i = 0; i < 4; i++) pinMode(W[i], INPUT_PULLUP);
  for (int i = 0; i < 3; i++) pinMode(L[i], OUTPUT);
  Serial.println("=== DEFUSE HARDWARE TEST v2 ===");
  Serial.println("Press every keypad key once. Pull each bomb wire out and plug it back.");
  for (int i = 0; i < 3; i++) { digitalWrite(L[i], HIGH); digitalWrite(8, HIGH); delay(120); digitalWrite(8, LOW); delay(200); }
  for (int i = 0; i < 3; i++) digitalWrite(L[i], LOW);
  Serial.println("STARTUP: buzzer beeped x3 and LEDs lit (if you heard/saw them, those work)");
}

void loop() {
  // --- keypad scan: drive each pin low, see which other pin follows ---
  int a = -1, b = -1;
  for (int i = 0; i < 8; i++) {
    for (int k = 0; k < 8; k++) pinMode(KP[k], INPUT_PULLUP);
    pinMode(KP[i], OUTPUT); digitalWrite(KP[i], LOW);
    delayMicroseconds(50);
    for (int j = 0; j < 8; j++) if (j != i && digitalRead(KP[j]) == LOW && a < 0) { a = i; b = j; }
  }
  if (a != lastA || b != lastB) {
    lastA = a; lastB = b;
    if (a >= 0) {
      int lo = min(a, b), hi = max(a, b);
      Serial.print("KEYPAD contact: ribbon wires "); Serial.print(lo + 1); Serial.print("+"); Serial.print(hi + 1);
      Serial.print(" (Mega pins "); Serial.print(KP[lo]); Serial.print("+"); Serial.print(KP[hi]); Serial.print(")");
      // measured ribbon order: rows = wires 1,2,3,8 ; columns = wires 5,6,7,4
      int row = -1, col = -1;
      for (int q = 0; q < 2; q++) {
        int x = q ? hi : lo, y = q ? lo : hi;   // x = candidate row wire, y = candidate column wire
        int r = (x == 0) ? 0 : (x == 1) ? 1 : (x == 2) ? 2 : (x == 7) ? 3 : -1;
        int c = (y == 4) ? 0 : (y == 5) ? 1 : (y == 6) ? 2 : (y == 3) ? 3 : -1;
        if (r >= 0 && c >= 0) { row = r; col = c; }
      }
      if (row >= 0) {
        char k = KEYS[row][col];
        seen[row][col] = true;
        Serial.print("  -> key "); Serial.println(k);
        lcd.setCursor(0, 0); lcd.print("Key: "); lcd.print(k); lcd.print("            ");
        digitalWrite(8, HIGH); delay(60); digitalWrite(8, LOW);
        summary();
      } else Serial.println("  -> NOT a valid key pair (unexpected pair - tell me)");
    }
  }
  // --- bomb wires ---
  for (int i = 0; i < 4; i++) {
    bool plugged = digitalRead(W[i]) == LOW;
    if (plugged != lastW[i]) {
      lastW[i] = plugged;
      Serial.print("BOMB WIRE "); Serial.print(i + 1); Serial.print(" (A"); Serial.print(i); Serial.print(")  ");
      Serial.println(plugged ? "plugged in" : "PULLED OUT");
    }
  }
  lcd.setCursor(0, 1); lcd.print("W:");
  for (int i = 0; i < 4; i++) lcd.print(lastW[i] ? '1' : '_');
  lcd.print("          ");
  // --- LED check: hold keys 5/6/7? simple: blink all LEDs slowly so you can see each one ---
  unsigned long t = millis() / 700 % 4;
  for (int i = 0; i < 3; i++) digitalWrite(L[i], t == (unsigned)i);
  if (millis() - lastSummary > 15000) { lastSummary = millis(); Serial.print("HEARTBEAT "); summary(); }
}
