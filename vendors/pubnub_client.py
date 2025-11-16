from typing import Dict

from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub


class PubNubClient:
    pn_config = PNConfiguration()

    def __init__(self):
        self.pubnub = PubNub(self.pn_config)

    @classmethod
    def configure(cls, config: Dict):
        cls.pn_config.subscribe_key = config["pubnub"]["subscribe-key"]
        cls.pn_config.publish_key = config["pubnub"]["publish-key"]
        cls.pn_config.user_id = "telemetry-sensor"
        cls.pn_config.enable_subscribe = True
        cls.pn_config.connect_timeout = 10
        cls.pn_config.non_subscribe_request_timeout = 30
        cls.pn_config.origin = "ps.pndsn.com"

        cls.__sensor_id = config.get("sensor-id")
        cls.__channel = config["pubnub"]["channel-name"]

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


if __name__ == "__main__":
    from main import load_config

    config = load_config("../config.json")
    PubNubClient.configure(config)
    pb = PubNubClient()
    pb.send_telemetry("data", 123)
