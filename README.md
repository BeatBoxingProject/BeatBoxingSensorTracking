# 🥊 BeatBoxing Sensor Tracking

The system utilizes a **Raspberry Pi Zero 2W** mounted on the player or equipment, which reads data from two **BNO055 IMU sensors** (one for each glove) via an I2C multiplexer. This telemetry is packaged into a JSON payload and streamed wirelessly via UDP to the host machine running Unity.

## ✨ Key Features

* **Dual IMU Tracking:** Tracks linear acceleration and gyroscope data for two separate hands simultaneously.
* **I2C Multiplexing:** Utilizes a TCA9548A multiplexer to bypass I2C address conflicts, allowing two identical BNO055 sensors to operate on the same bus.
* **Sensor Fusion:** Runs the BNO055 in NDOF (Nine Degrees of Freedom) mode to leverage onboard sensor fusion, providing clean, gravity-filtered linear acceleration.
* **Low-Latency UDP Streaming:** Packages data into lightweight JSON dictionaries sent over the network at ~20Hz to ensure the game engine registers impacts instantly.
* **Live Visualizer:** Includes a Matplotlib-based real-time dashboard to monitor and debug the telemetry streams locally on the host PC.

## 🛠️ Hardware Setup

1. **Microcontroller:** Raspberry Pi Zero 2W (Configured for headless WiFi operation).
2. **Sensors:** 2x **SEN0253 (BNO055)** IMU modules (Mounted securely inside or on the boxing gloves).
3. **Multiplexer:** 1x **TCA9548A** I2C Multiplexer (Required because both IMUs share the `0x28` I2C address).
4. **Wiring:**
    * Pi I2C (SDA/SCL) $\rightarrow$ Multiplexer Main I2C
    * Multiplexer Channel 0 $\rightarrow$ Left Glove IMU
    * Multiplexer Channel 1 $\rightarrow$ Right Glove IMU


5. **Network:** Both the Pi and the Host PC must be on the same local network. The scripts are currently configured to target the IP `10.42.0.1`.

## 📂 Project Structure

| Location | Description |
| --- | --- |
| `sensor-stream.py` (Pi Version) | **The Transmitter.** Runs on the Raspberry Pi Zero 2W. Handles I2C communication, multiplexer switching, and UDP broadcasting. |
| `sensor-stream.py` (PC Version) | **The Visualizer.** Runs on the Host PC. Listens for the UDP packets and plots the live $X, Y, Z$ acceleration data for both gloves. |

## ⚙️ Installation & Requirements

### On the Raspberry Pi Zero 2W

1. Ensure I2C is enabled on your Raspberry Pi (`sudo raspi-config` > Interfacing Options > I2C > Enable).
2. Ensure your user is part of the `i2c` group.
3. Install the required Python libraries:

```bash
pip install smbus2

```

### On the Host PC (Visualizer)

If you want to run the debugging visualizer on your main machine, install the required plotting libraries:

```bash
pip install matplotlib

```

## ⚡ Usage Workflow

### 1. Start the Telemetry Stream (Raspberry Pi)

SSH into your Raspberry Pi and execute the transmitter script. This will initialize the sensors and begin blasting UDP packets to the host.

```bash
python core/sensor-stream.py

```

* **Expected Output:** The console will confirm connection to the BNO055 chips (reading Chip ID `0xA0`) and confirm initialization in NDOF mode.

### 2. Verify Data with the Visualizer (Host PC)

Run the visualizer script on the machine receiving the data to ensure the networking is correct and the sensors are responding to physical punches.

```bash
python core/sensor-stream.py

```

* **Goal:** You should see a live scrolling graph with 6 lines (X, Y, Z for both Sensor 0 and Sensor 1). When you punch, you should see sharp spikes in the acceleration data.

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

* **I2C Permission Denied:** If the Pi throws a permission error, ensure you are running the script with `sudo` or have correctly added your user to the I2C group.
* **No Data in Visualizer/Unity:** Verify the IP address in the Raspberry Pi script. It is currently hardcoded to `10.42.0.1`. If your host PC has a different local IP address, you must update the `UDP_IP` variable.
* **Sensor Initialization Fails:** Double-check the wiring to the TCA9548A multiplexer. You can run `i2cdetect -y 1` on the Pi to verify that the multiplexer (usually `0x70`) is visible on the bus.