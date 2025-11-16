from time import sleep
from typing import Literal

import adafruit_dht
import board


class DHT22:
    def __init__(self, pin: board.Pin):
        self.__pin = pin
        self._dht = adafruit_dht.DHT22(pin, use_pulseio=False)

    def read_telemetry(self, parameter: Literal["temperature", "humidity"]) -> int:
        context = {
            "temperature": self._dht.temperature,
            "humidity": self._dht.humidity
        }

        for i in range(5):  # try five times before error
            try:
                if result := context[parameter]:
                    return result
            except RuntimeError as e:
                sleep(2.0)
                pass
        raise RuntimeError("Failed to reed temperature from DHT-25")
