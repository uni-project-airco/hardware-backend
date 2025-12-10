import logging
from typing import Callable, Optional

import requests
from pubnub.callbacks import SubscribeCallback
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub


class ThresholdUpdateCallback(SubscribeCallback):
    def __init__(self, message_handler: Optional[Callable] = None):
        self.message_handler = message_handler

    def message(self, pubnub, message):
        if self.message_handler:
            self.message_handler(message.message)


class PubNubClient:

    def __init__(self, sub_key: str, pub_key: str, sensor_id: str, chanel_name: str, access_token: str, server_url: str,
                 certification_string: str):
        pn_config = PNConfiguration()
        pn_config.subscribe_key = sub_key
        pn_config.publish_key = pub_key
        pn_config.user_id = "telemetry-sensor"
        pn_config.enable_subscribe = True
        pn_config.connect_timeout = 10
        pn_config.non_subscribe_request_timeout = 30
        pn_config.origin = "ps.pndsn.com"

        self.pubnub = PubNub(pn_config)
        self.pubnub.set_token(access_token)
        self.__sensor_id = sensor_id
        self.__channel = chanel_name
        self.__callback = None
        self._server_url = server_url
        self.__certification_string = certification_string

    def subscribe(self, message_handler: Optional[Callable] = None):
        self.__callback = ThresholdUpdateCallback(message_handler)
        self.pubnub.add_listener(self.__callback)
        self.pubnub.subscribe().channels(self.__channel).execute()

    def unsubscribe(self):
        if self.__callback:
            self.pubnub.remove_listener(self.__callback)
        self.pubnub.unsubscribe().channels(self.__channel).execute()

    def _send_message(self, message, mtype, ):
        pb_resource = self.pubnub.publish().channel(self.__channel).message(message).custom_message_type(mtype).sync()

        if pb_resource.status.status_code == 403:
            logging.info("Updating pubnub auth key")
            resource = requests.post(url=f'{self._server_url}/sensor/refresh-token',
                                     headers={
                                         "certificate-string": self.__certification_string,
                                         "sensor-id": self.__sensor_id})
            if resource.ok:
                self.pubnub.set_token(resource.json()["token"])
                self.pubnub.publish().channel(self.__channel).message(message).custom_message_type(mtype).sync()
            else:
                logging.error(f"Failed to update pubnub auth key: {resource.status_code} - {resource.json()}")

    def send_telemetry(self, **kwargs):
        messages = {
            "request_type": "send_telemetry",
            "sensor_id": self.__sensor_id,
            "aqi": kwargs.get("aqi"),
            "telemetry": {
                "temperature": kwargs.get("temperature"),
                "humidity": kwargs.get("humidity"),
                "co2_level": kwargs.get("co2"),
                "pm2_level": kwargs.get("pm25")
            }

        }
        self._send_message(message=messages, mtype="sensor-telemetry")

    def send_alert(self, title: str, message: str, value, status: str):
        messages = {
            "request_type": "send_alert",
            "title": title,
            "message": message,
            "value": value,
            "status": status
        }
        self._send_message(message=messages, mtype="sensor-alert")
