#include <Servo.h>

const int SERVO_PIN = 10;
Servo penServo;

void setup() {
  Serial.begin(115200);
  penServo.attach(SERVO_PIN);
  
  // Start at 90 degrees (Usually Pen UP)
  penServo.write(90); 
  Serial.println("Servo Tester Ready!");
  Serial.println("Type an angle (0 to 180) and press Enter:");
}

void loop() {
  if (Serial.available() > 0) {
    int angle = Serial.parseInt();
    
    // Clear the buffer
    while(Serial.available() > 0) { Serial.read(); }
    
    if (angle >= 0 && angle <= 180) {
      penServo.write(angle);
      Serial.print("Moved Pen Servo to: ");
      Serial.println(angle);
    }
  }
}