from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub


class PubNubClient:

    def __init__(self, sub_key: str, pub_key: str, sensor_id: str, chanel_name: str):
        pn_config = PNConfiguration()
        pn_config.subscribe_key = sub_key
        pn_config.publish_key = pub_key
        pn_config.user_id = "telemetry-sensor"
        pn_config.enable_subscribe = True
        pn_config.connect_timeout = 10
        pn_config.non_subscribe_request_timeout = 30
        pn_config.origin = "ps.pndsn.com"

        self.pubnub = PubNub(pn_config)
        self.__sensor_id = sensor_id
        self.__channel = chanel_name

    def send_telemetry(self, telemetry_type, value):
        messages = {
            "request_type": "send_telemetry",
            "sensor_id": self.__sensor_id,
            "telemetry_type": telemetry_type,
            "value": value,
        }
        self.pubnub.publish().channel(self.__channel).message(messages).sync()

    def get_alerts(self):
        pass
