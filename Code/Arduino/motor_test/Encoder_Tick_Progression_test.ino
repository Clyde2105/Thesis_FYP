// --- MOTOR PINS (ELEGOO V4 / SmartCar Shield V1.1) ---
const int STBY        = 3; 
const int RIGHT_SPEED = 5; 
const int LEFT_SPEED  = 6; 
const int RIGHT_DIR   = 7; 
const int LEFT_DIR    = 8; 

// --- ENCODER PINS ---
const int LEFT_ENC = 12;
const int RIGHT_ENC = 13;

// --- TICK COUNTERS ---
volatile unsigned long leftTicks = 0;
volatile unsigned long rightTicks = 0;

// --- DEBOUNCE VARIABLES ---
byte lastLeftState = LOW;
byte lastRightState = LOW;
unsigned long lastLeftTime = 0;
unsigned long lastRightTime = 0;

// --- TEST SETTINGS ---
const int TARGET_TICKS = 20; // 1 full rotation
bool leftDone = false;
bool rightDone = false;
unsigned long lastReportTime = 0;
bool finishedPrinted = false;

void setup() {
  Serial.begin(115200);
  Serial.println("Starting Motor Calibration Test...");
  delay(2000); // Give you 2 seconds to open the Serial Monitor

  // Setup Motors
  pinMode(STBY, OUTPUT);
  pinMode(RIGHT_SPEED, OUTPUT);
  pinMode(LEFT_SPEED, OUTPUT);
  pinMode(RIGHT_DIR, OUTPUT);
  pinMode(LEFT_DIR, OUTPUT);
  
  digitalWrite(STBY, HIGH); // Enable the motor driver

  // Setup Encoders
  pinMode(LEFT_ENC, INPUT_PULLUP);
  pinMode(RIGHT_ENC, INPUT_PULLUP);

  // Enable Pin Change Interrupts for D12 and D13
  PCICR |= B00000001; 
  PCMSK0 |= B00110000; 
}

void loop() {
  // If either motor hasn't reached the target, keep checking
  if (!leftDone || !rightDone) {
    
    // --- LEFT MOTOR LOGIC ---
    if (leftTicks < TARGET_TICKS) {
      digitalWrite(LEFT_DIR, HIGH); // Move Forward
      analogWrite(LEFT_SPEED, 80); // Moderate speed
    } else {
      analogWrite(LEFT_SPEED, 0);   // Stop instantly!
      leftDone = true;
    }

    // --- RIGHT MOTOR LOGIC ---
    if (rightTicks < TARGET_TICKS) {
      digitalWrite(RIGHT_DIR, HIGH); // Move Forward
      analogWrite(RIGHT_SPEED, 100); // Moderate speed
    } else {
      analogWrite(RIGHT_SPEED, 0);   // Stop instantly!
      rightDone = true;
    }

    // Print progress to the monitor every 30ms
    if (millis() - lastReportTime > 30) {
      Serial.print("Left Ticks: "); 
      Serial.print(leftTicks);
      Serial.print(" | Right Ticks: "); 
      Serial.println(rightTicks);
      lastReportTime = millis();
    }
    
  } else {
    // Both motors have stopped. Print the final results once.
    if (!finishedPrinted) {
      Serial.println("===========================");
      Serial.println("       TEST COMPLETE       ");
      Serial.println("===========================");
      Serial.print("FINAL LEFT:  "); Serial.println(leftTicks);
      Serial.print("FINAL RIGHT: "); Serial.println(rightTicks);
      finishedPrinted = true;
    }
  }
}

// --- DUAL ENCODER INTERRUPT ROUTINE ---
ISR(PCINT0_vect) {
  byte currentLeft = digitalRead(LEFT_ENC);
  byte currentRight = digitalRead(RIGHT_ENC);
  unsigned long currentTime = millis();

  // Left Wheel Debounce
  if (currentLeft == HIGH && lastLeftState == LOW) {
    if (currentTime - lastLeftTime > 10) { 
      leftTicks++;
      lastLeftTime = currentTime;
    }
  }
  
  // Right Wheel Debounce
  if (currentRight == HIGH && lastRightState == LOW) {
    if (currentTime - lastRightTime > 10) { 
      rightTicks++;
      lastRightTime = currentTime;
    }
  }

  lastLeftState = currentLeft;
  lastRightState = currentRight;
}