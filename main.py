import socket
import json
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
import time
import threading

# Configuration
UDP_IP = "0.0.0.0"
UDP_PORT = 50123
BUFFER_SIZE = 600  # Store data for approx. 1 minute at 60 FPS
UPDATE_INTERVAL = 20  # milliseconds

class iRacingTelemetry:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((UDP_IP, UDP_PORT))
        
        # Data buffer arrays
        self.timestamps = []
        self.throttle_values = []
        self.brake_values = []
        
        # Game and car detection flags
        self.game_running = False
        self.car_detected = False
        
    def update_data(self):
        """Capture UDP packets and parse telemetry data"""
        while True:  # Infinite loop for background processing
            try:
                data, addr = self.sock.recvfrom(65535)
                packet_id = int(data[0])
                
                # Detect game running when we receive any UDP packet
                if not self.game_running:
                    self.game_running = True
                
                # Skip non-primary packets
                if packet_id == 2:  # Primary UDP packet ID changes per race (usually starts at packet ID 2)
                    json_data = json.loads(data[4:].decode('utf-8'))
                    
                    # Check if CarTelemetry exists and has data
                    if 'CarTelemetry' in json_data:
                        self.car_detected = True
                        
                        # Get your player data index
                        for car_index, car_data in enumerate(json_data['Sessions'][0]['Participants']):
                            if car_data['DriverId'] == json_data['DriverId']:
                                self._process_telemetry(car_index, json_data)
            except Exception as e:
                print(f"Data error: {e}")
                time.sleep(0.1)  # Prevent blocking

    def _process_telemetry(self, car_index, json_data):
        """Extract and store throttle/brake data"""
        # Get latest timestamp
        current_time = time.time()
        
        # Store player car telemetry data 
        throttle_percent = json_data['CarTelemetry'][car_index]['Throttle'] * 100
        brake_percent = json_data['CarTelemetry'][car_index]['Brake'] * 100
        
        # Limit buffer size
        if len(self.timestamps) > BUFFER_SIZE:
            self.timestamps = self.timestamps[-BUFFER_SIZE:]
            self.throttle_values = self.throttle_values[-BUFFER_SIZE:]
            self.brake_values = self.brake_values[-BUFFER_SIZE:]
            
        # Store data
        self.timestamps.append(current_time)
        self.throttle_values.append(throttle_percent)
        self.brake_values.append(brake_percent)

def main(tel):
    print("Initializing plot...")
    
    # Setup visualization plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Create empty line objects
    throttle_line, = ax.plot([], [], 'g-', label='Throttle')
    brake_line, = ax.plot([], [], 'r-', label='Brake (Reverse)')
    
    # Format plot
    ax.set_xlabel("Time (s)")
    if tel.game_running and tel.car_detected:
        plt.title("Trail Braking Analysis")
    
    # Initial empty plot setup
    ax.set_ylim(-100, 100)  # Invert brake display
    ax.legend(loc='upper right')
    
    def init():
        """Initialize empty plot lines"""
        throttle_line.set_data([], [])
        brake_line.set_data([], [])
        
        # Set initial title based on detection status
        if tel.game_running and tel.car_detected:
            plt.title("Trail Braking Analysis")
        elif not tel.game_running:
            plt.title("Waiting for iRacing connection...")
        else:  # car detected but game might not be running
            plt.title("Player Car Detected")
            
        return throttle_line, brake_line
    
    def update_plot(frame):
        """Update plot animation"""
        # Only update if we have data
        if tel.timestamps:
            # Calculate time relative to latest data point
            rel_time = np.array([t - tel.timestamps[-1] for t in tel.timestamps])
            
            throttle_line.set_data(rel_time, tel.throttle_values)
            # Invert brake pressure for clearer visualization of release
            brake_line.set_data(rel_time, [-val for val in tel.brake_values])
            
            # Update title if needed
            ax.set_title(f"Trail Braking Analysis - {len(tel.timestamps)} points")
            
        fig.canvas.draw_idle()  # Ensure plot is updated
        return throttle_line, brake_line
    
    try:
        ani = FuncAnimation(fig, update_plot, init_func=init,
                          blit=True, interval=UPDATE_INTERVAL)
        
        # Show plot after animation is created
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Error in main: {e}")
    
if __name__ == "__main__":
    # Initialize telemetry handler
    tel = iRacingTelemetry()

    # Start background UDP thread
    udp_thread = threading.Thread(target=tel.update_data, daemon=True)
    
    # Initialize data arrays (fix for empty array on first run)
    tel.timestamps = [0] * BUFFER_SIZE
    tel.throttle_values = [0] * BUFFER_SIZE
    tel.brake_values = [0] * BUFFER_SIZE
    
    # Start thread and main program
    udp_thread.start()
    
    try:
        print("Starting main function...")
        main(tel)
        
        # Keep the program running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
