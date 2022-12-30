#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
This scripts reads sensors from the SenseHAT and publishes them on an MQTT broker.
Author: @cgomesu
Repo: https://github.com/cgomesu/rpi-sensehat-mqtt
"""

# local imports
import src.constants as const
# import src.errors as errors
import src.utils as utils
import src.mqtt as mqtt
import src.sensehat as sensehat
# external imports
import logging
from signal import signal, SIGINT, SIGHUP, SIGTERM, pause
import sys
import threading

# start a loggin instance for this module using constants
logging.basicConfig(filename=const.LOG_FILENAME, format=const.LOG_FORMAT, datefmt=const.LOG_DATEFMT)
logger = logging.getLogger(__name__)
logger.setLevel(const.LOG_LEVEL)
logger.debug("Initilized a logger object.")

# methods for sense object threads
def streaming_sensor():
    logger.info("Starting main sensor publishing loop.")
    while not stop_streaming.is_set():
        logger.debug("Updating and publishing sensor data.")
        mqtt_pub_sensor.publish(sense_sensor.sensors_data())
        logger.debug(f"Waiting for signal or timeout ({config.resolution}).")
        stop_streaming.wait(config.resolution)
        if not stop_streaming.is_set():
            logger.debug(f"Reached wait timeout.")

# TODO
def streaming_led():
    while not stop_streaming.is_set():
        # check queue and if not empyt, dequeue, parse and show, then loop
        pass

def streaming_joystick():
    while not stop_streaming.is_set():
        logger.info(f"Waiting for joystick directions.")
        sense_joystick.wait_directions(stop_streaming)
        if not sense_joystick.directions.empty():
            logger.info(f"A joystick direction was detected. Publishing direction from queue.")
            mqtt_pub_joystick.publish(sense_joystick.joystick_data())

# methods of the main logic
def start(*signals):
    logger.info("Starting service.")
    # trap signals from args using stop function as handler
    for s in signals: signal(s, stop)
    # global lists of objects
    global senses, mqtts, threads
    senses = []
    mqtts = []
    threads = []
    # thread helpers
    global stop_streaming
    stop_streaming = threading.Event()

def stop(signum, frame=None):
    logger.info(f"Received a signal '{signum}' to stop.")
    # cleanup procedures
    stop_streaming.set()
    # disconnect and stop threads
    for m in mqtts:
        if m.is_enabled: m.disable()
    # turn off sensehat led and so on
    for s in senses:
        if s.is_enabled: s.disable()
    # exit the application
    sys.exit(signum)

def main():
    # startup procedure to trap INT, HUP, TERM signals
    start(SIGINT, SIGHUP, SIGTERM)
    # TODO: catch exceptions in object initialization and loop logic
    # create a config object
    global config
    config = utils.Configuration()
    # create sensehat objects
    global sense_sensor, sense_led, sense_joystick
    sense_sensor = sensehat.SenseHatSensor(rounding=config.sensehat_rounding,
                                        acceleration_multiplier=config.sensehat_acceleration_multiplier,
                                        gyroscope_multiplier=config.sensehat_gyroscope_multiplier)
    sense_led = sensehat.SenseHatLed(low_light=config.sensehat_low_light)
    sense_joystick = sensehat.SenseHatJoystick()
    senses.extend([sense_sensor, sense_led, sense_joystick])
    # create mqtt objects
    global mqtt_pub_sensor, mqtt_sub_led, mqtt_pub_joystick
    mqtt_pub_sensor = mqtt.MqttClientPub(broker_address=config.mqtt_broker_address,
                            zone=config.mqtt_zone,
                            room=config.mqtt_room,
                            client_name=config.mqtt_client_name,
                            type='sensor',
                            client_id=f"{config.mqtt_client_name}_sensor",
                            user=config.mqtt_user,
                            password=config.mqtt_password)
    mqtt_sub_led = mqtt.MqttClientSub(broker_address=config.mqtt_broker_address,
                            zone=config.mqtt_zone,
                            room=config.mqtt_room,
                            client_name=config.mqtt_client_name,
                            type='led',
                            client_id=f"{config.mqtt_client_name}_led",
                            user=config.mqtt_user,
                            password=config.mqtt_password)
    mqtt_pub_joystick = mqtt.MqttClientPub(broker_address=config.mqtt_broker_address,
                            zone=config.mqtt_zone,
                            room=config.mqtt_room,
                            client_name=config.mqtt_client_name,
                            type='joystick',
                            client_id=f"{config.mqtt_client_name}_joystick",
                            user=config.mqtt_user,
                            password=config.mqtt_password)
    mqtts.extend([mqtt_pub_sensor, mqtt_sub_led, mqtt_pub_joystick])
    # thread handlers
    thread_sensor = threading.Thread(target=streaming_sensor)
    thread_led = threading.Thread(target=streaming_led)
    thread_joystick = threading.Thread(target=streaming_joystick)
    threads.extend([thread_sensor, thread_led, thread_joystick])
    # finished setting up, then print welcome message if set (blocking)
    if config.welcome_msg: sense_led.sense.show_message(config.welcome_msg)
    # start threads and wait for interrupt signal in this one
    logger.debug(f"Starting threads '{threads}'.")
    for t in threads: t.start()
    logger.info(f"Main thread is done. Waiting for interrupt.")
    pause()

if __name__ == "__main__":
    main()
