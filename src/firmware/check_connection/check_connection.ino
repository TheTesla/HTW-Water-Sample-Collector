// SPDX-FileCopyrightText: 2025 Stefan Helmert
//
// SPDX-License-Identifier: AGPL-3.0

/*
  Lora Check connection for Iot
  This sketch checks LoRa avability for MKR WAN 1300/1310 LoRa module.
*/

#include <MKRWAN.h>

LoRaModem modem;

// Uncomment if using the Murata chip as a module
// LoRaModem modem(Serial1);

#include "arduino_secrets.h"
// Please enter your sensitive data in the Secret tab or arduino_secrets.h
String appEui = SECRET_APP_EUI;
String appKey = SECRET_APP_KEY;

// Status LEDs
int led_conn = 6;
int led_err = 7;

void setup() {
  // put your setup code here, to run once:
  // change this to your regional band (eg. US915, AS923, ...)

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
  String msg = "Probensammler W1 ist voll";


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
