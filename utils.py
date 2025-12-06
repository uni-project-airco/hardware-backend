from typing import Dict


def calculate_air_quality_index(data: Dict, thresholds: Dict):
    weights = {
        "co2": 0.40,
        "pm25": 0.30,
        "humidity": 0.15,
        "temperature": 0.15
    }

    aqi = 0
    max_aqi = 100
    danger_trigger = 70
    danger_zone = False

    for parameter, value in data.items():
        if parameter in thresholds:
            warning = thresholds[parameter].get("warning")
            danger = thresholds[parameter].get("danger")

            if value >= danger:
                danger_zone = True

            if value <= warning:
                aqi_contrib = 0
            elif value <= danger:
                aqi_contrib = (value - warning) / (danger - warning) * max_aqi
            else:
                aqi_contrib = max_aqi

            aqi += aqi_contrib * weights[parameter]

    if danger_zone:
        aqi = max(aqi, danger_trigger)

    aqi = min(aqi, max_aqi)

    return round(aqi)
