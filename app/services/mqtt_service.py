import json
import logging
from typing import Callable

import paho.mqtt.client as mqtt

from app.core.config import settings

logger = logging.getLogger(__name__)


class MQTTService:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self._handlers: dict[str, Callable] = {}

        if settings.MQTT_USERNAME:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker")
            for topic in self._handlers:
                client.subscribe(topic)
        else:
            logger.error("MQTT connection failed with code %s", rc)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            payload = msg.payload.decode()
        for pattern, handler in self._handlers.items():
            if mqtt.topic_matches_sub(pattern, msg.topic):
                handler(msg.topic, payload)

    def subscribe(self, topic: str, handler: Callable):
        self._handlers[topic] = handler
        if self.client.is_connected():
            self.client.subscribe(topic)

    def publish(self, topic: str, payload: dict):
        self.client.publish(topic, json.dumps(payload))

    def start(self):
        self.client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()


mqtt_service = MQTTService()
