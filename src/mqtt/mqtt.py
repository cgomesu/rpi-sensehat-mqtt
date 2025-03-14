"""
Module that contains application-specific MQTT functions.
This module is meant to be use in conjunction with the paho-mqtt package.
"""
# local imports
from src.constants import constants as const
from src.utils import validate as val
from src.errors import errors as err
# external imports
import logging
from abc import ABC, abstractmethod
from paho.mqtt import client as mqttc
from urllib.parse import urlparse
import json
# message handling via queue
from queue import Queue

# start a loggin instance for this module using constants
logging.basicConfig(filename=const.LOG_FILENAME, format=const.LOG_FORMAT, datefmt=const.LOG_DATEFMT)
logger = logging.getLogger(__name__)
logger.setLevel(const.LOG_LEVEL)
logger.debug("Initilized a logger object.")

class MqttClient(ABC):
    """
    ABC for MqttClient subclasses. Force use of either Pub or Sub subclasses.
    Paho mqtt doc: https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php
    """
    # class conventions
    # additional topic prefix
    SENSOR = 'sensor'
    LED = 'led'
    JOYSTICK = 'joystick'
    TYPES = [SENSOR, LED, JOYSTICK]
    # valid payload names for each function; this is appended to the topic after type
    COMMAND = 'cmd'
    STATUS = 'status'
    FUNCTIONS = [COMMAND, STATUS]

    def __init__(self, broker_address, zone, room, client_name, type, client_id, user, password):
        # check broker_url first
        try:
            b_url = urlparse(broker_address)
            if not val.broker_url(b_url):
                logger.info(f"There was an error parsing the address {broker_address}.")
                raise err.InvalidMqttAttr(f"There was an error parsing the address {broker_address}.", 'broker_address')
            self._broker_url = b_url
        except ValueError as verr:
            logger.info(f"There was a value error parsing the address {broker_address}: '{verr.args}'")
            raise err.InvalidMqttAttr(f"Unable to parse the address {broker_address}: '{verr.args}'", 'broker_address')
        self._zone = zone
        self._room = room
        self._client_name = client_name
        self._type = type
        self._client_id = client_id
        self._user = user
        self._password = password
        # build topic from zone, room, client_name, and type
        topics = [t for t in [self._zone, self._room, self._client_name, self._type] if t]
        self._topic = "/".join(map(str, topics))
        # attr for the paho mqtt client for this object
        self._client = None
        # other common class object helpers
        self._is_enabled = False
        self._is_connected = False
        self._messages = Queue()
        # initialize connection procedure
        self.connect()
        # MQTT client object has been fully initialized
        self._is_enabled = True
        logger.info(f"The client/type subscriber '{self._client_name}/{self._type}' for the broker '{self._broker_url.hostname}' was initialized.")

    @property
    def client(self):
        return self._client
    @client.setter
    def client(self, client:mqttc.Client):
        self._client = client

    @property
    def is_enabled(self):
        return self._is_enabled
    @is_enabled.setter
    def is_enabled(self, state:bool):
        self._is_enabled = state
    
    @property
    def is_connected(self):
        return self._is_connected
    @is_connected.setter
    def is_connected(self, state:bool):
        self._is_connected = state
    
    @property
    def broker_url(self):
        return self._broker_url
    
    @property
    def client_name(self):
        return self._client_name

    @property
    def zone(self):
        return self._zone

    @property
    def room(self):
        return self._room
    
    @property
    def topic(self):
        return self._topic

    @property
    def type(self):
        return self._type
    @type.setter
    def type(self, type):
        self._type = type if type in MqttClient.TYPES else None

    @property
    def client_id(self):
        return self._client_id
    
    @property
    def user(self):
        return self._user
    
    @property
    def password(self):
        return self._password

    @property
    def messages(self):
        return self._messages
    @messages.setter
    def messages(self, messages:Queue):
        self._messages = messages

    @abstractmethod
    def on_connect(self, client, userdata, flags, rc):
        pass

    @abstractmethod
    def on_disconnect(self, client, userdata, rc):
        pass

    def on_message(self, client, userdata, message):
        # clients that parse messages should message.get() them if not messages.empty()
        self.messages.put(message)
        logger.debug(f"The cliet/type '{self.client_name}/{self.type}' enqueued an encoded message.")

    def on_log(client, userdata, level, buff):
        # only for logging purposes
        # log to our log file any log messages caught by paho.mqtt (e.g., exceptions)
        logger.debug(f"[paho.mqtt.client] {buff}")

    def on_publish(self, client, userdata, mid):
        # only for logging purposes
        logger.debug(f"The broker '{self.broker_url.hostname}' has ACK publish request of mid '{mid}' by '{self.client_name}/{self.type}'.")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        # only for logging purposes
        logger.debug(f"The broker '{self.broker_url.hostname}' has ACK subscribe request of mid '{mid}' by '{self.client_name}/{self.type}'.")

    def connect(self):
        """
        Init helper to connect this object's client to its broker.
        Beware that this method calls both connect_async() and loop_start(), so
        cleanup is required afterwards--see disable().
        """
        # protocol selection
        if self.broker_url.scheme == 'ws':
            self.client = mqttc.Client(client_id=self.client_id, transport='websockets')
        else:
            # assume default protocol
            self.client = mqttc.Client(client_id=self.client_id)
        # custom mqtt function references
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_log = self.on_log
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe
        # TODO: TLS support
        # credentials handling
        if self.user:
            self.client.username_pw_set(username=self.user, password=self.password)
        # connect to the broker in a non-blocking way
        self.client.connect_async(host=self.broker_url.hostname,
                                port=self.broker_url.port,
                                keepalive=30)
        self.client.loop_start()

    def disable(self):
        """
        Method that disables the client (disconnect and stop loop if initialized).
        To be used in exit, interrupts, and cleanup procedures.
        """
        logger.debug(f"Received a call to disable the client and type '{self.client_name}/{self.type}'.")
        # disconnect and stop object's client
        if self.is_enabled:
            self.client.disconnect()
            self.client.loop_stop()
            self.is_enabled=False

class MqttClientSub(MqttClient):
    """
    Class that generates an MQTT client subscriber.
    """
    def __init__(self,
                broker_address:str,
                zone:str,
                room:str,
                client_name:str,
                type:str,
                client_id:str,
                user:str = None,
                password:str = None):
        super().__init__(broker_address=broker_address,
                        zone=zone,
                        room=room,
                        client_name=client_name,
                        type=type,
                        client_id=client_id,
                        user=user,
                        password=password)
        # Subs subscribe to the COMMAND topic because they just need to parse commands to this client type
        self._full_topic = self.topic+'/'+MqttClient.COMMAND

    @property
    def full_topic(self):
        return self._full_topic
    @full_topic.setter
    def full_topic(self, full_topic:str):
        self._full_topic = full_topic

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # MQTT connected
            self.is_connected = True
            logger.info(f"The client/type '{self.client_name}/{self.type}' connected successfully to '{self.broker_url.hostname}'.")
            self.client.subscribe(topic=self.full_topic, qos=0)
            logger.debug(f"Subscribed to topic '{self.full_topic}' from broker '{self.broker_url.hostname}'.")
        else:
            # Connection error
            logger.info(f"The client/type '{self.client_name}/{self.type}' got an error ({rc}) trying to connect to '{self.broker_url.hostname}'.")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            # MQTT disconnected
            self.is_connected = False
            logger.info(f"The client/type '{self.client_name}/{self.type}' was disconnected from '{self.broker_url.hostname}'.")
            self.client.unsubscribe(topic=self.full_topic)
            logger.debug(f"Unsubscribed from topic '{self.full_topic}' from broker '{self.broker_url.hostname}'.")
    
    # class specific methods
    def decoded_message(self)->dict:
        """
        Method that decodes a message from this object's queue and returns a dict containig its contents
        """
        if self.messages.empty():
            return {}
        # deqeue and stringify message
        message = self.messages.get()
        message = str(message.payload.decode("utf-8"))
        # assume message is always JSON format
        try:
            return json.loads(message)
        except json.JSONDecodeError as jerr:
            logger.info(f"There was an error deserializing the following message: '{message}'. Error: '{jerr.msg}'")
            raise err.MqttDecodingError(f"There was an error deserializing the message.", jerr.msg)
        except TypeError:
            logger.info(f"The following message is of wrong type: '{message}'.")
            raise err.MqttDecodingError(f"The message is of wrong type.", 'TypeError')

class MqttClientPub(MqttClient):
    """
    Class that generates an MQTT client publisher.
    """
    def __init__(self,
                broker_address:str,
                zone:str,
                room:str,
                client_name:str,
                type:str,
                client_id:str,
                user:str = None,
                password:str = None):
        super().__init__(broker_address=broker_address,
                        zone=zone,
                        room=room,
                        client_name=client_name,
                        type=type,
                        client_id=client_id,
                        user=user,
                        password=password)
        # Pubs publish to the STATUS topic because they just need to set status to this client type
        self._full_topic = self.topic+'/'+MqttClient.STATUS

    @property
    def full_topic(self):
        return self._full_topic
    @full_topic.setter
    def full_topic(self, full_topic:str):
        self._full_topic = full_topic

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # MQTT connected
            self.is_connected = True
            logger.info(f"The client/type '{self.client_name}/{self.type}' connected successfully to '{self.broker_url.hostname}'.")
        else:
            # Connection error
            logger.info(f"The client/type '{self.client_name}/{self.type}' got an error ({rc}) trying to connect to '{self.broker_url.hostname}'.")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            # MQTT disconnected
            self.is_connected = False
            logger.info(f"The client/type '{self.client_name}/{self.type}' was disconnected from '{self.broker_url.hostname}'.")

    # class specific methods
    def publish(self, data:dict)->None:
        """
        Method to publish data in dict format to the MQTT broker.
        Make sure the topic is right for the data dict format and function is a string
        that indicates the last topic for this publisher (e.g., 'status' to publish
        sensor data; 'cmd' to publish a command that will be digested by a topic subscriber).
        """
        json_data = json.dumps(data)
        self.client.publish(topic=self.full_topic,
                            payload=json_data,
                            qos=0,
                            retain=True)
        logger.debug(f"A publish request to topic '{self.full_topic}' was made to publish the following JSON data: {json_data}.")
