const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws/events';

// State
let slots = [];
let entryTimerInterval;
let exitTimerInterval;

// DOM Elements
const slotGrid = document.getElementById('slot-grid');
const logFeed = document.getElementById('log-feed');
const freeCountEl = document.getElementById('free-count');
const totalCountEl = document.getElementById('total-count');

// --- INIT ---
async function init() {
    await fetchSlots();
    refreshEntryQR();
    refreshExitQR();
    connectWebSocket();

    // Auto-refresh QRs before they expire (every 80s for 90s TTL)
    setInterval(refreshEntryQR, 80000);
    setInterval(refreshExitQR, 80000);
}

// --- API CALLS ---
async function fetchSlots() {
    try {
        const res = await fetch(`${API_BASE}/api/slots`);
        const data = await res.json();
        slots = data.slots;
        renderSlots(data);
    } catch (e) {
        log(`Error fetching slots: ${e.message}`, 'error');
    }
}

async function refreshEntryQR() {
    try {
        const res = await fetch(`${API_BASE}/api/qr/entry`);
        const data = await res.json();
        // URL for Native Camera Scan
        const host = window.location.host;
        const url = `http://${host}/pwa/claim.html?t=${data.token}&type=entry`;

        renderQR('entry-qr', url);
        startTimer('entry-timer', new Date(data.expires_at));
    } catch (e) {
        console.error(e);
    }
}

async function refreshExitQR() {
    try {
        const res = await fetch(`${API_BASE}/api/qr/exit`);
        const data = await res.json();
        renderQR('exit-qr', JSON.stringify({ t: data.token, type: 'exit' }));
        startTimer('exit-timer', new Date(data.expires_at));
    } catch (e) {
        console.error(e);
    }
}

async function resetSlots() {
    if (!confirm("Reset all slots to FREE?")) return;
    await fetch(`${API_BASE}/api/admin/set_slots`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ total_slots: 4 })
    });
    fetchSlots();
    log("Admin reset all slots");
}

async function controlGate(cmd) {
    try {
        await fetch(`${API_BASE}/api/admin/gate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd })
        });
        log(`Manual Gate Command: ${cmd.toUpperCase()}`);
    } catch (e) {
        log(`Error sending command: ${e.message}`, 'error');
    }
}

// --- RENDER ---
function renderSlots(data) {
    freeCountEl.textContent = data.free;
    totalCountEl.textContent = data.total;

    slotGrid.innerHTML = slots.map(slot => `
        <div class="slot ${slot.status} p-6 rounded-lg text-center border-2 border-gray-700">
            <div class="text-4xl font-bold mb-2">${slot.id}</div>
            <div class="uppercase text-sm font-tracking-wider opacity-75">${slot.status}</div>
            ${slot.session_id ? `<div class="text-xs mt-2 truncate">${slot.session_id}</div>` : ''}
        </div>
    `).join('');
}

function renderQR(elementId, text) {
    const el = document.getElementById(elementId);
    el.innerHTML = '';
    new QRCode(el, {
        text: text,
        width: 160,
        height: 160
    });
}

function startTimer(elementId, expiry) {
    const el = document.getElementById(elementId);
    // Simple countdown visual
    el.textContent = `Expires: ${expiry.toLocaleTimeString()}`;
}

function log(msg, type = 'info') {
    const div = document.createElement('div');
    const time = new Date().toLocaleTimeString();
    div.className = `p-2 border-l-2 ${type === 'error' ? 'border-red-500 bg-red-900/20' : 'border-blue-500 bg-blue-900/20'}`;
    div.innerHTML = `<span class="opacity-50">[${time}]</span> ${msg}`;
    logFeed.prepend(div);
}

// --- WEBSOCKET ---
function connectWebSocket() {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => log("Connected to Backend Events");
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleEvent(msg);
    };
    ws.onclose = () => {
        log("Disconnected. Reconnecting...", 'error');
        setTimeout(connectWebSocket, 3000);
    };
}

function handleEvent(msg) {
    log(`Event: ${msg.type} ${JSON.stringify(msg)}`);

    if (['slot_reserved', 'slot_occupied', 'slot_freed'].includes(msg.type)) {
        fetchSlots();
    }
}

init();
