import serial
import threading
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SerialBridge")

class SerialBridge:
    def __init__(self, port="COM3", baud=9600):
        self.port = port
        self.baud = baud
        self.ser = None
        self.running = False
        self.event_callback = None
        self.sensor_response_event = threading.Event()
        self.last_sensor_snapshot = None
        self.lock = threading.Lock()

    def start(self, callback):
        self.event_callback = callback
        self.running = True
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _connect(self):
        while self.running:
            try:
                self.ser = serial.Serial(self.port, self.baud, timeout=1)
                logger.info(f"Connected to {self.port}")
                return
            except serial.SerialException:
                logger.warning(f"Failed to connect to {self.port}. Retrying in 2s...")
                time.sleep(2)

    def _read_loop(self):
        self._connect()
        while self.running:
            if not self.ser or not self.ser.is_open:
                self._connect()
                continue
            
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        logger.info(f"RX: {line}")
                        
                        # Intercept INFO:SENSORS for synchronous query
                        if line.startswith("INFO:SENSORS:"):
                            try:
                                # Format: INFO:SENSORS:ENTRY:LOW:EXIT:HIGH
                                parts = line.split(":")
                                self.last_sensor_snapshot = {
                                    "entry": parts[3] == "LOW",
                                    "exit": parts[5] == "LOW"
                                }
                                self.sensor_response_event.set()
                            except:
                                logger.error("Failed to parse sensor snapshot")

                        if self.event_callback:
                            self.event_callback(line)
            except Exception as e:
                logger.error(f"Serial read error: {e}")
                if self.ser:
                    self.ser.close()

    def send_command(self, cmd):
        with self.lock:
            if self.ser and self.ser.is_open:
                try:
                    full_cmd = f"{cmd}\n"
                    self.ser.write(full_cmd.encode('utf-8'))
                    logger.info(f"TX: {cmd}")
                    return True
                except Exception as e:
                    logger.error(f"Serial write error: {e}")
                    return False
            else:
                logger.warning("Serial not connected, cannot send command")
                return False

    def get_sensor_snapshot(self, timeout=1.0):
        """Synchronously query Arduino for current sensor state."""
        self.sensor_response_event.clear()
        if not self.send_command("CMD:SENSORS"):
            return None
        
        if self.sensor_response_event.wait(timeout):
            return self.last_sensor_snapshot
        return None

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()
