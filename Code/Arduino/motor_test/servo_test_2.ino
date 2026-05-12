#include <Servo.h>

// --- Servo Settings ---
const int SERVO_PIN = 10;
Servo penServo;
const int PEN_UP = 50;
const int PEN_DOWN = 80;

// --- MOTOR PINS (ELEGOO V4 / SmartCar Shield V1.1) ---
const int STBY        = 3; // Standby (Must be HIGH to enable motors)
const int RIGHT_SPEED = 5; // ENB
const int LEFT_SPEED  = 6; // ENA
const int RIGHT_DIR   = 7; // IN3/IN4 Logic
const int LEFT_DIR    = 8; // IN1/IN2 Logic

// Set a drawing speed (0-255). Lower is better for drawing accuracy!
const int DRAW_SPEED = 120; 

void setup() {
  Serial.begin(115200);
  
  // 1. Initialize motor pins
  pinMode(STBY, OUTPUT);
  pinMode(RIGHT_SPEED, OUTPUT);
  pinMode(LEFT_SPEED, OUTPUT);
  pinMode(RIGHT_DIR, OUTPUT);
  pinMode(LEFT_DIR, OUTPUT);
  
  // Enable the motor driver shield
  digitalWrite(STBY, HIGH); 
  stopMotors(); 

  // 2. Initialize Servo and immediately set to PEN UP (50 deg)
  penServo.attach(SERVO_PIN);
  penServo.write(PEN_UP); 
  Serial.println("Robot Powered On. Pen is UP.");
  
  // 3. Wait 3 seconds
  Serial.println("Waiting 3 seconds...");
  delay(3000);
  
  // 4. Lower pen gently to 80 degrees (PEN DOWN)
  Serial.println("Lowering pen gently...");
  movePenGently(PEN_UP, PEN_DOWN, 15); // 15ms delay per degree for smooth motion
  
  // 5. Move forward for 5 seconds
  Serial.println("Drawing forward for 5 seconds...");
  moveForward();
  delay(5000);
  
  // Stop briefly so the pen doesn't jerk during the direction change
  stopMotors();
  delay(500); 
  
  // 6. Reverse back for 5 seconds
  Serial.println("Reversing for 5 seconds...");
  moveBackward();
  delay(5000);
  stopMotors();
  
  // 7. Raise pen gently back to 50 degrees (PEN UP)
  Serial.println("Raising pen gently...");
  movePenGently(PEN_DOWN, PEN_UP, 15);
  
  Serial.println("Sequence Complete!");
}

void loop() {
  // Empty loop so the drawing sequence only runs once 
  // when you turn it on or press the reset button.
}


// ==========================================
// Custom Helper Functions
// ==========================================

// Gradually moves the servo to prevent jerky motions and buzzing
void movePenGently(int startAngle, int endAngle, int speedDelay) {
  if (startAngle < endAngle) {
    for (int angle = startAngle; angle <= endAngle; angle++) {
      penServo.write(angle);
      delay(speedDelay);
    }
  } else {
    for (int angle = startAngle; angle >= endAngle; angle--) {
      penServo.write(angle);
      delay(speedDelay);
    }
  }
}

// Elegoo V4 Motor Control Logic
void moveForward() {
  digitalWrite(RIGHT_DIR, HIGH);
  digitalWrite(LEFT_DIR, HIGH);
  analogWrite(RIGHT_SPEED, DRAW_SPEED);
  analogWrite(LEFT_SPEED, DRAW_SPEED);
}

void moveBackward() {
  digitalWrite(RIGHT_DIR, LOW);
  digitalWrite(LEFT_DIR, LOW);
  analogWrite(RIGHT_SPEED, DRAW_SPEED);
  analogWrite(LEFT_SPEED, DRAW_SPEED);
}

void stopMotors() {
  analogWrite(RIGHT_SPEED, 0);
  analogWrite(LEFT_SPEED, 0);
}