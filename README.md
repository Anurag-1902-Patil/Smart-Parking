# Smart Parking System Prototype

A full-stack smart parking system with Arduino gate control, Python FastAPI backend, Operator Dashboard, and Mobile Web Access (Native QR).

## 📂 Project Structure

- `arduino_gate/`: Arduino sketch for the servo gate and IR sensors.
- `backend/`: Python FastAPI application managing slots, sessions, and hardware.
- `operator_ui/`: Web dashboard for the parking operator.
- `pwa_app/`: Mobile web pages for drivers (Claim/Exit).

## 🛠️ Hardware Setup (Arduino Uno)

- **Pin 2**: Entry IR Sensor (Input Pullup)
- **Pin 3**: Exit IR Sensor (Input Pullup)
- **Pin 4**: Servo Motor (Gate)
- **USB**: Connect to PC (Check COM port in `backend/main.py`)

> **Note**: Sensors are expected to be **Active LOW** (LOW = Object Detected).

## 🚀 Getting Started

### 1. Arduino
1. Open `arduino_gate/arduino_parking.ino` in Arduino IDE.
2. Select your Board and Port.
3. Upload the sketch.
4. **Close the Serial Monitor** (the backend needs the port).

### 2. Backend
1. Open a terminal in the project root.
2. Create virtual environment (if not done):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. **Edit Configuration**:
   - Open `backend/main.py`.
   - Update `SERIAL_PORT = "COM3"` (or your port).
5. Run the server:
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

### 3. Operator UI (Laptop)
1. Find your Laptop's IP (run `ipconfig`).
2. Open `http://<YOUR_IP>:8000/operator` (e.g., `http://192.168.1.5:8000/operator`).
3. **Do not use localhost**, or the QR codes won't work for mobile.

### 4. Driver Flow (Mobile)
1. **Drive Up**: Place hand/car in front of Entry Sensor.
2. **Scan QR**: Use phone camera to scan the QR on the Laptop screen.
3. **Claim**: Tap the link -> "Access Granted" -> "I'M PARKED".
   - *If it says "Please drive up...", ensure the sensor is blocked and try again.*

## 🧪 Sensor Logic
- The system enforces that a car must be present at the gate to claim a ticket.
- **Entry**: `sensor_state['entry']` must be `True` (Blocked).
- **Exit**: `sensor_state['exit']` must be `True` (Blocked).
- The Backend queries the Arduino for initial sensor state (`CMD:SENSORS`) on startup.

## ⚠️ Troubleshooting

- **"Please drive up..."**: Sensor is not blocked. Check wiring or put hand closer.
- **"Gate Offline"**: Check USB connection.
- **Mobile Hangs**: Ensure Phone and Laptop are on the same Wi-Fi.
