# /*****************************************************************************
# * | File        :   device.py
# * | Description :   High-level Pythonic interface for Waveshare AD HAT (ADS1263)
# ******************************************************************************/
import time
from typing import Dict, List, Optional, Union

try:
    from .ADS1263 import ADS1263, ADS1263_GAIN, ADS1263_DRATE
    from .config import HAS_HARDWARE
except (ImportError, ValueError):
    from ADS1263 import ADS1263, ADS1263_GAIN, ADS1263_DRATE
    from config import HAS_HARDWARE


# Numerical gain multiplier lookup
GAIN_FACTORS = {
    'ADS1263_GAIN_1': 1,
    'ADS1263_GAIN_2': 2,
    'ADS1263_GAIN_4': 4,
    'ADS1263_GAIN_8': 8,
    'ADS1263_GAIN_16': 16,
    'ADS1263_GAIN_32': 32,
    'ADS1263_GAIN_64': 64,
}


class ADHat:
    """
    High-level controller for the Waveshare High-Precision AD HAT (ADS1263).
    
    Provides convenient methods for single-ended and differential voltage readings,
    configurable sampling rate, programmable gain amplifier (PGA), and context
    management.
    """

    MODE_SINGLE_ENDED = 0
    MODE_DIFFERENTIAL = 1

    def __init__(
        self,
        ref_voltage: float = 5.08,
        rate: str = 'ADS1263_400SPS',
        gain: str = 'ADS1263_GAIN_1',
        mode: int = MODE_SINGLE_ENDED
    ):
        """
        Initialize the AD HAT controller.

        :param ref_voltage: Reference voltage in Volts (external AVDD/AVSS typically ~5.08V).
        :param rate: Default sampling rate key from ADS1263_DRATE (e.g. 'ADS1263_400SPS').
        :param gain: Default PGA gain key from ADS1263_GAIN (e.g. 'ADS1263_GAIN_1').
        :param mode: 0 for Single-ended (AIN0-AIN9), 1 for Differential (5 pairs).
        """
        self.ref_voltage = ref_voltage
        self.rate_key = rate
        self.gain_key = gain
        self.gain_factor = GAIN_FACTORS.get(gain, 1)
        self.mode = mode
        self.adc: Optional[ADS1263] = None
        self._is_open = False

    @property
    def is_hardware_available(self) -> bool:
        """Indicates if physical hardware SPI/GPIO drivers are present."""
        return HAS_HARDWARE

    def open(self) -> bool:
        """
        Initializes SPI/GPIO and powers up the ADS1263 ADC.

        :return: True if initialization succeeded, False otherwise.
        """
        if self._is_open:
            return True

        self.adc = ADS1263()
        init_result = self.adc.ADS1263_init_ADC1(self.rate_key)
        if init_result == -1:
            self._is_open = False
            return False

        self.set_mode(self.mode)
        self.set_gain(self.gain_key)
        self._is_open = True
        return True

    def close(self):
        """Safely shuts down the ADC and releases GPIO/SPI hardware resources."""
        if self.adc is not None and self._is_open:
            try:
                self.adc.ADS1263_Exit()
            except Exception:
                pass
            self._is_open = False

    def __enter__(self):
        if not self.open():
            raise RuntimeError("Failed to initialize Waveshare AD HAT (ADS1263).")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def set_mode(self, mode: int):
        """
        Sets the measurement mode.
        :param mode: 0 for single-ended (10 channels), 1 for differential (5 pairs).
        """
        if mode not in (self.MODE_SINGLE_ENDED, self.MODE_DIFFERENTIAL):
            raise ValueError(f"Invalid mode {mode}. Expected 0 (single-ended) or 1 (differential).")
        self.mode = mode
        if self.adc:
            self.adc.ADS1263_SetMode(mode)

    def set_gain(self, gain_key: str):
        """
        Configures the programmable gain amplifier (PGA).
        :param gain_key: Valid ADS1263_GAIN key (e.g. 'ADS1263_GAIN_1', 'ADS1263_GAIN_64').
        """
        if gain_key not in ADS1263_GAIN:
            raise ValueError(f"Unknown gain '{gain_key}'. Valid options: {list(ADS1263_GAIN.keys())}")
        self.gain_key = gain_key
        self.gain_factor = GAIN_FACTORS.get(gain_key, 1)
        if self.adc and self._is_open:
            gain_val = ADS1263_GAIN[gain_key]
            drate_val = ADS1263_DRATE[self.rate_key]
            self.adc.ADS1263_ConfigADC(gain_val, drate_val)

    def set_rate(self, rate_key: str):
        """
        Configures the sampling rate.
        :param rate_key: Valid ADS1263_DRATE key (e.g. 'ADS1263_400SPS', 'ADS1263_14400SPS').
        """
        if rate_key not in ADS1263_DRATE:
            raise ValueError(f"Unknown rate '{rate_key}'. Valid options: {list(ADS1263_DRATE.keys())}")
        self.rate_key = rate_key
        if self.adc and self._is_open:
            gain_val = ADS1263_GAIN[self.gain_key]
            drate_val = ADS1263_DRATE[rate_key]
            self.adc.ADS1263_ConfigADC(gain_val, drate_val)

    def raw_to_voltage(self, raw_value: int) -> float:
        """
        Converts a 32-bit ADC raw integer value to Volts, accounting for signed
        conversion, reference voltage, and PGA gain factor.
        """
        # Convert unsigned 32-bit read to signed integer
        if raw_value & 0x80000000:
            # Negative voltage
            signed_val = raw_value - 0x100000000
        else:
            signed_val = raw_value

        # Calculate voltage relative to full-scale range and PGA gain
        voltage = (signed_val * self.ref_voltage / 0x7FFFFFFF) / self.gain_factor
        return voltage

    def read_raw(self, channel: int) -> int:
        """
        Reads the raw 32-bit count for the specified channel.
        :param channel: Channel number (0-9 for single-ended, 0-4 for differential).
        """
        if not self._is_open:
            raise RuntimeError("ADHat device is not open. Call open() or use 'with ADHat():'")
        return self.adc.ADS1263_GetChannalValue(channel)

    def read_voltage(self, channel: int) -> float:
        """
        Reads the single-ended analog voltage on the specified channel (AIN0-AIN9).
        Automatically switches mode to single-ended if currently in differential.
        :param channel: 0 to 9
        :return: Voltage in Volts.
        """
        if channel < 0 or channel > 9:
            raise ValueError("Single-ended channel must be between 0 and 9.")
        if self.mode != self.MODE_SINGLE_ENDED:
            self.set_mode(self.MODE_SINGLE_ENDED)

        raw = self.read_raw(channel)
        return self.raw_to_voltage(raw)

    def read_diff_voltage(self, pair: int) -> float:
        """
        Reads differential analog voltage across a channel pair:
          - Pair 0: AIN0 - AIN1
          - Pair 1: AIN2 - AIN3
          - Pair 2: AIN4 - AIN5
          - Pair 3: AIN6 - AIN7
          - Pair 4: AIN8 - AIN9
        Automatically switches mode to differential if currently single-ended.
        :param pair: 0 to 4
        :return: Differential voltage in Volts.
        """
        if pair < 0 or pair > 4:
            raise ValueError("Differential pair index must be between 0 and 4.")
        if self.mode != self.MODE_DIFFERENTIAL:
            self.set_mode(self.MODE_DIFFERENTIAL)

        raw = self.read_raw(pair)
        return self.raw_to_voltage(raw)

    def read_all_voltages(self, channels: Optional[List[int]] = None) -> Dict[int, float]:
        """
        Reads voltages from multiple channels sequentially.
        :param channels: List of channel indices (default: [0, 1, 2, 3, 4]).
        :return: Dictionary mapping channel index to voltage in Volts.
        """
        if channels is None:
            channels = [0, 1, 2, 3, 4]
        results = {}
        for ch in channels:
            if self.mode == self.MODE_DIFFERENTIAL:
                results[ch] = self.read_diff_voltage(ch)
            else:
                results[ch] = self.read_voltage(ch)
        return results
