// SPDX-FileCopyrightText: 2025 Stefan Helmert
//
// SPDX-License-Identifier: AGPL-3.0

/*
  Wake up the node to send a keep alive notification in a defined time interval.
*/

#include "MCP7940.h"  // Include the MCP7940 RTC library
#include "Arduino.h"  // Arduino data type definitions
#include "Wire.h"     // Standard I2C "Wire" library

enum alarmTypes {
  matchSeconds,
  matchMinutes,
  matchHours,
  matchDayOfWeek,
  matchDayOfMonth,
  Unused1,
  Unused2,
  matchAll,
  Unknown
};

MCP7940_Class MCP7940; // Create instance of the MCP7940M


// Reed Switch
int in_reed = 0;

// Status LEDs
int led_conn = 6;
int led_err = 7;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.print("START\n");
  delay(1000);
  // put your setup code here, to run once:
  while (!MCP7940.begin()) { // Loop until the RTC communications are established
    delay(500);
    Serial.print("begin failed\n");
  }  // of loop until device is located
  Serial.print("begin done\n");
  delay(1000);
  while (!MCP7940.deviceStatus()) { // Turn oscillator on if necessary
    Serial.print("status off\n");
    if (!MCP7940.deviceStart()) { // Turn oscillator on
      delay(250);
      Serial.print("start failed\n");
    }  // of while the oscillator is off
  }
  Serial.print("start done\n");
  //MCP7940.adjust();  // Use compile date/time to set clock
  DateTime now = MCP7940.now();
  MCP7940.clearAlarm(0);
  MCP7940.clearAlarm(1);
  MCP7940.setAlarm(0, matchSeconds, now - TimeSpan(0, 0, 0, now.second()), true);  // Match once a minute at 0 seconds
  //MCP7940.setAlarm(0, matchMinutes, now - TimeSpan(0, 0, 0, now.second()), true);  // Match once a minute at 0 seconds
  MCP7940.setAlarmPolarity(1);
  MCP7940.setBattery(1);
  MCP7940.setSQWState(false);  
  //MCP7940.setSQWSpeed(0);  // Set the square wave pin
  //MCP7940.writeRegisterBit(MCP7940_CONTROL, 3, 0);
  //MCP7940.setMFP(false);

  pinMode(in_reed, INPUT);
  pinMode(led_conn, OUTPUT);
  pinMode(led_err, OUTPUT);
  digitalWrite(led_conn, LOW);
  digitalWrite(led_err, LOW);


  
  digitalWrite(led_err, LOW);
  // Set poll interval to 60 secs.

}

void loop() {
  bool reed = digitalRead(in_reed);
  bool alarm = MCP7940.isAlarm(0);
  bool pwr_fail = MCP7940.getPowerFail();
  if (alarm) {
    MCP7940.clearAlarm(0);
  }
  if (pwr_fail) {
    MCP7940.clearPowerFail();
  }
  String msg;
  if(!alarm & !reed) {
    msg = "Fehler, kein Ereignis!";
  } else if(!alarm & reed) {
    msg = "Probensammler W1 ist voll";
  } else if(alarm & !reed) {
    msg = "Probensammler W1 regelmäßiger Statusbericht";
  } else {
    msg = "Probensammler W1 ist voll und Statusbericht";
  }

  if (pwr_fail) {
    msg += " - Unterbrechung Stromversorgung erkannt!";
  }
  DateTime       now = MCP7940.now();
  Serial.print(now.year());
  Serial.print("-");
  Serial.print(now.month());
  Serial.print("-");
  Serial.print(now.day());
  Serial.print(" ");
  
  Serial.print(now.hour());
  Serial.print(":");
  Serial.print(now.minute());
  Serial.print(":");
  Serial.print(now.second());
  Serial.print(" ");
  
  Serial.print(MCP7940.oscOK());
  Serial.print("\n");


}
