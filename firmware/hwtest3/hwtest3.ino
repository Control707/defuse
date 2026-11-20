// DEFUSE keypad pin finder: scans Mega pins 22..53 and reports which two pins touch when a key is pressed.
// Press keys ONE AT A TIME in this order, releasing each: 1 2 3 A 4 5 6 B 7 8 9 C * 0 # D
const uint8_t FIRST = 22, LAST = 53;
int curA = -1, curB = -1, stable = 0, count = 0;
void setup() {
  Serial.begin(115200);
  pinMode(8, OUTPUT);
  Serial.println("=== KEYPAD PIN FINDER ===");
  Serial.println("Press keys one at a time, release each: 1 2 3 A 4 5 6 B 7 8 9 C * 0 # D");
}
void loop() {
  int a = -1, b = -1;
  for (int i = FIRST; i <= LAST && a < 0; i++) {
    for (int k = FIRST; k <= LAST; k++) pinMode(k, INPUT_PULLUP);
    pinMode(i, OUTPUT); digitalWrite(i, LOW);
    delayMicroseconds(30);
    for (int j = i + 1; j <= LAST; j++) if (digitalRead(j) == LOW) { a = i; b = j; break; }
  }
  if (a == curA && b == curB) { if (stable < 5) stable++; } else { curA = a; curB = b; stable = 0; }
  if (stable == 3) {
    if (a >= 0) {
      count++;
      Serial.print("PRESS #"); Serial.print(count); Serial.print(": Mega pins "); Serial.print(a); Serial.print(" + "); Serial.println(b);
      digitalWrite(8, HIGH); delay(60); digitalWrite(8, LOW);
    } else Serial.println("  (released)");
    stable = 4;
  }
}
