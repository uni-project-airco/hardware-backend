from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

from utils import calculate_air_quality_index


class PubNubClient:

    def __init__(self, sub_key: str, pub_key: str, sensor_id: str, chanel_name: str, access_token: str):
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

    def send_telemetry(self, **kwargs):
        aqi = calculate_air_quality_index(kwargs)
        messages = {
            "request_type": "send_telemetry",
            "sensor_id": self.__sensor_id,
            "aqi": aqi,
            "telemetry": {
                "temperature": kwargs.get("temperature"),
                "humidity": kwargs.get("humidity"),
                "co2_level": kwargs.get("co2"),
                "pm2_level": kwargs.get("pm25")
            }

        }
        self.pubnub.publish().channel(self.__channel).message(messages).custom_message_type("sensor-telemetry").sync()

    def send_alert(self, title: str, message: str, status: str):
        messages = {
            "request_type": "send_alert",
            "title": title,
            "message": message,
            "status": status
        }
        self.pubnub.publish().channel(self.__channel).message(messages).custom_message_type("sensor-alert").sync()
