import socket
import json
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
import time

# Configuration
UDP_IP = "0.0.0.0"
UDP_PORT = 50123  # Standard iRacing UDP port
BUFFER_SIZE = 600  # Store data for approx. 1 minute at 60 FPS
UPDATE_INTERVAL = 20  # milliseconds

class iRacingTelemetry:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.1)  # Don't block too long
        
        # Data buffer arrays
        self.timestamps = []
        self.throttle_values = []
        
        print(f"Bound to {UDP_IP}:{UDP_PORT}")
        
    def update_data(self):
        """Capture UDP packets and parse telemetry data"""
        try:
            # First, check if we're receiving any data at all
            data = self.sock.recvfrom(65535)
            if not data:
                print("No UDP packets received!")
                return
            
            raw_data, addr = data
            packet_id = int(raw_data[0])
            
            print(f"Received {len(raw_data)} bytes, Packet ID: {packet_id}")
            print("First few bytes:", raw_data[:30].hex())
            
            # Skip non-primary packets
            if packet_id == 2:  # Primary UDP packet ID (let's verify this)
                json_start = raw_data[4:]
                
                try:
                    # Try to parse as JSON (might be invalid binary data)
                    json_data = json.loads(json_start.decode('utf-8'))
                    
                    print("Successfully parsed JSON")
                    # Print extracted driver ID for debugging
                    if 'DriverId' in json_data:
                        print(f"DriverID: {json_data['DriverId']}")
                    
                    # Get your player data index
                    for car_index, car_data in enumerate(json_data.get('Sessions', {}).get(0,{}).get('Participants',[])):
                        if car_data.get('DriverId') == json_data['DriverId']:
                            # Print some sample data for verification
                            print(f"Found player car ({car_index})")
                            if 'Throttle' in car_data.get('CarTelemetry', {}):
                                self._process_telemetry(car_index, json_data)
                            
                except Exception as e:
                    print(f"JSON error: {e}")
                    
        except socket.timeout:
            # Expected if no data is coming
            pass
            
        except Exception as e:
            print(f"Error in update_data: {e}")

    def _process_telemetry(self, car_index, json_data):
        """Extract and store throttle/brake data"""
        # Get latest timestamp
        current_time = time.time()
        
        print(f"Processing car telemetry for index {car_index}")
        
        # Store player car telemetry data 
        try:
            throttle_percent = json_data['CarTelemetry'][car_index]['Throttle'] * 100
            brake_percent = json_data['CarTelemetry'][car_index]['Brake'] * 100
            
            # Limit buffer size
            if len(self.timestamps) > BUFFER_SIZE:
                self.timestamps = self.timestamps[-BUFFER_SIZE:]
                self.throttle_values = self.throttle_values[-BUFFER_SIZE:]
                
            # Store data
            self.timestamps.append(current_time)
            self.throttle_values.append(throttle_percent)
            
        except (KeyError, IndexError) as e:
            print(f"Telemetry data error: {e}")

def main():
    # Initialize telemetry handler
    tel = iRacingTelemetry()
    
    # Setup visualization plot
    fig, ax = plt.subplots(figsize=(12, 6))
    plt.title("Trail Braking Analysis")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("% Input")
    
    # Create line objects
    throttle_line, = ax.plot([], [], 'g-', label='Throttle')
    
    # Format plot
    ax.set_ylim(-10, 100)  # Invert brake display
    ax.legend(loc='upper right')
    
    def init():
        """Initialize empty plot lines"""
        throttle_line.set_data([], [])
        return throttle_line,
    
    def update_plot(frame):
        """Update plot animation"""
        # Check if we have data
        if tel.timestamps:
            rel_time = np.array([t - tel.timestamps[-1] for t in tel.timestamps])
            
            throttle_line.set_data(rel_time, tel.throttle_values[-BUFFER_SIZE:] if len(tel.timestamps) > BUFFER_SIZE else tel.throttle_values)
            
            ax.relim()
            ax.autoscale_view()
        return throttle_line,
    
    # Create animation
    ani = FuncAnimation(fig, update_plot, init_func=init,
                       blit=True, interval=UPDATE_INTERVAL)

    
    # Keep main thread alive
    print("Press Ctrl+C to exit")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    
    plt.show()

if __name__ == "__main__":
    main()
