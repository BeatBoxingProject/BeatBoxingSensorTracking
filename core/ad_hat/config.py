# /*****************************************************************************
# * | File        :   config.py
# * | Function    :   Hardware underlying interface for Waveshare AD HAT (ADS1263)
# ******************************************************************************/
import os
import sys
import time

# Pin definitions for Raspberry Pi HAT
RST_PIN = 18
CS_PIN = 22
DRDY_PIN = 17

HAS_HARDWARE = False

class RaspberryPi:
    RST_PIN = RST_PIN
    CS_PIN = CS_PIN
    DRDY_PIN = DRDY_PIN

    def __init__(self):
        import spidev
        import RPi.GPIO

        self.GPIO = RPi.GPIO
        self.SPI = spidev.SpiDev(0, 0)

    def digital_write(self, pin, value):
        self.GPIO.output(pin, value)

    def digital_read(self, pin):
        return self.GPIO.input(pin)

    def delay_ms(self, delaytime):
        time.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.SPI.writebytes(data)

    def spi_readbytes(self, reg):
        return self.SPI.readbytes(reg)

    def module_init(self):
        self.GPIO.setmode(self.GPIO.BCM)
        self.GPIO.setwarnings(False)
        self.GPIO.setup(self.RST_PIN, self.GPIO.OUT)
        self.GPIO.setup(self.CS_PIN, self.GPIO.OUT)
        self.GPIO.setup(self.DRDY_PIN, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)
        self.SPI.max_speed_hz = 2000000
        self.SPI.mode = 0b01
        return 0

    def module_exit(self):
        try:
            self.SPI.close()
        except Exception:
            pass
        try:
            self.GPIO.output(self.RST_PIN, 0)
            self.GPIO.output(self.CS_PIN, 0)
            self.GPIO.cleanup()
        except Exception:
            pass


class MockHardware:
    """Mock interface for development/testing when running off-Pi."""
    RST_PIN = RST_PIN
    CS_PIN = CS_PIN
    DRDY_PIN = DRDY_PIN

    def __init__(self):
        self._pins = {self.RST_PIN: 1, self.CS_PIN: 1, self.DRDY_PIN: 0}
        self._last_cmd = 0
        self._regs = {0: 0x20}  # REG_ID: 0x20 >> 5 == 1

    def digital_write(self, pin, value):
        self._pins[pin] = value

    def digital_read(self, pin):
        return self._pins.get(pin, 0)

    def delay_ms(self, delaytime):
        # Keep mock delays minimal for snappy testing
        pass

    def spi_writebyte(self, data):
        if data:
            self._last_cmd = data[0]
            # Write register command: 0x40 | reg
            if (data[0] & 0xE0) == 0x40 and len(data) >= 3:
                reg_addr = data[0] & 0x1F
                self._regs[reg_addr] = data[2]

    def spi_readbytes(self, reg):
        # RDATA1 (0x12) or RDATA2 (0x14) status polling or data read
        if self._last_cmd in (0x12, 0x14):
            if reg == 1:
                return [0xC0]  # Bits 6 and 7 high -> conversion complete
            if reg == 5:
                # 4 bytes value 0x00001020 + checksum 0xCB
                return [0x00, 0x00, 0x10, 0x20, 0xCB]
        # Read register command: 0x20 | reg
        if (self._last_cmd & 0xE0) == 0x20:
            reg_addr = self._last_cmd & 0x1F
            return [self._regs.get(reg_addr, 0x00)] * reg
        return [0x20] * reg

    def module_init(self):
        return 0

    def module_exit(self):
        pass


try:
    implementation = RaspberryPi()
    HAS_HARDWARE = True
except (ImportError, Exception):
    implementation = MockHardware()
    HAS_HARDWARE = False

for func in [x for x in dir(implementation) if not x.startswith('_')]:
    setattr(sys.modules[__name__], func, getattr(implementation, func))
