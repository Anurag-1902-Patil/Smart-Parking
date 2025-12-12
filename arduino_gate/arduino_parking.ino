/*
 * Smart Parking Gate Controller - Bidirectional State Machine
 * 
 * Hardware Wiring:
 * - IR Entry Sensor: Pin 2 (Input Pullup, Active LOW)
 * - IR Exit Sensor:  Pin 3 (Input Pullup, Active LOW)
 * - Servo Motor:     Pin 4
 */

#include <Servo.h>

// --- CONFIGURATION ---
const uint8_t PIN_IR_ENTRY = 2;
const uint8_t PIN_IR_EXIT  = 3;
const uint8_t PIN_SERVO    = 4;

const int ANGLE_OPEN   = 10;
const int ANGLE_CLOSED = 100;

const unsigned long DEBOUNCE_MS = 50;
const unsigned long FAILSAFE_TIMEOUT_MS = 30000; // 30s timeout if car doesn't pass

// --- STATES ---
enum State {
  IDLE,
  GATE_OPEN_ENTRY,      // Gate Open, waiting for car to reach Exit Sensor
  GATE_PASSING_ENTRY,   // Gate Open, car is blocking Exit Sensor
  GATE_OPEN_EXIT,       // Gate Open, waiting for car to reach Entry Sensor
  GATE_PASSING_EXIT     // Gate Open, car is blocking Entry Sensor
};

State currentState = IDLE;

// --- GLOBALS ---
Servo gateServo;
bool isGateOpen = false;
unsigned long stateStartTime = 0;

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
    // Slow open (Soft Start)
    for (int pos = ANGLE_CLOSED; pos >= ANGLE_OPEN; pos--) {
      gateServo.write(pos);
      delay(15);
    }
    isGateOpen = true;
    Serial.println("EVENT:GATE_OPENED");
  }
}

void closeGate() {
  if (isGateOpen) {
    // Slow close
    for (int pos = ANGLE_OPEN; pos <= ANGLE_CLOSED; pos++) {
      gateServo.write(pos);
      delay(15);
    }
    isGateOpen = false;
    Serial.println("EVENT:GATE_CLOSED");
  } else {
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

  // 1. Read Sensors
  checkSensor(PIN_IR_ENTRY, lastEntryState, lastEntryDebounce, stableEntryState, "ENTRY");
  checkSensor(PIN_IR_EXIT, lastExitState, lastExitDebounce, stableExitState, "EXIT");

  // 2. Handle Serial Commands (Only in IDLE or to force reset)
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd == "CMD:OPEN") {
      // Decide direction based on which sensor is blocked
      if (stableEntryState == LOW) {
        currentState = GATE_OPEN_ENTRY;
        stateStartTime = now;
        openGate();
      } else if (stableExitState == LOW) {
        currentState = GATE_OPEN_EXIT;
        stateStartTime = now;
        openGate();
      } else {
        // Fallback: If neither blocked, maybe default to Entry or just Open
        // For safety, let's default to Entry flow as it's most common
        currentState = GATE_OPEN_ENTRY;
        stateStartTime = now;
        openGate();
      }
    } else if (cmd == "CMD:CLOSE") {
      currentState = IDLE;
      closeGate();
    } else if (cmd == "CMD:STATUS") {
      Serial.print("INFO:GATE:");
      Serial.println(isGateOpen ? "OPEN" : "CLOSED");
    } else if (cmd == "CMD:SENSORS") {
      Serial.print("INFO:SENSORS:ENTRY:");
      Serial.print(stableEntryState == LOW ? "LOW" : "HIGH");
      Serial.print(":EXIT:");
      Serial.println(stableExitState == LOW ? "LOW" : "HIGH");
    }
  }

  // 3. State Machine Logic
  switch (currentState) {
    case IDLE:
      // Do nothing, wait for CMD:OPEN
      break;

    // --- ENTRY FLOW ---
    case GATE_OPEN_ENTRY:
      // Waiting for car to reach Exit Sensor
      if (stableExitState == LOW) {
        currentState = GATE_PASSING_ENTRY;
        stateStartTime = now; // Reset timeout
      }
      // Failsafe Timeout
      if (now - stateStartTime > FAILSAFE_TIMEOUT_MS) {
        currentState = IDLE;
        closeGate();
      }
      break;

    case GATE_PASSING_ENTRY:
      // Car is blocking Exit Sensor. Wait for it to clear.
      if (stableExitState == HIGH) {
        // Car has cleared!
        delay(500); // Small buffer
        currentState = IDLE;
        closeGate();
      }
      // Note: No timeout here. If car is stuck on sensor, gate stays open.
      break;

    // --- EXIT FLOW ---
    case GATE_OPEN_EXIT:
      // Waiting for car to reach Entry Sensor
      if (stableEntryState == LOW) {
        currentState = GATE_PASSING_EXIT;
        stateStartTime = now; // Reset timeout
      }
      // Failsafe Timeout
      if (now - stateStartTime > FAILSAFE_TIMEOUT_MS) {
        currentState = IDLE;
        closeGate();
      }
      break;

    case GATE_PASSING_EXIT:
      // Car is blocking Entry Sensor. Wait for it to clear.
      if (stableEntryState == HIGH) {
        // Car has cleared!
        delay(500); // Small buffer
        currentState = IDLE;
        closeGate();
      }
      break;
  }
}
