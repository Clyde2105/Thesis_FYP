#include <Servo.h>

// --- MOTOR PINS ---
const int STBY        = 3; 
const int RIGHT_SPEED = 5; 
const int LEFT_SPEED  = 6; 
const int RIGHT_DIR   = 7; 
const int LEFT_DIR    = 8; 

// --- ENCODER PINS ---
const int LEFT_ENC = 12;
const int RIGHT_ENC = 13;

volatile unsigned long leftTicks = 0;
volatile unsigned long rightTicks = 0;
byte lastLeftState = LOW;
byte lastRightState = LOW;

// --- SERVO PIN ---
const int SERVO_PIN = 10;
Servo penServo;
// Kept your beautifully dialed-in pen angles!
const int PEN_UP_ANGLE = 40; 
const int PEN_DOWN_ANGLE = 78; 

// --- AUTO-DRIVE STATE VARIABLES ---
bool isDriving = false;
unsigned long targetTicks = 0;

// --- MICRO-TUNED BASE SPEEDS (For Straight Lines) ---
const int LEFT_BASE_SPEED = 80; 
const int RIGHT_BASE_SPEED = 82; 

// Restored to 8 so straight lines lock in quickly
const int kP = 8; 

unsigned long lastReportTime = 0;

void setup() {
  Serial.begin(115200);

  pinMode(STBY, OUTPUT);
  pinMode(RIGHT_SPEED, OUTPUT);
  pinMode(LEFT_SPEED, OUTPUT);
  pinMode(RIGHT_DIR, OUTPUT);
  pinMode(LEFT_DIR, OUTPUT);
  digitalWrite(STBY, HIGH); 

  penServo.attach(SERVO_PIN);
  penServo.write(PEN_UP_ANGLE); 

  pinMode(LEFT_ENC, INPUT_PULLUP);
  pinMode(RIGHT_ENC, INPUT_PULLUP);

  PCICR |= B00000001; 
  PCMSK0 |= B00110000; 
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    executeCommand(command);
  }

  // Auto-Stop & P-Control State Machine (Only runs during Straight Lines)
  if (isDriving) {
    if (leftTicks >= targetTicks || rightTicks >= targetTicks) {
      analogWrite(LEFT_SPEED, 0);
      analogWrite(RIGHT_SPEED, 0);
      isDriving = false;
      Serial.println("DONE"); 
    } 
    else {
      int error = leftTicks - rightTicks;
      int currentBaseL, currentBaseR;

      // Check which way we are driving!
      if (digitalRead(LEFT_DIR) == HIGH) {
        // Forward: Use your perfectly locked-in constants
        currentBaseL = LEFT_BASE_SPEED;  // 80
        currentBaseR = RIGHT_BASE_SPEED; // 82
      } 
      else {
        // Backward: Flip the balance! Right is too strong in reverse.
        currentBaseL = 82; // Boost left
        currentBaseR = 85; // Drop right
      }

      int leftPwm = currentBaseL - (error * kP);
      int rightPwm = currentBaseR + (error * kP);
      
      leftPwm = constrain(leftPwm, 40, 150);
      rightPwm = constrain(rightPwm, 40, 150);

      analogWrite(LEFT_SPEED, leftPwm);
      analogWrite(RIGHT_SPEED, rightPwm);
    }
  }

  if (millis() - lastReportTime > 30) {
    Serial.print("E:");
    Serial.print(leftTicks);
    Serial.print(",");
    Serial.println(rightTicks);
    lastReportTime = millis();
  }
}

// --- HARDWARE INTERRUPT ROUTINE ---
unsigned long lastLeftTime = 0;
unsigned long lastRightTime = 0;

ISR(PCINT0_vect) {
  byte currentLeft = digitalRead(LEFT_ENC);
  byte currentRight = digitalRead(RIGHT_ENC);
  unsigned long currentTime = millis();

  if (currentLeft == HIGH && lastLeftState == LOW) {
    if (currentTime - lastLeftTime > 10) { 
      leftTicks++;
      lastLeftTime = currentTime;
    }
  }
  
  if (currentRight == HIGH && lastRightState == LOW) {
    if (currentTime - lastRightTime > 10) { 
      rightTicks++;
      lastRightTime = currentTime;
    }
  }

  lastLeftState = currentLeft;
  lastRightState = currentRight;
}

// --- COMMAND EXECUTION ---
void executeCommand(String cmd) {
  if (cmd.startsWith("P:")) {
    int state = cmd.substring(2).toInt();
    if (state == 1) penServo.write(PEN_DOWN_ANGLE);
    else penServo.write(PEN_UP_ANGLE);
  }
  else if (cmd.startsWith("D:")) {
    targetTicks = cmd.substring(2).toInt();
    leftTicks = 0;
    rightTicks = 0;
    digitalWrite(LEFT_DIR, HIGH);
    digitalWrite(RIGHT_DIR, HIGH);
    
    analogWrite(LEFT_SPEED, LEFT_BASE_SPEED);
    analogWrite(RIGHT_SPEED, RIGHT_BASE_SPEED);
    isDriving = true; 
  }
  else if (cmd.startsWith("B:")) {
    targetTicks = cmd.substring(2).toInt();
    leftTicks = 0;
    rightTicks = 0;
    
    digitalWrite(LEFT_DIR, LOW);
    digitalWrite(RIGHT_DIR, LOW);
    
    // Apply our new reverse baseline speeds
    analogWrite(LEFT_SPEED, 85);
    analogWrite(RIGHT_SPEED, 82);
    isDriving = true;
  }
  else if (cmd.startsWith("M:")) {
    isDriving = false; 
    int firstComma = cmd.indexOf(',');
    int secondComma = cmd.indexOf(',', firstComma + 1);
    int thirdComma = cmd.indexOf(',', secondComma + 1);

    int speedL = cmd.substring(2, firstComma).toInt();
    int speedR = cmd.substring(firstComma + 1, secondComma).toInt();
    int dirL = cmd.substring(secondComma + 1, thirdComma).toInt();
    int dirR = cmd.substring(thirdComma + 1).toInt();

    digitalWrite(LEFT_DIR, dirL == 1 ? HIGH : LOW);
    digitalWrite(RIGHT_DIR, dirR == 1 ? HIGH : LOW);
    analogWrite(LEFT_SPEED, speedL);
    analogWrite(RIGHT_SPEED, speedR);
  }
  else if (cmd.startsWith("R:")) {
    leftTicks = 0;
    rightTicks = 0;
  }
}