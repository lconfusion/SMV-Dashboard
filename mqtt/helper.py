import random
from paho.mqtt import client as mqtt_client
from .models import Trip, MQTTError
from datetime import datetime
from .topics import topics_list as topics
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import os
import sys
from random import randint

import time

sys.path.append('..')
from smvDashboard.settings import ip_address

LOCATION = [0,0,0]

broker = ip_address
port = 1883
global CLIENT
# Generate a Client ID with the subscribe prefix.
client_id = f'subscribe-{random.randint(0, 100)}'
username = 'smv'
password = os.environ.get("MQTT_PW")

def connect_mqtt(client_id=client_id) -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            MQTTError.objects.create(module='mqtt', event='connect', message='connected', error=False, time=datetime.now(), trip=Trip.objects.last())
        else:
            #error state
            MQTTError.objects.create(module='mqtt', event='connect', message=f"Failed to connect, return code {rc}, client: {client}\n", error=True, time=datetime.now(), trip=Trip.objects.last())
            return None
    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def store(msg):
    channel_layer = get_channel_layer()
    try:
        #1. Compare msg value. Is it in bounds of min/max?
        payload = round(abs(float(msg.payload.decode())), 3) #absolute value of input, rounded to 3 decimal places
        if round(float(msg.payload.decode()), 3) > 999.000 or round(float(msg.payload.decode()), 3) < 0:
            #if out of bounds(needs to be [0, 999.000))
            payload =  round(float(msg.payload.decode()), 3)
            MQTTError.objects.create(module='mqtt', event='receive', message=f'Invalid Argument {msg.payload.decode()}', error=True, time=datetime.now(), trip=Trip.objects.last())
            async_to_sync(channel_layer.group_send)("speed", {"type": f"data.notif", "module": f"{topics[msg.topic]['name']}", "content": payload, "error": True})
            async_to_sync(channel_layer.group_send)("teamdata", {"type": f"team.notif", "module": f"{topics[msg.topic]['name']}", "content": payload, "error": True})
        
        else:
            #error is false unless specifically set
            error = False
            if "max" in topics[msg.topic]:
                #only error handle if max is defined in topics.py
                if not topics[msg.topic]['max'] >= payload and topics[msg.topic]['min'] <= payload:
                    #if payload not in range, error
                    error = True
            MQTTError.objects.create(module='mqtt', event='receive', message=f'{payload}', error=error, time=datetime.now(), trip=Trip.objects.last())
            #update associated model
            topics[msg.topic]['model'].objects.create(date=datetime.now(), data=payload, trip=Trip.objects.last()) 
            if str(msg.topic) == "/DAQ/Latitude" and str(msg.topic) == "/DAQ/Longitude":
                #do NOT deal with long/lat here. need to implement separate feature to store it
                pass
            else:
                #send to team view always, except for lat/long data
                async_to_sync(channel_layer.group_send)("teamdata", {"type": f"team.notif", "module": f"{topics[msg.topic]['name']}", "content": payload, "error": error})
                async_to_sync(channel_layer.group_send)("speed", {"type": f"data.notif", "module": f"{topics[msg.topic]['name']}", "content": payload, "error": error})
    except Exception as e:
        #on error, pass. log error in MQTT Error Log
        MQTTError.objects.create(module='mqtt', event='receive', message=f'{e}', error=True, time=datetime.now(), trip=Trip.objects.last())


def subscribe(topic, client: mqtt_client):
    def on_message(client, userdata, msg):
        store(msg)
    client.subscribe(topic)
    client.on_message = on_message

def run():
    client = connect_mqtt()
    if client:
        for topic in topics:
            subscribe(topic, client)
        client.loop_forever()
    else:
        run()

def publish(topic, message):
    client = connect_mqtt(client_id=f'subscribe-{random.randint(0, 1000)}')
    client.publish(topic, message)
def publish(client, topic, message):
    client.publish(topic, message)

def send_location(lat, long):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("teamdata", {"type": f"team.notif", "module": f"daq.location", "content": {"lat": lat, "long": long}, "error": False})

def test_senddata(channel, module, content, type1):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(channel, {"type": type1, "module": module, "content": content, "error": False})
def test_mqttStress(numPerSec):
    client = connect_mqtt()
    ct = 0
    while ct < numPerSec:
        for key, val in topics.items():
            ct += 1
            publish(client, key, randint(-5,100))
            time.sleep(1/6600)