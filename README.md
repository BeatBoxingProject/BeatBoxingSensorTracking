# 📡 BeatBoxing Sensor Tracking

The system utilizes a **Raspberry Pi Zero 2W** mounted on the player or equipment, which reads data from two **BNO055 IMU sensors** (one for each glove) via an I2C multiplexer, and **Piezoelectric sensors** via an **ADS1263 High-Precision ADC** over SPI. This telemetry is packaged into a JSON payload and streamed wirelessly via UDP to the host machine running Unity.

## ✨ Key Features

* **Dual IMU Tracking:** Tracks linear acceleration and gyroscope data for two separate hands simultaneously.
* **I2C Multiplexing:** Utilizes a TCA9548A multiplexer to bypass I2C address conflicts, allowing two identical BNO055 sensors to operate on the same bus.
* **Piezo Impact Detection:** High-precision, high-speed analog readings from piezo sensors using an ADS1263 ADC over SPI to detect exact punch impacts.
* **Sensor Fusion:** Runs the BNO055 in NDOF (Nine Degrees of Freedom) mode to leverage onboard sensor fusion, providing clean, gravity-filtered linear acceleration.
* **Low-Latency UDP Streaming:** Packages data into lightweight JSON dictionaries sent over the network at ~20Hz to ensure the game engine registers impacts instantly.
* **Live Visualizer:** Includes a Matplotlib-based real-time dashboard to monitor and debug the telemetry streams locally on the host PC.

## 🛠️ Hardware Setup

1. **Microcontroller:** Raspberry Pi Zero 2W (Configured for headless WiFi operation).
2. **Sensors:** 
   * 2x **SEN0253 (BNO055)** IMU modules (Mounted securely inside or on the boxing gloves).
   * **Piezoelectric Sensors** (For analog impact detection).
3. **Multiplexer & ADC:** 
   * 1x **TCA9548A** I2C Multiplexer (Required because both IMUs share the `0x28` I2C address).
   * 1x **ADS1263** 32-bit ADC module (For reading the analog piezo signals).
4. **Wiring:**
   * Pi I2C (SDA/SCL) $\rightarrow$ Multiplexer Main I2C
   * Multiplexer Channel 0 $\rightarrow$ Left Glove IMU
   * Multiplexer Channel 1 $\rightarrow$ Right Glove IMU
   * Pi SPI (MOSI/MISO/SCLK/CE0) $\rightarrow$ ADS1263 ADC
   * ADS1263 Analog Inputs $\rightarrow$ Piezo Sensors
5. **Network:** Both the Pi and the Host PC must be on the same local network. The scripts are currently configured to target the IP `10.42.0.1`.

## 📂 Project Structure

| Location | Description |
| --- | --- |
| `core/sensor-stream.py` (Pi) | **The Transmitter.** Runs on the Raspberry Pi Zero 2W. Handles I2C communication, multiplexer switching, and UDP broadcasting. |
| `core/visualizer.py` (PC) | **The Visualizer.** Runs on the Host PC. Listens for the UDP packets and plots the live $X, Y, Z$ acceleration data for both gloves. |
| `core/piezo/main.py` (Pi) | **Piezo ADC Tester.** Tests and reads analog values from the piezo sensors via the ADS1263 module over SPI. |

## ⚙️ Installation & Requirements

### On the Raspberry Pi Zero 2W

#### 1. Hardware Interfaces & System Dependencies
Enable the communication buses (I2C for IMUs, SPI for ADC/Piezo) and install required native build dependencies (needed for compiling C-extensions like `spidev` and `lgpio` on modern kernels/Python versions):

```bash
# Enable I2C and SPI interfaces
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0

# Add the current user to hardware access groups
sudo usermod -aG i2c,spi,gpio $USER

# Install native build tools, Python headers, and GPIO development libraries
sudo apt update
sudo apt install -y python3-dev python3-lgpio liblgpio-dev swig i2c-tools

```

> **Note:** A reboot is recommended after enabling interfaces or modifying user groups: `sudo reboot`

#### 2. Python Virtual Environment Setup

Activate your project environment and install the required Python packages:

```bash
pip install smbus2 spidev rpi-lgpio

```

*(Note: `rpi-lgpio` provides the `RPi.GPIO` interface compatible with modern Raspberry Pi kernels and Bookworm/Python 3.13+).*

### On the Host PC (Visualizer)

If you want to run the debugging visualizer on your main machine, install the required plotting libraries:

```bash
pip install matplotlib

```

## ⚡ Usage Workflow

### 1. Start the Telemetry Stream (Raspberry Pi)

SSH into your Raspberry Pi, activate your virtual environment, and run the transmitter script:

```bash
python core/sensor-stream.py

```

* **Expected Output:** The console will confirm connection to the BNO055 chips (reading Chip ID `0xA0`) and confirm initialization in NDOF mode.

### 2. Test the Piezo Sensors (Raspberry Pi)

You can run the standalone ADC test script to verify piezo sensor readings:

```bash
python core/piezo/main.py
```

* **Expected Output:** The console will print the voltages read from the ADS1263 analog inputs. Squeezing or striking the piezo should cause a spike in the voltage reading.

### 3. Verify Data with the Visualizer (Host PC)

Run the visualizer script on your host machine to confirm data reception and sensor responsiveness:

```bash
python core/visualizer.py
```

* **Goal:** You should see a live scrolling graph with 6 lines (X, Y, Z for both Sensor 0 and Sensor 1). When you punch, sharp spikes will appear in the acceleration data.

## 🎮 Unity Integration

The Raspberry Pi broadcasts a combined JSON payload via UDP to Port **5005**.

**JSON Format:**

```json
{
  "sensor_0": {
    "accel": {"x": -12, "y": 45, "z": 900},
    "gyro": {"x": 0, "y": -5, "z": 12}
  },
  "sensor_1": {
    "accel": {"x": 8, "y": -30, "z": 850},
    "gyro": {"x": 2, "y": 8, "z": -1}
  }
}

```

**To receive and process this in Unity:**

1. Create a C# script utilizing `System.Net.Sockets.UdpClient`.
2. Listen on Port **5005**.
3. Deserialize the JSON using `JsonUtility` or `Newtonsoft.Json`.

```csharp
// Example Unity C# parsing logic
using Newtonsoft.Json;
using UnityEngine;

[System.Serializable]
public class SensorData {
    public Vector3Data accel;
    public Vector3Data gyro;
}

[System.Serializable]
public class Vector3Data {
    public float x, y, z;
}

[System.Serializable]
public class GloveTelemetry {
    public SensorData sensor_0;
    public SensorData sensor_1;
}

// Inside your UDP receive loop:
// string jsonString = Encoding.UTF8.GetString(receivedBytes);
// GloveTelemetry telemetry = JsonConvert.DeserializeObject<GloveTelemetry>(jsonString);
// float leftPunchForce = telemetry.sensor_0.accel.y; // Example extraction

```

## 🔧 Troubleshooting

* **I2C Permission Denied:** Ensure you have added your user to the `i2c` group (`sudo usermod -aG i2c $USER`) and re-logged or rebooted.
* **No Data in Visualizer/Unity:** Verify the IP address in the Raspberry Pi script (`sensor-stream.py`). It is currently hardcoded to `10.42.0.1`. Update `UDP_IP` to match your host PC's local IP address.
* **Sensor Initialization Fails:** Verify the wiring to the TCA9548A multiplexer. Run `i2cdetect -y 1` on the Pi to check that the multiplexer address (`0x70`) responds on the bus.
* **ModuleNotFoundError / GPIO Errors:** Ensure `rpi-lgpio` is installed instead of legacy `RPi.GPIO` or `Jetson.GPIO`.