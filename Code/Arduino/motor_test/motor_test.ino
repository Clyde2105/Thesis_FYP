#include <Servo.h>

// --- PIN DEFINITIONS ---
#define STBY 3
#define RIGHT_SPEED 5
#define LEFT_SPEED 6
#define RIGHT_DIR 7
#define LEFT_DIR 8
#define SERVO_PIN 10

// --- SETTINGS ---
#define PEN_UP_ANGLE 125
#define PEN_DOWN_ANGLE 95
#define MOTOR_SPEED 50  

Servo penServo;

void setup() {
  Serial.begin(9600);
  
  // Setup Motor Pins
  pinMode(STBY, OUTPUT);
  pinMode(RIGHT_SPEED, OUTPUT);
  pinMode(LEFT_SPEED, OUTPUT);
  pinMode(RIGHT_DIR, OUTPUT);
  pinMode(LEFT_DIR, OUTPUT);

  // Setup Servo
  penServo.attach(SERVO_PIN);
  penServo.write(PEN_UP_ANGLE); // Start with pen UP

  // Wake up the Motor Driver!
  digitalWrite(STBY, HIGH); 
  stopMotors();
  
  Serial.println("Arduino Ready (Pins Corrected)");
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read(); // Read the command

    // --- MOVEMENT COMMANDS ---
    if (cmd == 'F') {      // Forward
      drive(HIGH, HIGH, MOTOR_SPEED);
    }
    else if (cmd == 'B') { // Backward
      drive(LOW, LOW, MOTOR_SPEED);
    }
    else if (cmd == 'L') { // Spin Left
      drive(LOW, HIGH, MOTOR_SPEED); // Left Back, Right Fwd
    }
    else if (cmd == 'R') { // Spin Right
      drive(HIGH, LOW, MOTOR_SPEED); // Left Fwd, Right Back
    }
    else if (cmd == 'S') { // Stop
      stopMotors();
    }
    
    // --- PEN COMMANDS ---
    else if (cmd == 'U') { // Pen Up
      penServo.write(PEN_UP_ANGLE);
    }
    else if (cmd == 'D') { // Pen Down
      penServo.write(PEN_DOWN_ANGLE);
    }
  }
}

// --- HELPER FUNCTIONS ---
void drive(int leftDir, int rightDir, int speed) {
  digitalWrite(STBY, HIGH); // Ensure driver is awake
  
  digitalWrite(LEFT_DIR, leftDir);
  digitalWrite(RIGHT_DIR, rightDir);
  
  analogWrite(LEFT_SPEED, speed);
  analogWrite(RIGHT_SPEED, speed); 
}

void stopMotors() {
  analogWrite(LEFT_SPEED, 0);
  analogWrite(RIGHT_SPEED, 0);
  // We keep STBY HIGH so the brakes engage (stopping instantly)
  // instead of coasting.
}