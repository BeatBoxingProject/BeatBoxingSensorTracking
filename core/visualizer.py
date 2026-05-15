# region Imports
import socket
import json
import matplotlib

matplotlib.use('TkAgg')  # Force Matplotlib to open a physical window
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

# endregion

# region Configuration
UDP_PORT = 5005
MAX_DATAPOINTS = 100  # How many points to show on the screen at once


# endregion

class SensorVisualizer:
    """
    <summary>
    Listens for UDP JSON packets on the local network and plots the
    accelerometer data for TWO sensors in real-time using Matplotlib.
    </summary>
    """

    # region Initialization
    def __init__(self):
        """
        <summary>
        Initializes the UDP socket and the Matplotlib figure with dual-sensor lines.
        </summary>
        """
        # Set up UDP networking
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Explicitly listen ONLY on the Ethernet IP
        self.sock.bind(("10.42.0.1", UDP_PORT))
        self.sock.setblocking(False)  # Non-blocking so the graph doesn't freeze

        # Set up data storage for Sensor 0 (Channel 0)
        self.s0_x = deque(maxlen=MAX_DATAPOINTS)
        self.s0_y = deque(maxlen=MAX_DATAPOINTS)
        self.s0_z = deque(maxlen=MAX_DATAPOINTS)

        # Set up data storage for Sensor 1 (Channel 1)
        self.s1_x = deque(maxlen=MAX_DATAPOINTS)
        self.s1_y = deque(maxlen=MAX_DATAPOINTS)
        self.s1_z = deque(maxlen=MAX_DATAPOINTS)

        self.time_data = deque(maxlen=MAX_DATAPOINTS)
        self.counter = 0

        # Set up Matplotlib Figure
        self.fig, self.ax = plt.subplots(figsize=(12, 7))
        self.fig.canvas.manager.set_window_title('Safe-Strike: Dual Sensor Telemetry')

        # Sensor 0 Lines (Solid)
        self.line_s0_x, = self.ax.plot([], [], label='S0 Accel X (Red Solid)', color='red', linestyle='-')
        self.line_s0_y, = self.ax.plot([], [], label='S0 Accel Y (Green Solid)', color='green', linestyle='-')
        self.line_s0_z, = self.ax.plot([], [], label='S0 Accel Z (Blue Solid)', color='blue', linestyle='-')

        # Sensor 1 Lines (Dashed)
        self.line_s1_x, = self.ax.plot([], [], label='S1 Accel X (Red Dashed)', color='red', linestyle='--')
        self.line_s1_y, = self.ax.plot([], [], label='S1 Accel Y (Green Dashed)', color='green', linestyle='--')
        self.line_s1_z, = self.ax.plot([], [], label='S1 Accel Z (Blue Dashed)', color='blue', linestyle='--')

        self.ax.set_title("Real-Time Dual BNO055 Linear Acceleration")
        self.ax.set_ylabel("Linear Acceleration")
        self.ax.set_xlabel("Samples")
        # Place legend outside the plot to avoid covering the data lines
        self.ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), borderaxespad=0.)
        self.fig.subplots_adjust(right=0.75)  # Shrink plot to fit legend
        self.ax.grid(True)

    # endregion

    # region Update Logic
    def _read_udp_buffer(self):
        """
        <summary>
        Reads the latest UDP packet from the network buffer.
        </summary>
        <returns>A parsed JSON dictionary, or None if no new data arrived.</returns>
        """
        latest_data = None
        try:
            # Drain the buffer to get only the freshest packet
            while True:
                data, addr = self.sock.recvfrom(2048)  # Increased buffer size for larger dual-sensor payload
                latest_data = data
        except BlockingIOError:
            pass  # Buffer is empty, which is fine

        if latest_data:
            try:
                return json.loads(latest_data.decode('utf-8'))
            except json.JSONDecodeError:
                pass
        return None

    def update_plot(self, frame):
        """
        <summary>
        The animation callback function. Reads UDP and updates all 6 graph lines.
        </summary>
        """
        payload = self._read_udp_buffer()

        if payload and "sensor_0" in payload and "sensor_1" in payload:
            accel_0 = payload["sensor_0"]["accel"]
            accel_1 = payload["sensor_1"]["accel"]

            # Append Sensor 0 data
            self.s0_x.append(accel_0['x'])
            self.s0_y.append(accel_0['y'])
            self.s0_z.append(accel_0['z'])

            # Append Sensor 1 data
            self.s1_x.append(accel_1['x'])
            self.s1_y.append(accel_1['y'])
            self.s1_z.append(accel_1['z'])

            self.time_data.append(self.counter)
            self.counter += 1

            # Update Sensor 0 line data
            self.line_s0_x.set_data(self.time_data, self.s0_x)
            self.line_s0_y.set_data(self.time_data, self.s0_y)
            self.line_s0_z.set_data(self.time_data, self.s0_z)

            # Update Sensor 1 line data
            self.line_s1_x.set_data(self.time_data, self.s1_x)
            self.line_s1_y.set_data(self.time_data, self.s1_y)
            self.line_s1_z.set_data(self.time_data, self.s1_z)

            # Dynamically adjust the X axes to fit the scrolling data
            self.ax.set_xlim(max(0, self.counter - MAX_DATAPOINTS), self.counter)

            # Auto-scale Y axis based on current min/max values of ALL arrays
            if len(self.s0_x) > 0:
                all_values = (
                        list(self.s0_x) + list(self.s0_y) + list(self.s0_z) +
                        list(self.s1_x) + list(self.s1_y) + list(self.s1_z)
                )
                current_min = min(all_values)
                current_max = max(all_values)

                # Add a 10% padding to the top and bottom
                padding = max(abs(current_max), abs(current_min)) * 0.1 + 10
                self.ax.set_ylim(current_min - padding, current_max + padding)

        return (self.line_s0_x, self.line_s0_y, self.line_s0_z,
                self.line_s1_x, self.line_s1_y, self.line_s1_z)

    # endregion

    # region Public API
    def start(self):
        """
        <summary>
        Starts the Matplotlib animation loop.
        </summary>
        """
        print(f"Listening for dual-sensor telemetry on UDP Port {UDP_PORT}...")
        # FuncAnimation handles the loop automatically
        ani = animation.FuncAnimation(
            self.fig, self.update_plot, interval=50, blit=False, cache_frame_data=False
        )
        plt.show()
    # endregion


# region Main Execution
if __name__ == "__main__":
    """
    <summary>
    Main entry point for the local dual-telemetry visualizer.
    </summary>
    """
    visualizer = SensorVisualizer()
    visualizer.start()
# endregion