import time

import lgpio


class Buzzer:
    frequency = 3000
    period = 1 / frequency

    def __init__(self, pin: int):
        self.chip = lgpio.gpiochip_open(0)
        self.pin = pin
        lgpio.gpio_claim_output(self.chip, pin)

    def _play_sound(self):
        for _ in range(300):
            lgpio.gpio_write(self.chip, self.pin, 1)
            time.sleep(self.period / 2)
            lgpio.gpio_write(self.chip, self.pin, 0)
            time.sleep(self.period / 2)

    def play_alert(self, n_times):
        for _ in range(n_times):
            self._play_sound()
            time.sleep(0.5)

    def __del__(self):
        lgpio.gpiochip_close(self.chip)
