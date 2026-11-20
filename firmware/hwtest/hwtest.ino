// DEFUSE hardware test: upload this first. Tests keypad, LCD, buzzer, strike LEDs, bomb wires.
#include <LiquidCrystal.h>
#include <Keypad.h>
LiquidCrystal lcd(38, 40, 42, 44, 46, 48);
char KEYS[4][4] = {{'1','2','3','A'},{'4','5','6','B'},{'7','8','9','C'},{'*','0','#','D'}};
byte rowPins[4] = {22, 24, 26, 28}, colPins[4] = {30, 32, 34, 36};
Keypad kp = Keypad(makeKeymap(KEYS), rowPins, colPins, 4, 4);
const uint8_t W[4] = {A0, A1, A2, A3};
const uint8_t L[3] = {A8, A9, A10};
void setup() {
  lcd.begin(16, 2);
  lcd.print("LCD OK  turn knob");
  pinMode(8, OUTPUT);
  for (int i = 0; i < 4; i++) pinMode(W[i], INPUT_PULLUP);
  for (int i = 0; i < 3; i++) pinMode(L[i], OUTPUT);
  // LED chase + beep at start
  for (int i = 0; i < 3; i++) { digitalWrite(L[i], HIGH); digitalWrite(8, HIGH); delay(150); digitalWrite(8, LOW); delay(150); }
  for (int i = 0; i < 3; i++) digitalWrite(L[i], LOW);
}
void loop() {
  char k = kp.getKey();
  if (k) { tone(8, 1500, 60); lcd.setCursor(0, 0); lcd.print("Key: "); lcd.print(k); lcd.print("          ");
    int n = (k >= '1' && k <= '3') ? k - '1' : -1; if (n >= 0) { digitalWrite(L[n], !digitalRead(L[n])); } }
  // line 2 shows the 4 bomb wires: 1 = plugged in (grounded), _ = pulled out
  lcd.setCursor(0, 1); lcd.print("W:");
  for (int i = 0; i < 4; i++) lcd.print(digitalRead(W[i]) == LOW ? '1' : '_');
  lcd.print(" press 1 2 3");
}
