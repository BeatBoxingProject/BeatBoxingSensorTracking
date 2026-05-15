# region Imports
import time
import socket
import json
from smbus2 import SMBus

# endregion

# region Configuration Constants
I2C_BUS = 1  # /dev/i2c-1
MULTIPLEXER_ADDR = 0x70  # TCA9548A I2C Multiplexer Address
BNO055_ADDR = 0x28  # Verified via i2cdetect

# BNO055 Register Addresses
REG_CHIP_ID = 0x00
REG_OPR_MODE = 0x3D
REG_ACCEL_DATA_X_LSB = 0x28  # <-- Linear Acceleration (Gravity & Noise Filtered)
REG_GYRO_DATA_X_LSB = 0x14

# BNO055 Operating Modes
MODE_CONFIG = 0x00
MODE_NDOF = 0x0C  # Nine Degrees of Freedom (Sensor Fusion Mode)
# endregion

class TCA9548A_Multiplexer:
    """
    <summary>
    A driver class to control the TCA9548A I2C Multiplexer.
    </summary>
    """

    # region Initialization
    def __init__(self, bus, address=MULTIPLEXER_ADDR):
        """
        <summary>
        Initializes the multiplexer using a shared I2C bus.
        </summary>
        <param name="bus">The shared SMBus instance.</param>
        <param name="address">The I2C address of the multiplexer.</param>
        """
        self.bus = bus
        self.address = address

    # endregion

    # region Public API
    def select_channel(self, channel):
        """
        <summary>
        Switches the multiplexer to the specified channel (0-7).
        Safely catches hardware disconnection errors.
        </summary>
        <param name="channel">The channel number to activate.</param>
        <returns>True if successful, False if the multiplexer is unreachable.</returns>
        """
        if channel < 0 or channel > 7:
            raise ValueError("Channel must be between 0 and 7.")

        try:
            # Write a single byte with the bit set for the desired channel
            self.bus.write_byte(self.address, 1 << channel)
            time.sleep(0.001)  # Brief pause to allow hardware routing to switch
            return True
        except OSError:
            print(f"Warning: Multiplexer unresponsive on channel {channel}. Check wiring.")
            return False
    # endregion


class SEN0253_IMU:
    """
    <summary>
    A native Linux I2C driver class specifically for the BNO055 IMU chip
    found on the SEN0253 module.
    </summary>
    """

    # region Initialization
    def __init__(self, bus, address=BNO055_ADDR):
        """
        <summary>
        Initializes the BNO055 sensor, establishes the I2C connection via the shared bus,
        and sets the operating mode.
        </summary>
        <param name="bus">The shared SMBus instance.</param>
        <param name="address">The I2C address of the sensor (0x28).</param>
        """
        self.address = address
        self.bus = bus  # Store the shared bus reference
        self._initialize_sensor()

    def _initialize_sensor(self):
        """
        <summary>
        Configures the BNO055 into NDOF (Sensor Fusion) mode.
        </summary>
        """
        try:
            # Check Chip ID (BNO055 should return 0xA0)
            chip_id = self.bus.read_byte_data(self.address, REG_CHIP_ID)
            print(f"Connected to BNO055. Chip ID: {hex(chip_id)}")

            # Set to Config Mode first (required before changing to other modes)
            self.bus.write_byte_data(self.address, REG_OPR_MODE, MODE_CONFIG)
            time.sleep(0.05)

            # Set to NDOF (Nine Degrees of Freedom) mode to activate accel and gyro
            self.bus.write_byte_data(self.address, REG_OPR_MODE, MODE_NDOF)
            time.sleep(0.05)  # The BNO055 takes about 7ms to switch modes

            print("Sensor initialized successfully in NDOF mode.")

        except PermissionError:
            print("Permission denied: Ensure your user is in the 'i2c' group or run via sudo.")
        except Exception as e:
            print(f"Warning: Initialization failed. Sensor may be disconnected. ({e})")

    # endregion

    # region Data Processing
    def _read_raw_data(self, reg_address):
        """
        <summary>
        Reads 6 bytes of sequential data from a specified starting register
        and converts them into signed 16-bit integers for the X, Y, and Z axes.
        </summary>
        <param name="reg_address">The starting register address.</param>
        <returns>A dictionary containing the X, Y, and Z axis values.</returns>
        """
        if self.bus is None:
            return {'x': 0, 'y': 0, 'z': 0}

        try:
            # Read 6 sequential bytes (X_LSB, X_MSB, Y_LSB, Y_MSB, Z_LSB, Z_MSB)
            data = self.bus.read_i2c_block_data(self.address, reg_address, 6)

            # Convert two's complement 16-bit values (Little Endian for BNO055)
            x = self._twos_comp((data[1] << 8) | data[0], 16)
            y = self._twos_comp((data[3] << 8) | data[2], 16)
            z = self._twos_comp((data[5] << 8) | data[4], 16)

            return {'x': x, 'y': y, 'z': z}
        except Exception:
            # Silently return zeros so the stream doesn't crash on mid-stream disconnects
            return {'x': 0, 'y': 0, 'z': 0}

    def _twos_comp(self, val, bits):
        """
        <summary>
        Calculates the two's complement of a given integer.
        </summary>
        <param name="val">The raw integer value.</param>
        <param name="bits">The bit-width of the value.</param>
        <returns>The signed integer value.</returns>
        """
        if (val & (1 << (bits - 1))) != 0:
            val = val - (1 << bits)
        return val

    # endregion

    # region Public API
    def get_accel_data(self):
        """
        <summary>
        Retrieves the current raw accelerometer data.
        </summary>
        <returns>A dictionary with 'x', 'y', and 'z' acceleration values.</returns>
        """
        return self._read_raw_data(REG_ACCEL_DATA_X_LSB)

    def get_gyro_data(self):
        """
        <summary>
        Retrieves the current raw gyroscope data.
        </summary>
        <returns>A dictionary with 'x', 'y', and 'z' rotational values.</returns>
        """
        return self._read_raw_data(REG_GYRO_DATA_X_LSB)
    # endregion


# region Main Execution
if __name__ == "__main__":
    """
    <summary>
    Main entry point. Reads BNO055 data from multiple sensors via multiplexer 
    and streams it over the network via UDP. Continues streaming zeros if 
    sensors are disconnected.
    </summary>
    """
    # Network Configuration
    UDP_IP = "10.42.0.1"
    UDP_PORT = 5005
    print(f"Targeting IP: {UDP_IP}:{UDP_PORT}")

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Initialize the shared I2C bus ONCE
    bus = SMBus(I2C_BUS)

    # Initialize the Multiplexer
    mux = TCA9548A_Multiplexer(bus)

    try:
        # Route to Channel 0 and boot up the first sensor
        print("Initializing Sensor 1 on Multiplexer Channel 0...")
        mux.select_channel(0)
        sensor_0 = SEN0253_IMU(bus)

        # Route to Channel 1 and boot up the second sensor
        print("Initializing Sensor 2 on Multiplexer Channel 1...")
        mux.select_channel(1)
        sensor_1 = SEN0253_IMU(bus)

        print(f"Streaming dual sensor data to Port {UDP_PORT}... Press Ctrl+C to stop.")

        while True:
            # 1. Read Data from the Left Glove (Channel 0)
            if mux.select_channel(0):
                accel_0 = sensor_0.get_accel_data()
                gyro_0 = sensor_0.get_gyro_data()
            else:
                accel_0 = gyro_0 = {'x': 0, 'y': 0, 'z': 0}

            # 2. Read Data from the Right Glove (Channel 1)
            if mux.select_channel(1):
                accel_1 = sensor_1.get_accel_data()
                gyro_1 = sensor_1.get_gyro_data()
            else:
                accel_1 = gyro_1 = {'x': 0, 'y': 0, 'z': 0}

            # 3. Package both gloves into a single JSON dictionary
            payload = {
                "sensor_0": {
                    "accel": accel_0,
                    "gyro": gyro_0
                },
                "sensor_1": {
                    "accel": accel_1,
                    "gyro": gyro_1
                }
            }

            # 4. Send the combined JSON packet over the network
            sock.sendto(json.dumps(payload).encode('utf-8'), (UDP_IP, UDP_PORT))

            time.sleep(0.05)  # 20Hz update rate

    except KeyboardInterrupt:
        print("\nStreaming stopped.")
    finally:
        # Safely close the shared bus and socket
        bus.close()
        sock.close()
# endregion