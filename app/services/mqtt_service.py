import asyncio
import json
import logging
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from app.core.config import settings

logger = logging.getLogger(__name__)


class MQTTService:
    def __init__(self):
        self.client = mqtt.Client(client_id="smart_helmet_backend")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self._handlers: dict[str, Callable] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        if settings.MQTT_USERNAME:
            self.client.username_pw_set(
                settings.MQTT_USERNAME, settings.MQTT_PASSWORD
            )

    # ── Callbacks (run in paho-mqtt's network thread) ────────────────────

    def _on_connect(self, client, _userdata, _flags, rc):
        if rc == 0:
            logger.info(
                "[MQTT] Connected to broker at %s:%s",
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
            )
            for topic in self._handlers:
                client.subscribe(topic)
                logger.info("[MQTT] Subscribed to topic: %s", topic)
        else:
            logger.error(
                "[MQTT] Connection failed (rc=%s) — will retry", rc
            )

    def _on_disconnect(self, _client, _userdata, rc):
        if rc != 0:
            logger.warning(
                "[MQTT] Unexpected disconnect (rc=%s) — reconnecting", rc
            )

    def _on_message(self, _client, _userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning(
                "[MQTT] Non-JSON payload on topic %s — ignored", msg.topic
            )
            return

        for pattern, handler in self._handlers.items():
            if mqtt.topic_matches_sub(pattern, msg.topic):
                if asyncio.iscoroutinefunction(handler):
                    # Bridge sync paho thread → async event loop
                    if self._loop and self._loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            handler(msg.topic, payload), self._loop
                        )
                    else:
                        logger.warning(
                            "[MQTT] No running event loop; message dropped"
                        )
                else:
                    handler(msg.topic, payload)

    # ── Public API ────────────────────────────────────────────────────────

    def subscribe(self, topic: str, handler: Callable):
        """Register a topic handler (sync or async coroutine function)."""
        self._handlers[topic] = handler
        if self.client.is_connected():
            self.client.subscribe(topic)

    def publish(self, topic: str, payload: dict):
        self.client.publish(topic, json.dumps(payload))

    def start(self, loop: asyncio.AbstractEventLoop):
        """Connect to the broker and start the background network thread."""
        self._loop = loop
        try:
            self.client.connect(
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
                keepalive=60,
            )
            self.client.reconnect_delay_set(min_delay=1, max_delay=30)
            self.client.loop_start()
            logger.info("[MQTT] Service started")
        except Exception as exc:
            logger.error("[MQTT] Could not connect to broker: %s", exc)

    def stop(self):
        """Cleanly disconnect and stop the network thread."""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("[MQTT] Service stopped")
        except Exception:
            pass


mqtt_service = MQTTService()
