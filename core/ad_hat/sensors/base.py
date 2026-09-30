# /*****************************************************************************
# * | File        :   sensors/base.py
# * | Description :   Base abstraction for sensors connected to the AD HAT
# ******************************************************************************/
from abc import ABC, abstractmethod
from typing import Any, Optional

try:
    from ..device import ADHat
except (ImportError, ValueError):
    try:
        from core.ad_hat.device import ADHat
    except (ImportError, ValueError):
        from device import ADHat


class BaseSensor(ABC):
    """
    Abstract base class for any sensor connected to the Waveshare AD HAT.

    Subclasses implement specific measurement approaches (e.g. Piezo impact detection,
    Load cell strain-gauge force measurement, potentiometer, etc.) while sharing
    a common hardware access and reading lifecycle.
    """

    def __init__(self, hat: ADHat, name: Optional[str] = None):
        """
        :param hat: Configured and active ADHat instance.
        :param name: Optional friendly identifier for this sensor.
        """
        self.hat = hat
        self.name = name or self.__class__.__name__

    @abstractmethod
    def read_raw(self) -> int:
        """Read the raw ADC count from the configured channel(s)."""
        pass

    @abstractmethod
    def read_voltage(self) -> float:
        """Read the physical voltage (in Volts) from the sensor channel."""
        pass

    @abstractmethod
    def read_value(self) -> Any:
        """
        Read the processed domain-specific measurement value.
        For Piezo: dynamic impact/peak voltage or trigger state.
        For Load Cell: calibrated force or weight (grams/Newtons).
        """
        pass
