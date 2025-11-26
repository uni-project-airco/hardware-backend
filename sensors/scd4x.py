from typing import Literal, Optional
import time

import board
import busio
import adafruit_scd4x


class SCD4xSensor:
    def __init__(
        self,
        i2c: busio.I2C,
        *,
        start_periodic: bool = True,
        max_initial_wait_sec: int = 10,
        max_retries: int = 7,
        retry_delay_sec: float = 1.0,
    ):
        self._scd = adafruit_scd4x.SCD4X(i2c)
        self._max_retries = max_retries
        self._retry_delay_sec = retry_delay_sec

        if start_periodic:
            self._scd.start_periodic_measurement()
            # Initial blocking wait until first measurement (like your script)
            start_time = time.time()
            while not self._scd.data_ready:
                if time.time() - start_time > max_initial_wait_sec:
                    raise TimeoutError("SCD4x initial measurement not ready in time")
                time.sleep(1.0)

    def _ensure_data_ready(self) -> bool:
        for _ in range(self._max_retries):
            if self._scd.data_ready:
                return True
            time.sleep(self._retry_delay_sec)
        return False

    def read_telemetry(self) -> dict:
        if not self._ensure_data_ready():
            raise RuntimeError("SCD4x data not ready after retries")

        return {
            "co2": self._scd.CO2,
            "temperature": self._scd.temperature,
            "humidity": self._scd.relative_humidity,
        }
