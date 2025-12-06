import json
import logging
import threading
import time
from pathlib import Path
from time import sleep
from typing import Dict

import board
import busio
import requests

from sensors.pmsa003i import PMSA003ISensor
from sensors.scd4x import SCD4xSensor
from vendors.pubnub_client import PubNubClient


logging.basicConfig(
    filename='./logfile.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(path: Path) -> Dict:
    with open(path) as f:
        return json.load(f)


def save_config(path: Path, cfg: Dict) -> None:
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)


CONFIG_PATH = Path(__file__).parent / "config.json"
CONFIG = load_config(CONFIG_PATH)
PUBNUB_CLIENT = PubNubClient(
    sub_key=CONFIG['pubnub']['subscribe-key'],
    pub_key=CONFIG['pubnub']['publish-key'],
    sensor_id=CONFIG['sensor-id'],
    chanel_name=CONFIG['pubnub']['channel-name'],
    access_token=CONFIG['pubnub']['access-token']
)


def pubnub_channel_boot(cfg: Dict) -> None:
    if cfg["pubnub"]["channel-name"] is None:
        url: str = f"{cfg['server-url']}/sensor/register"
        response: requests.Response = requests.post(
            url=url,
            json={
                "sensor-id": cfg["sensor-id"],
            },
            headers={"certificate-string": cfg['certificate-string'], "sensor-id": cfg['sensor-id']}

        )
        if not response.ok:
            raise ValueError("Device certification failed")

        cfg["pubnub"]["channel-name"] = response.json()["channel"]
        cfg["pubnub"]["access-token"] = response.json()["token"]


def boot(cfg: Dict) -> Dict:
    # TODO connect to home wifi if not registered
    # wifi_boot()

    pubnub_channel_boot(cfg)

    # TODO get current thresholds
    # update_config(cfg)

    return cfg


shared_state: dict = {}
stop_flag = False
lock = threading.Lock()


def read_telemetry_data() -> None:
    I2C = busio.I2C(board.SCL, board.SDA, frequency=100000)
    pm_sensor = PMSA003ISensor(I2C, reset_pin=None)
    scd_sensor = SCD4xSensor(I2C)

    global shared_state, stop_flag
    while not stop_flag:
        with lock:
            scd_data = scd_sensor.read_telemetry()
            pm_data = pm_sensor.read_telemetry()

            shared_state["temperature"] = scd_data["temperature"]
            shared_state["co2"] = scd_data["co2"]
            shared_state["humidity"] = scd_data["humidity"]
            shared_state["pm25"] = pm_data["p_25"]

        time.sleep(0.5)


def send_alerts(cfg: Dict) -> None:
    previous_alerts = {
        "temperature": "normal",
        "humidity": "normal",
        "co2": "normal",
        "pm25": "normal",
    }

    global shared_state, stop_flag
    while not stop_flag:
        with lock:
            snapshot = dict(shared_state)

        if snapshot:
            for key, value in snapshot.items():
                if (value > cfg['thresholds'][key]['danger']) and (previous_alerts[key] != "danger"):
                    previous_alerts[key] = 'danger'
                    PUBNUB_CLIENT.send_alert(title=f"{key} alert",
                                             message=f"{key} in a dangerous level: {value}",
                                             status='high')
                elif (value > cfg['thresholds'][key]['warning']) and (
                        previous_alerts[key] not in ['warning', 'danger']):
                    previous_alerts[key] = 'warning'
                    PUBNUB_CLIENT.send_alert(title=f"{key} alert",
                                             message=f"{key} in a warning level: {value}",
                                             status='warning')
                elif value < cfg['thresholds'][key]['warning'] and (previous_alerts[key] != "normal"):
                    previous_alerts[key] = 'normal'
            logger.info("Alerts check", snapshot)
            sleep(2)


if __name__ == "__main__":
    try:
        logger.info("Program launched")
        cfg = load_config(CONFIG_PATH)
        cfg = boot(cfg)
        save_config(CONFIG_PATH, cfg)
        cfg = load_config(CONFIG_PATH)

        t_writer = threading.Thread(target=read_telemetry_data, daemon=True)
        t_alerts = threading.Thread(target=send_alerts, args=(cfg,), daemon=True)

        t_writer.start()
        t_alerts.start()

        while True:
            calculations = {
                "temperature": 0,
                "humidity": 0,
                "co2": 0,
                "pm25": 0,
            }
            for i in range(6):  # total 10 minutes
                with lock:
                    snapshot = dict(shared_state)

                for key, value in snapshot.items():
                    calculations[key] += value
                sleep(2 * 60)
            response = requests.post(url=f'{cfg["server-url"]}/telemetry/save_telemetry', json={
                "temperature": round(calculations['temperature'] / 5),
                "humidity": round(calculations['humidity'] / 5),
                "co2": round(calculations['co2'] / 5),
                "pm25": round(calculations['pm25'] / 5),
            }, headers={"certificate-string": cfg['certificate-string'], "sensor-id": cfg['sensor-id']})

            logger.info("Telemetry sent", response.status_code)

    finally:
        stop_flag = True
        time.sleep(2)
