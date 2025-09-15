// SPDX-FileCopyrightText: 2025 Stefan Helmert
//
// SPDX-License-Identifier: AGPL-3.0

/*
  Wake up the node to send a keep alive notification in a defined time interval.
*/

#include <MKRWAN.h>
#include <MCP7940.h>  // Include the MCP7940 RTC library

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

LoRaModem modem;       // Create instance of the integrated LoRa modem

#include "arduino_secrets.h"
// Please enter your sensitive data in the Secret tab or arduino_secrets.h
String appEui = SECRET_APP_EUI;
String appKey = SECRET_APP_KEY;

// Reed Switch
int in_reed = 0;

// Status LEDs
int led_conn = 6;
int led_err = 7;

void setup() {
  // put your setup code here, to run once:
  while (!MCP7940.begin()) { // Loop until the RTC communications are established
    delay(1000);
  }  // of loop until device is located
  while (!MCP7940.deviceStatus()) { // Turn oscillator on if necessary
    while (!MCP7940.deviceStart()) { // Turn oscillator on
      delay(1000);
    }  // of while the oscillator is off
  }
  MCP7940.adjust();  // Use compile date/time to set clock
  DateTime now = MCP7940.now(); 
  MCP7940.setAlarm(0, matchSeconds, now - TimeSpan(0, 0, 0, now.second()), true);  // Match once a minute at 0 seconds
  MCP7940.setAlarmPolarity(1);
  MCP7940.setBattery(1);

  pinMode(in_reed, INPUT);
  pinMode(led_conn, OUTPUT);
  pinMode(led_err, OUTPUT);
  digitalWrite(led_conn, LOW);
  digitalWrite(led_err, LOW);

  if (!modem.begin(EU868)) {
    digitalWrite(led_err, HIGH);
  };
  digitalWrite(led_err, LOW);

  
  while (!modem.joinOTAA(appEui, appKey)) {
    digitalWrite(led_err, HIGH);
  }
  digitalWrite(led_conn, HIGH);
  digitalWrite(led_err, LOW);
  // Set poll interval to 60 secs.
  modem.minPollInterval(60);
  // NOTE: independent of this setting, the modem will
  // not allow sending more than one message every 2 minutes,
  // this is enforced by firmware and can not be changed.

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


  int err;
  modem.beginPacket();
  modem.print(msg);
  err = modem.endPacket(true);
  if (err > 0) {
    digitalWrite(led_err, LOW);
  } else {
    digitalWrite(led_err, HIGH);
  }
  delay(1000);
  if (!modem.available()) {
    return;
  }
  char rcv[64];
  int i = 0;
  while (modem.available()) {
    rcv[i++] = (char)modem.read();
  }
  for (unsigned int j = 0; j < i; j++) {
  }

}
