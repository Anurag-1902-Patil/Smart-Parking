/*
 * Smart Parking Gate Controller
 * 
 * Hardware Wiring:
 * - IR Entry Sensor: Pin 2 (Input Pullup)
 * - IR Exit Sensor:  Pin 3 (Input Pullup)
 * - Servo Motor:     Pin 4
 * 
 * Serial Protocol (9600 baud):
 * PC -> Arduino:
 * - CMD:OPEN\n   : Open gate
 * - CMD:CLOSE\n  : Close gate
 * - CMD:STATUS\n : Request status
 * 
 * Arduino -> PC:
 * - SYSTEM:READY\n         : Boot complete
 * - EVENT:GATE_OPENED\n    : Gate finished opening
 * - EVENT:GATE_CLOSED\n    : Gate finished closing
 * - EVENT:BEAM:ENTRY:LOW\n : Entry beam broken (falling edge)
 * - EVENT:BEAM:EXIT:LOW\n  : Exit beam broken (falling edge)
 * - INFO:GATE:OPEN|CLOSED  : Status response
 */

#include <Servo.h>

// --- CONFIGURATION ---
const uint8_t PIN_IR_ENTRY = 2;
const uint8_t PIN_IR_EXIT  = 3;
const uint8_t PIN_SERVO    = 4;

const int ANGLE_OPEN   = 10;
const int ANGLE_CLOSED = 100;

const unsigned long DEBOUNCE_MS = 100;
const unsigned long GATE_AUTO_CLOSE_MS = 5000; // Safety auto-close if backend forgets

// --- GLOBALS ---
Servo gateServo;
bool isGateOpen = false;
unsigned long gateOpenTime = 0;

// Debounce State
int lastEntryState = HIGH;
int lastExitState = HIGH;
unsigned long lastEntryDebounce = 0;
unsigned long lastExitDebounce = 0;
int stableEntryState = HIGH;
int stableExitState = HIGH;

void setup() {
  Serial.begin(9600);
  
  pinMode(PIN_IR_ENTRY, INPUT_PULLUP);
  pinMode(PIN_IR_EXIT, INPUT_PULLUP);
  
  gateServo.attach(PIN_SERVO);
  closeGate(); // Start closed
  
  Serial.println("SYSTEM:READY");
}

void openGate() {
  if (!isGateOpen) {
    // Slow open to prevent brownout (100 -> 10)
    for (int pos = ANGLE_CLOSED; pos >= ANGLE_OPEN; pos--) {
      gateServo.write(pos);
      delay(15); // 15ms per degree = ~1.35s total
    }
    isGateOpen = true;
    gateOpenTime = millis();
    Serial.println("EVENT:GATE_OPENED");
  }
}

void closeGate() {
  if (isGateOpen) {
    // Slow close (10 -> 100)
    for (int pos = ANGLE_OPEN; pos <= ANGLE_CLOSED; pos++) {
      gateServo.write(pos);
      delay(15);
    }
    isGateOpen = false;
    Serial.println("EVENT:GATE_CLOSED");
  } else {
    // Ensure it's physically closed
    gateServo.write(ANGLE_CLOSED);
  }
}

// Helper: Detect change with debounce
void checkSensor(int pin, int &lastState, unsigned long &lastDbTime, int &stableState, const char* name) {
  int reading = digitalRead(pin);

  if (reading != lastState) {
    lastDbTime = millis();
  }

  if ((millis() - lastDbTime) > DEBOUNCE_MS) {
    if (reading != stableState) {
      stableState = reading;
      // State changed
      Serial.print("EVENT:BEAM:");
      Serial.print(name);
      Serial.print(":");
      Serial.println(stableState == LOW ? "LOW" : "HIGH");
    }
  }
  
  lastState = reading;
}

void loop() {
  unsigned long now = millis();

  // 1. Handle Serial Commands
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd == "CMD:OPEN") {
      openGate();
    } else if (cmd == "CMD:CLOSE") {
      closeGate();
    } else if (cmd == "CMD:STATUS") {
      Serial.print("INFO:GATE:");
      Serial.println(isGateOpen ? "OPEN" : "CLOSED");
    } else if (cmd == "CMD:SENSORS") {
      Serial.print("INFO:SENSORS:ENTRY:");
      Serial.print(digitalRead(PIN_IR_ENTRY) == LOW ? "LOW" : "HIGH");
      Serial.print(":EXIT:");
      Serial.println(digitalRead(PIN_IR_EXIT) == LOW ? "LOW" : "HIGH");
    }
  }

  // 2. Read Sensors
  checkSensor(PIN_IR_ENTRY, lastEntryState, lastEntryDebounce, stableEntryState, "ENTRY");
  checkSensor(PIN_IR_EXIT, lastExitState, lastExitDebounce, stableExitState, "EXIT");

  // 3. Safety Auto-Close
  if (isGateOpen && (now - gateOpenTime > GATE_AUTO_CLOSE_MS)) {
    closeGate();
  }
}
