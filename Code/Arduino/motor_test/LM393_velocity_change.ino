// Motor Control Pins
#define PWMA 5    
#define AIN1 7    
#define PWMB 6    
#define BIN1 8    
#define STBY 3    

// Variables to hold our tick counts (volatile because they are changed in an interrupt)
volatile unsigned int leftTicks = 0;
volatile unsigned int rightTicks = 0;

// Variables for our 100ms timer
unsigned long lastTime = 0;
uint8_t lastPinState = 0;

void setup() {
  Serial.begin(9600);
  
  // Motor Setup
  pinMode(PWMA, OUTPUT); pinMode(AIN1, OUTPUT);
  pinMode(PWMB, OUTPUT); pinMode(BIN1, OUTPUT);
  pinMode(STBY, OUTPUT); digitalWrite(STBY, HIGH);
  
  // Sensor Setup (Pins 12 and 13)
  pinMode(12, INPUT);
  pinMode(13, INPUT);

  // --- ADVANCED: Pin Change Interrupt (PCINT) Setup ---
  // This tells the Arduino chip to trigger an interrupt whenever Pin 12 or 13 changes state.
  PCICR |= 0b00000001;    // Enable PCINT for Port B (Digital Pins 8 to 13)
  PCMSK0 |= 0b00110000;   // Enable PCINT specifically for Pin 12 (PB4) and Pin 13 (PB5)
  lastPinState = PINB & 0b00110000; // Record initial state

  // Print CSV Headers for your data file
  Serial.println("Time(ms),LeftTicks,RightTicks");
  
  // Start driving forward
  digitalWrite(AIN1, HIGH); digitalWrite(BIN1, HIGH);
  analogWrite(PWMA, 150);   // Set left speed
  analogWrite(PWMB, 150);   // Set right speed
}

void loop() {
  // Every 100 milliseconds, print the data
  if (millis() - lastTime >= 100) {
    lastTime = millis();
    
    // Print in CSV format: Time, Left, Right
    Serial.print(lastTime);
    Serial.print(",");
    Serial.print(leftTicks);
    Serial.print(",");
    Serial.println(rightTicks);
  }
}

// --- The Hardware Interrupt Routine ---
// This runs instantly in the background whenever Pin 12 or 13 changes
ISR(PCINT0_vect) {
  uint8_t currentState = PINB & 0b00110000; // Read Pins 12 and 13
  uint8_t changedPins = currentState ^ lastPinState; // Find out which pin changed
  
  if (changedPins & 0b00010000) leftTicks++;  // If Pin 12 changed, add a left tick
  if (changedPins & 0b00100000) rightTicks++; // If Pin 13 changed, add a right tick
  
  lastPinState = currentState;
}