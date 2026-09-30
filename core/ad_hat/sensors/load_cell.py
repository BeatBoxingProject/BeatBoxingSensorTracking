# /*****************************************************************************
# * | File        :   sensors/load_cell.py
# * | Description :   Load cell strain-gauge approach for AD HAT
# ******************************************************************************/
from typing import Optional

try:
    from .base import BaseSensor
except (ImportError, ValueError):
    try:
        from core.ad_hat.sensors.base import BaseSensor
    except (ImportError, ValueError):
        from sensors.base import BaseSensor

try:
    from ..device import ADHat
except (ImportError, ValueError):
    try:
        from core.ad_hat.device import ADHat
    except (ImportError, ValueError):
        from device import ADHat


class LoadCell(BaseSensor):
    """
    Sensor model for strain-gauge load cells connected to the AD HAT.

    Load cells utilize a Wheatstone bridge circuit producing low-millivolt differential
    signals proportional to applied force or weight.

    This class encapsulates differential channel pairs, programmable gain settings,
    tare (zero-offset calibration), and scale factor conversion to physical units
    (grams, kilograms, or Newtons).
    """

    def __init__(
        self,
        hat: ADHat,
        diff_channel: int = 0,
        gain: str = 'ADS1263_GAIN_64',
        scale_factor: float = 1.0,
        name: Optional[str] = None
    ):
        """
        :param hat: ADHat controller instance.
        :param diff_channel: Differential channel pair (0: AIN0-AIN1, 1: AIN2-AIN3, etc.).
        :param gain: ADS1263 PGA gain setting (recommended: 32x or 64x for small bridge signals).
        :param scale_factor: Calibration multiplier converting (volts - offset) to engineering units.
        :param name: Optional friendly sensor identifier.
        """
        super().__init__(hat=hat, name=name or f"LoadCell_DiffCH{diff_channel}")
        self.diff_channel = diff_channel
        self.gain = gain
        self.scale_factor = scale_factor
        self.tare_offset = 0.0

    def configure_hardware(self):
        """Applies optimal gain and differential mode settings on the AD HAT."""
        self.hat.set_mode(self.hat.MODE_DIFFERENTIAL)
        self.hat.set_gain(self.gain)

    def read_raw(self) -> int:
        """Reads raw 32-bit count from the differential channel pair."""
        return self.hat.read_raw(self.diff_channel)

    def read_voltage(self) -> float:
        """Reads differential voltage in Volts across the bridge input pair."""
        return self.hat.read_diff_voltage(self.diff_channel)

    def read_value(self) -> float:
        """
        Calculates applied force/weight using tare offset and scale factor.
        Formula: (voltage - tare_offset) * scale_factor
        """
        net_voltage = self.read_voltage() - self.tare_offset
        return net_voltage * self.scale_factor

    def tare(self, samples: int = 20) -> float:
        """
        Zeroes the load cell by averaging quiescent readings under no load.
        """
        total = sum(self.read_voltage() for _ in range(samples))
        self.tare_offset = total / max(samples, 1)
        return self.tare_offset

    def calibrate(self, known_load: float, samples: int = 20) -> float:
        """
        Calculates the scale factor given a known applied load.
        """
        total = sum(self.read_voltage() for _ in range(samples))
        avg_voltage = total / max(samples, 1)
        net_voltage = avg_voltage - self.tare_offset
        if net_voltage != 0:
            self.scale_factor = known_load / net_voltage
        return self.scale_factor
