#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Ddingdong firmware booted");
}

void loop() {
  delay(1000);
}
