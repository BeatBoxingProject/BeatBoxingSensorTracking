# /*****************************************************************************
# * | File        :   sensors/piezo.py
# * | Description :   Piezoelectric sensor approach for AD HAT
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


class PiezoSensor(BaseSensor):
    """
    Sensor model for piezoelectric elements connected to the AD HAT.

    Piezoelectric sensors generate dynamic transient voltage spikes in response to
    mechanical stress or physical impact (such as a punch strike).

    This class encapsulates channel mapping, baseline voltage tracking, and provides
    the extension hooks for impact threshold detection and peak force capture.
    """

    def __init__(
        self,
        hat: ADHat,
        channel: int = 0,
        threshold_volts: float = 0.5,
        name: Optional[str] = None
    ):
        """
        :param hat: ADHat controller instance.
        :param channel: Single-ended analog channel index (0 to 9).
        :param threshold_volts: Voltage threshold above baseline to register an impact.
        :param name: Optional friendly sensor identifier.
        """
        super().__init__(hat=hat, name=name or f"Piezo_CH{channel}")
        self.channel = channel
        self.threshold_volts = threshold_volts
        self.baseline_voltage = 0.0

    def read_raw(self) -> int:
        """Reads raw 32-bit count from the piezo channel."""
        return self.hat.read_raw(self.channel)

    def read_voltage(self) -> float:
        """Reads instantaneous voltage in Volts from the piezo channel."""
        return self.hat.read_voltage(self.channel)

    def read_value(self) -> float:
        """
        Returns the instantaneous voltage relative to the baseline.
        Future domain logic (peak capture, impact event filtering) can be expanded here.
        """
        return self.read_voltage() - self.baseline_voltage

    def calibrate_baseline(self, samples: int = 10) -> float:
        """
        Measures the quiescent baseline voltage when no impact is present.
        Hook for future baseline drift correction.
        """
        total = sum(self.read_voltage() for _ in range(samples))
        self.baseline_voltage = total / max(samples, 1)
        return self.baseline_voltage

    def detect_impact(self, threshold: Optional[float] = None) -> bool:
        """
        Determines whether the current reading exceeds the impact threshold.
        Hook for future peak detection and debouncing logic.
        """
        thresh = threshold if threshold is not None else self.threshold_volts
        return abs(self.read_value()) >= thresh
