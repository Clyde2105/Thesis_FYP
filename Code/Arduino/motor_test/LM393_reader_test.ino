void setup() {
  Serial.begin(9600);
  pinMode(12, INPUT); // Left Sensor
  pinMode(13, INPUT); // Right Sensor
}

void loop() {
  int leftState = digitalRead(12);
  int rightState = digitalRead(13);
  
  Serial.print("Left: ");
  Serial.print(leftState);
  Serial.print(" | Right: ");
  Serial.println(rightState);
  
  delay(100); // Small delay to make it readable
}