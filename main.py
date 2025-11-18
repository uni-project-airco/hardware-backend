import json
from pathlib import Path
from typing import Dict

import requests

from vendors.pubnub_client import PubNubClient


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
    chanel_name=CONFIG['pubnub']['channel-name']
)


def pubnub_channel_boot(cfg: Dict) -> None:
    if cfg["pubnub"]["channel-name"] is None:
        url: str = f"{cfg['server-url']}/device/register"
        response: requests.Response = requests.post(
            url=url,
            json={
                "certification-string": cfg["certificate-string"],
                "sensor-id": cfg["sensor-id"],
            },
        )
        if not response.ok:
            raise ValueError("Device certification failed")

        cfg["pubnub"]["channel-name"] = response.json()["channel"]


def boot(cfg: Dict) -> Dict:
    # TODO connect to home wifi if not registered
    # wifi_boot()

    pubnub_channel_boot(cfg)

    # TODO get current thresholds
    # update_config(cfg)

    return cfg


if __name__ == "__main__":
    cfg = load_config(CONFIG_PATH)
    cfg = boot(cfg)
    save_config(CONFIG_PATH, cfg)
