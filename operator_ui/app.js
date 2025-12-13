const API_BASE = window.location.protocol + '//' + window.location.hostname + ':8000';
const WS_URL = 'ws://' + window.location.hostname + ':8000/ws/events';

// State
let slots = [];
let entryTimerInterval;
let exitTimerInterval;

// DOM Elements
const slotGrid = document.getElementById('slot-grid');
const freeCountEl = document.getElementById('free-count');
const totalCountEl = document.getElementById('total-count');
const occupancyBar = document.getElementById('occupancy-bar');
const connectionStatus = document.getElementById('connection-status');

const gateIcon = document.getElementById('gate-icon');
const gateStatusText = document.getElementById('gate-status-text');

const sensorEntry = document.getElementById('sensor-entry');
const sensorExit = document.getElementById('sensor-exit');

// --- INIT ---
async function init() {
    await fetchSlots();
    refreshEntryQR();
    refreshEntryQR();
    connectWebSocket();

    // Auto-refresh QRs before they expire (every 80s for 90s TTL)
    setInterval(refreshEntryQR, 80000);
}

// --- API CALLS ---
async function fetchSlots() {
    try {
        const res = await fetch(`${API_BASE}/api/slots`);
        const data = await res.json();
        slots = data.slots;
        renderSlots(data);
    } catch (e) {
        console.error("Error fetching slots:", e);
    }
}

async function refreshEntryQR() {
    try {
        const res = await fetch(`${API_BASE}/api/qr/entry`);
        const data = await res.json();
        const host = window.location.host;
        const url = `http://${host}/pwa/claim.html?t=${data.token}&type=entry`;
        renderQR('entry-qr', url);
    } catch (e) { console.error(e); }
}


async function resetSlots() {
    if (!confirm("Reset all slots to FREE?")) return;
    await fetch(`${API_BASE}/api/admin/set_slots`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ total_slots: 4 })
    });
    fetchSlots();
}

async function controlGate(cmd) {
    try {
        await fetch(`${API_BASE}/api/admin/gate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd })
        });
    } catch (e) { console.error(e); }
}

// --- RENDER ---
function renderSlots(data) {
    freeCountEl.textContent = data.free;
    totalCountEl.textContent = data.total;

    // Update Progress Bar
    const occupied = data.total - data.free;
    const percentage = (occupied / data.total) * 100;
    occupancyBar.style.width = `${percentage}%`;

    // Color shift based on occupancy
    if (percentage < 50) occupancyBar.className = "h-4 rounded-full transition-all duration-500 bg-emerald-500";
    else if (percentage < 80) occupancyBar.className = "h-4 rounded-full transition-all duration-500 bg-yellow-500";
    else occupancyBar.className = "h-4 rounded-full transition-all duration-500 bg-rose-500";

    slotGrid.innerHTML = slots.map(slot => {
        let statusColor = "bg-emerald-500/20 border-emerald-500/50 text-emerald-400";
        if (slot.status === 'occupied') statusColor = "bg-rose-500/20 border-rose-500/50 text-rose-400";
        if (slot.status === 'reserved') statusColor = "bg-yellow-500/20 border-yellow-500/50 text-yellow-400";

        return `
        <div class="slot-card ${statusColor} border rounded-xl p-4 flex flex-col items-center justify-center min-h-[100px]">
            <div class="text-3xl font-bold mb-1">${slot.id}</div>
            <div class="text-xs font-bold uppercase tracking-wider opacity-80">${slot.status}</div>
        </div>
        `;
    }).join('');
}

function renderQR(elementId, text) {
    const el = document.getElementById(elementId);
    el.innerHTML = '';
    new QRCode(el, { text: text, width: 128, height: 128 });
}

// --- UI UPDATES ---
function updateGateStatus(isOpen) {
    if (isOpen) {
        gateIcon.textContent = "🔓";
        gateStatusText.textContent = "OPEN";
        gateStatusText.className = "text-2xl font-bold text-emerald-400";
    } else {
        gateIcon.textContent = "🚧";
        gateStatusText.textContent = "CLOSED";
        gateStatusText.className = "text-2xl font-bold text-rose-400";
    }
}

function updateSensorStatus(type, isBlocked) {
    const el = type === 'entry' ? sensorEntry : sensorExit;
    if (isBlocked) {
        el.innerHTML = `<span class="w-3 h-3 rounded-full bg-rose-500 animate-pulse"></span> <span class="text-rose-400 font-bold">BLOCKED</span>`;
    } else {
        el.innerHTML = `<span class="w-3 h-3 rounded-full bg-emerald-500"></span> <span class="text-emerald-400">Clear</span>`;
    }
}

function setConnectionStatus(connected) {
    if (connected) {
        connectionStatus.className = "flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-900/30 text-emerald-400 text-xs font-medium uppercase tracking-wider";
        connectionStatus.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500"></span> Live`;
    } else {
        connectionStatus.className = "flex items-center gap-2 px-3 py-1 rounded-full bg-red-900/30 text-red-400 text-xs font-medium uppercase tracking-wider";
        connectionStatus.innerHTML = `<span class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span> Disconnected`;
    }
}

// --- WEBSOCKET ---
function connectWebSocket() {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        setConnectionStatus(true);
        console.log("Connected to Backend Events");
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleEvent(msg);
    };

    ws.onclose = () => {
        setConnectionStatus(false);
        setTimeout(connectWebSocket, 3000);
    };
}

function handleEvent(msg) {
    console.log("Event:", msg);

    if (['slot_reserved', 'slot_occupied', 'slot_freed'].includes(msg.type)) {
        fetchSlots();
    }
    else if (msg.type === 'gate_opened') updateGateStatus(true);
    else if (msg.type === 'gate_closed') updateGateStatus(false);
    else if (msg.type === 'beam_entry') updateSensorStatus('entry', msg.state === 'blocked');
    else if (msg.type === 'beam_exit') updateSensorStatus('exit', msg.state === 'blocked');
}

init();
