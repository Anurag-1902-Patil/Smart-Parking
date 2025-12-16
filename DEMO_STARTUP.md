# Smart Parking System - Demo & Presentation Guide

## Quick Start (5 minutes)

### Prerequisites
- **Python 3.10+** installed
- **Arduino** connected on COM3 (with parking gate/sensor firmware)
- **Multiple devices/browsers** for testing (phone, tablet, or second computer)

---

## Step 1: Start the Backend Server

Open **PowerShell** in the project root directory and run:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     SerialBridge:Connected to COM3
INFO:     Application startup complete.
```

### Get Your Machine IP

In another PowerShell window:
```powershell
ipconfig | findstr "IPv4"
```

**Note:** Your IP is likely `10.223.109.253` (adjust based on your network).

---

## Step 2: Access the System

### **Operator Dashboard** (for parking admin/staff)
📍 Open in your **main browser** (desktop/laptop):
```
http://<YOUR_IP>:8000/operator
```
Example: `http://10.223.109.253:8000/operator`

### **User App** (PWA for drivers/visitors)
📍 Open on a **second device** (phone/tablet/second browser):
```
http://<YOUR_IP>:8000/pwa/index.html
```
Example: `http://10.223.109.253:8000/pwa/index.html`

---

## Step 3: Run a Demo Flow

### **Demo Scenario: Two Cars Parking**

#### **Car 1 - Entry**
1. On the **user app** (phone/second device):
   - Tap "Scan to Enter" → open camera
   - Go to the **operator dashboard** → click "Get QR Entry" button
   - Scan the displayed QR code with the user app
   
2. **Backend will**:
   - Check entry IR sensor (car at entry gate)
   - Assign a parking slot (e.g., Slot 1)
   - Open the entry gate (Arduino)
   - User app shows: "Access Granted - Slot 1"

3. **Operator dashboard** shows:
   - Slot 1 status changes to "occupied" (green)
   - Real-time updates via WebSocket

#### **Car 2 - Entry** (Same flow)
- Repeat steps 1-3, user gets Slot 2
- Dashboard now shows Slots 1 & 2 occupied

#### **Car 1 - Exit**
1. On the **user app** (phone/second device with Car 1 session):
   - Tap "Exit Parking" button
   - Drive to the exit gate
   - Tap "Open Exit Gate" button

2. **Backend will**:
   - Check exit IR sensor (car at exit)
   - Open the exit gate (Arduino)
   - User app shows: "Gate Open"
   - User drives out

3. **Exit Confirmation**:
   - When car passes the outer entry sensor, backend marks slot as "free"
   - Operator dashboard updates in real-time

#### **Car 2 - Exit**
- Same process as Car 1

---

## Step 4: Key Features to Demo

| Feature | Where to Show | What to Look For |
|---------|---------------|------------------|
| **Real-time slot status** | Operator Dashboard | Color changes (green=occupied, white=free) |
| **Out-of-order exit** | App (two phones) | Car 2 can exit before Car 1 |
| **QR scanning** | User App | Links to entry flow smoothly |
| **Live gate control** | Backend logs | "Gate command result: True" |
| **WebSocket updates** | Dashboard refresh | No page reload needed |
| **Responsive UI** | Mobile browser | Works on phones/tablets |

---

## Troubleshooting

### **Backend won't start**
```
Error: ModuleNotFoundError: No module named 'fastapi'
```
→ Install dependencies:
```powershell
pip install -r backend/requirements.txt
```

### **Arduino not detected**
```
SerialBridge: Failed to connect to COM3
```
→ Check:
- Arduino is plugged in
- Device Manager shows COM3
- Change `SERIAL_PORT` in `backend/main.py` if needed

### **User app shows "Session Lost"**
→ Clear browser cache/localStorage:
- Press F12 → Application → Local Storage → clear
- Reload page and try again

### **Operator dashboard not updating**
→ Check WebSocket connection:
- Open Browser DevTools (F12) → Console
- Should see WebSocket messages flowing
- If not, check that backend is running

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         Smart Parking System                     │
├──────────────────┬──────────────────┬────────────┤
│  Arduino         │  FastAPI Backend │  Web UIs   │
│  (COM3)          │  (Port 8000)     │  (HTTP)    │
│                  │                  │            │
│ • Sensors        │ • SQLite DB      │ Operator   │
│ • Gate Control   │ • Session Mgmt   │ Dashboard  │
│ • IR Beams       │ • WebSocket      │            │
│                  │ • REST API       │ User PWA   │
│                  │                  │ (Mobile)   │
└──────────────────┴──────────────────┴────────────┘
```

---

## Testing with Multiple Devices

### **Setup:**
1. **Device 1 (Desktop)**: Operator dashboard
2. **Device 2 (Phone A)**: Car 1 user app
3. **Device 3 (Phone B)**: Car 2 user app

### **Network:**
- All devices must be on the same network (same WiFi)
- Use the machine IP (`10.223.109.253`) not `localhost`

---

## After Demo

### **To Stop the Server**
```powershell
# In the terminal running uvicorn, press:
Ctrl + C
```

### **To Check Logs**
```powershell
# List all active sessions
python .\scripts\list_sessions_sqlite.py

# Check slot status
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/slots' | ConvertTo-Json
```

---

## Pro Tips for Presenters

✅ **Do:**
- Test the system 1-2 times before the presentation
- Use multiple devices for a more impressive demo
- Explain the flow: Entry → Parking → Exit
- Show operator dashboard updating in real-time

❌ **Don't:**
- Start without checking Arduino connection first
- Demo on slow/unreliable WiFi
- Forget to mention the 4-slot capacity limit

---

## Questions? Contact

If issues arise during demo, check:
1. `backend/main.py` logs (terminal output)
2. Browser console (F12 on operator/user apps)
3. Arduino serial output (if accessible)

**Good luck with your presentation! 🚗✨**
