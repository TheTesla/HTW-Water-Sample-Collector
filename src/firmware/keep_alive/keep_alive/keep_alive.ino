// SPDX-FileCopyrightText: 2025 Stefan Helmert
//
// SPDX-License-Identifier: AGPL-3.0

/*
  Wake up the node to send a keep alive notification in a defined time interval.
*/

//#define DEBUG 

#include <MKRWAN.h>
#include <MCP7940.h>  // Include the MCP7940 RTC library
#include "arduino_secrets.h"

// Name in message
String name = "Probensammler F1";

// Reed Switch
int in_reed = 7;

// Status LEDs
int led_dbg = 6;
int led_err = 1;

// Wakeup Interval
int interval_hours = 1;
int interval_minutes = 30;
int interval_seconds = 0; 


/*        Input processing functions
          ========================== */

bool read_reed()
{
  pinMode(in_reed, INPUT);
  bool reed = digitalRead(in_reed);
  pinMode(in_reed, OUTPUT);
  digitalWrite(in_reed, LOW); // discharge input, prevent floating charge
  return reed;
}

/*        Debug helper functions
          ====================== */

void debug_init()
{
#ifdef DEBUG
  delay(1000);
  Serial.begin(115200);
  delay(100);
  Serial.print("DEBUG INIT\n");
  delay(100);
#endif
}

void debug_print(String dbg_msg)
{
#ifdef DEBUG
  Serial.print(dbg_msg);
  Serial.print("\n");
#endif
}

void debug_led(int d)
{
  pinMode(led_dbg, OUTPUT);
  if (led_dbg < 0) return;
  if (0 == d) {
    digitalWrite(led_dbg, LOW);
  } else {
    digitalWrite(led_dbg, HIGH);
  }
}


/*        Error reporting functions
          ========================= */

enum errorTypes {
  OK,
  ERR_RTC_COMM,
  ERR_RTC_OSC,
  ERR_WAN_MODEM,
  ERR_WAN_JOIN,
  ERR_WAN_SEND,
};

const char* const errString[] = {
  "OK",
  "ERR_RTC_COMM",
  "ERR_RTC_OSC",
  "ERR_WAN_MODEM",
  "ERR_WAN_JOIN",
  "ERR_WAN_SEND",
};

void log_err(int e = 1)
{
  debug_print(errString[e]);
  pinMode(led_err, OUTPUT);
  if (led_err < 0) return;
  if (0 == e) {
    digitalWrite(led_err, LOW);
  } else {
    digitalWrite(led_err, HIGH);
  }
}


/*        LoRa WAN communication functions
          ================================ */

// Please enter your sensitive data in the Secret tab or arduino_secrets.h
String appEui = SECRET_APP_EUI;
String appKey = SECRET_APP_KEY;

LoRaModem modem;       // Create instance of the integrated LoRa modem

String lora_comm(String msg)
{
  int err;
  int i = 0;
  while (!modem.begin(EU868)) {
    log_err(ERR_WAN_MODEM);
    i++;
    if(i>4) return "";
  }
  log_err(OK);
  i = 0;
  while (!modem.joinOTAA(appEui, appKey)) {
    log_err(ERR_WAN_JOIN);
    i++;
    if(i>4) return "";
  }
  log_err(OK);
  // Set poll interval to 60 secs.
  modem.minPollInterval(60);
  // NOTE: independent of this setting, the modem will
  // not allow sending more than one message every 2 minutes,
  // this is enforced by firmware and can not be changed.
  modem.beginPacket();
  modem.print(msg);
  err = modem.endPacket(true);
  if (err > 0) {
    log_err(OK);
  } else {
    log_err(ERR_WAN_SEND);
    return "";
  }
  delay(10000); // wait until data is received
  if (!modem.available()) {
    return "";
  }
  String rcv = "";
  i = 0;
  while (modem.available()) {
    rcv += (char)modem.read();
    i++;
    if(i>255) break;
  }
  return rcv;
}


/*        Real Time Clock and Alarm functions
          =================================== */

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

void set_clock()
{
  while (!MCP7940.begin()) { // Loop until the RTC communications are established
    log_err(ERR_RTC_COMM);
    delay(500);
  }  // of loop until device is located
  while (!MCP7940.deviceStatus()) { // Turn oscillator on if necessary
    while (!MCP7940.deviceStart()) { // Turn oscillator on
      log_err(ERR_RTC_OSC);
      delay(250);
    }  // of while the oscillator is off
  }
  MCP7940.setBattery(1);
  MCP7940.setSQWState(false);  
  MCP7940.setAlarmState(0, false);  
  MCP7940.setAlarmState(1, false);  
  MCP7940.setMFP(1);  
}

void set_alarm(const TimeSpan& span)
{
  DateTime now = MCP7940.now();
  // "The ALMxIF bit cannot be written to a 1 in software. Writing to the ALMxWKDAY register will always clear
  // the ALMxIF bit." Datasheet
  MCP7940.setAlarm(0, matchAll, now + span, true);  // Match time span in the future, clears ALMxIF bit
  MCP7940.setAlarmPolarity(1);
  MCP7940.setSQWState(false);  
  MCP7940.clearAlarm(0); // not needed, because ALMxIF bit already cleared
}


/*        Application functions
          ===================== */

String create_msg(bool reed, bool alarm, bool pwr_fail)
{
  String msg;
  if(!alarm & !reed) {
    msg = name + " - Erstinbetriebnahme!";
  } else if(!alarm & reed) {
    msg = name + " ist voll";
  } else if(alarm & !reed) {
    msg = name + " regelmäßiger Statusbericht";
  } else {
    msg = name + " ist voll und Statusbericht";
  }
  if (pwr_fail) {
    msg += " - Unterbrechung Stromversorgung erkannt!";
  }
  return msg;
}

void setup() {
  debug_led(0);
  log_err(OK);
  debug_led(1);
  debug_init();
  set_clock();
  bool reed = read_reed();
  bool alarm = MCP7940.isAlarm(0);
  bool pwr_fail = MCP7940.getPowerFail();
  String msg = create_msg(reed, alarm, pwr_fail);
  String rcv = lora_comm(msg);
  debug_print("Received: " + rcv);
  if (pwr_fail) MCP7940.clearPowerFail();
  debug_led(0);
}

void loop()
{
  set_alarm(TimeSpan(0, interval_hours, interval_minutes, interval_seconds));
  delay(500);
}

