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
from utils import calculate_air_quality_index
from vendors.pubnub_client import PubNubClient
from devices.buzzer import Buzzer

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
config_lock = threading.Lock()


def update_pubnub_token_in_config(new_token: str) -> None:
    with config_lock:
        cfg = load_config(CONFIG_PATH)
        cfg['pubnub']['access-token'] = new_token
        save_config(CONFIG_PATH, cfg)
        logger.info("Updated PubNub access token in config file")


PUBNUB_CLIENT = PubNubClient(
    sub_key=CONFIG['pubnub']['subscribe-key'],
    pub_key=CONFIG['pubnub']['publish-key'],
    sensor_id=CONFIG['sensor-id'],
    chanel_name=CONFIG['pubnub']['channel-name'],
    access_token=CONFIG['pubnub']['access-token'],
    server_url=CONFIG['server-url'],
    certification_string=CONFIG['certificate-string'],
    config_update_callback=update_pubnub_token_in_config
)
CURRENT_THRESHOLDS = {}


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
            raise RuntimeError("Device certification failed")

        cfg["pubnub"]["channel-name"] = response.json()["channel"]
        cfg["pubnub"]["access-token"] = response.json()["token"]


def boot(cfg: Dict) -> Dict:
    # TODO connect to home wifi if not registered
    # wifi_boot()

    pubnub_channel_boot(cfg)
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

            shared_state["temperature"] = round(scd_data["temperature"])
            shared_state["co2"] = scd_data["co2"]
            shared_state["humidity"] = round(scd_data["humidity"])
            shared_state["pm25"] = pm_data["p_25"]

        time.sleep(0.5)


def send_alerts(cfg: Dict) -> None:
    previous_alerts = {
        "temperature": "normal",
        "humidity": "normal",
        "co2": "normal",
        "pm25": "normal",
    }
    buzzer = Buzzer(18)

    global shared_state, stop_flag, CURRENT_THRESHOLDS
    while not stop_flag:
        with lock:
            snapshot = dict(shared_state)

        with config_lock:
            thresholds = dict(CURRENT_THRESHOLDS)

        if snapshot:
            for key, value in snapshot.items():
                if (value > thresholds[key]['danger']) and (previous_alerts[key] != "danger"):
                    previous_alerts[key] = 'danger'
                    PUBNUB_CLIENT.send_alert(title=f"{key} alert",
                                             message=f"{key} in a dangerous level: {value}",
                                             status='high',
                                             value=value
                                             )
                    buzzer.play_alert(5)
                elif (value > thresholds[key]['warning']) and (
                        previous_alerts[key] not in ['warning', 'danger']):
                    previous_alerts[key] = 'warning'
                    PUBNUB_CLIENT.send_alert(title=f"{key} alert",
                                             message=f"{key} in a warning level: {value}",
                                             status='warning',
                                             value=value
                                             )
                elif value < thresholds[key]['warning'] and (previous_alerts[key] != "normal"):
                    previous_alerts[key] = 'normal'
        sleep(2)


def send_telemetry_update(cfg: Dict) -> None:
    global shared_state, stop_flag, CURRENT_THRESHOLDS
    while not stop_flag:
        with lock:
            snapshot = dict(shared_state)

        with config_lock:
            thresholds = dict(CURRENT_THRESHOLDS)

        if snapshot:
            snapshot["aqi"] = calculate_air_quality_index(snapshot, thresholds)
            PUBNUB_CLIENT.send_telemetry(**snapshot)
        sleep(10)


def handle_pubnub_message(message: Dict) -> None:
    global CURRENT_THRESHOLDS, CONFIG_PATH

    request_type = message.get("request_type", None)

    if request_type == "change_thresholds_level":
        thresholds = message.get("thresholds")
        if thresholds:
            logger.info(f"Received threshold update: {thresholds}")

            with config_lock:
                cfg = load_config(CONFIG_PATH)
                cfg['thresholds'] = thresholds
                save_config(CONFIG_PATH, cfg)
                CURRENT_THRESHOLDS = thresholds
                logger.info(f"Updated thresholds in config: {thresholds}")


def listen_pubnub_messages() -> None:
    global stop_flag
    try:
        PUBNUB_CLIENT.subscribe(message_handler=handle_pubnub_message)
        logger.info("Subscribed to PubNub channel for threshold updates")

        while not stop_flag:
            sleep(1)
    except Exception as e:
        logger.error(f"Error in PubNub listener thread: {e}")
    finally:
        PUBNUB_CLIENT.unsubscribe()
        logger.info("Unsubscribed from PubNub channel")


if __name__ == "__main__":
    try:
        logger.info("Program launched")
        cfg = load_config(CONFIG_PATH)
        cfg = boot(cfg)
        save_config(CONFIG_PATH, cfg)
        cfg = load_config(CONFIG_PATH)
        CURRENT_THRESHOLDS = cfg['thresholds']

        t_writer = threading.Thread(target=read_telemetry_data, daemon=True)
        t_alerts = threading.Thread(target=send_alerts, args=(cfg,), daemon=True)
        t_update = threading.Thread(target=send_telemetry_update, args=(cfg,), daemon=True)
        t_pubnub_listener = threading.Thread(target=listen_pubnub_messages, daemon=True)

        t_writer.start()
        t_alerts.start()
        t_update.start()
        t_pubnub_listener.start()

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

            logger.info(f"Telemetry sent - {response.status_code}")

    finally:
        stop_flag = True
        time.sleep(2)
