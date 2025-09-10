#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Stefan Helmert
#
# SPDX-License-Identifier: AGPL-3.0

import json
import smtplib
from email.mime.text import MIMEText
from paho.mqtt.client import Client
from dotenv import dotenv_values
import base64


creds = dotenv_values(".env")

TTN_APP_ID = creds.get("TTN_APP_ID")
TTN_ACCESS_KEY = creds.get("TTN_ACCESS_KEY")

MQTT_BROKER = creds.get("MQTT_BROKER", "eu1.cloud.thethings.network")
MQTT_PORT = creds.get("MQTT_PORT", 1883)
MQTT_TOPIC = creds.get("MQTT_TOPIC", f"v3/{TTN_APP_ID}@ttn/devices/+/up")

EMAIL_FROM = creds.get("EMAIL_FROM")
EMAIL_TO = creds.get("EMAIL_TO")
SMTP_SERVER = creds.get("SMTP_SERVER")
SMTP_PORT = creds.get("SMTP_PORT", 587)
SMTP_USER = creds.get("SMTP_USER")
SMTP_PASSWORD = creds.get("SMTP_PASSWORD")

def filter_msg(payload):
    return True

def build_msg(payload):
    data = json.loads(payload)
    dev_ids = data.get("end_device_ids")
    dev_id = dev_ids.get("device_id")
    recv_at = data.get("received_at")
    up_msg = data.get("uplink_message")
    frm_payload = up_msg.get("frm_payload")
    dec_payload = base64.b64decode(frm_payload).decode("utf-8")
    subject = f"[IoT msg] {dec_payload[:32]}"
    body = f"device: {dev_id}\ndate: {recv_at}\nmsg: {dec_payload}"
    return {"subject": subject, "body": body}

def send_email(betreff, text):
    msg = MIMEText(text)
    msg["Subject"] = betreff
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

# === MQTT CALLBACKS ===
def on_connect(client, userdata, flags, rc):
    print("Connecting to MQTT Broker")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print("Raw msg:", payload)
    mail = build_msg(payload)
    print("Fwd msg:", mail)
    if filter_msg(payload):
        send_email(mail.get("subject"), mail.get("body"))

# === HAUPTPROGRAMM ===
client = Client()
client.username_pw_set(TTN_APP_ID, TTN_ACCESS_KEY)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()

