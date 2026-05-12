String command;

void setup() {
  // Must match the 115200 baud rate we set on the Pi
  Serial.begin(115200);
  
  // NOTE: Later, you will define your motor pins here
  // pinMode(motorPin1, OUTPUT); 
}

void loop() {
  // Check if the Pi sent a message
  if (Serial.available() > 0) {
    
    // Read the incoming word until the newline ('\n') character
    command = Serial.readStringUntil('\n');
    
    // CRITICAL: .trim() removes any hidden spaces or carriage returns (\r) 
    // that might cause the 'if' statements to fail to match.
    command.trim(); 
    
    Serial.print("Arduino interpreting command: ");
    Serial.println(command);

    // --- The Shape Decision Tree ---
    if (command == "Circle") {
      drawCircle();
    } 
    else if (command == "Square") {
      drawSquare();
    }
    else if (command == "Rectangle") {
      drawRectangle();
    }
    else if (command == "Triangle") {
      drawTriangle();
    }
    else if (command == "5 Pointed Star") {
      drawStar();
    }
    else if (command == "Line") {
      drawLine();
    }
    else {
      Serial.println("Error: Unknown shape command received.");
    }
  }
}

// ** MOTOR CONTROL ROUTINE PLACEHOLDERS **
void drawCircle() {
  Serial.println("--> Starting motors for Circle pattern...");
  // Example logic you will add later:
  // analogWrite(leftMotorSpeed, 200);
  // analogWrite(rightMotorSpeed, 100); 
}

void drawSquare() {
  Serial.println("--> Starting motors for Square pattern...");
  // Example logic you will add later:
  // driveForward(); delay(1000); turn90Degrees(); // Repeat 4x
}

void drawRectangle() {
  Serial.println("--> Starting motors for Rectangle pattern...");
}

void drawTriangle() {
  Serial.println("--> Starting motors for Triangle pattern...");
}

void drawStar() {
  Serial.println("--> Starting motors for 5 Pointed Star pattern...");
}

void drawLine() {
  Serial.println("--> Starting motors for Straight Line pattern...");
}