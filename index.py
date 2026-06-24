import json
import os
import traceback
import threading
from flask import Flask, jsonify, render_template_string, request

try:
    from bot import Bot
    BOT_AVAILABLE = True
except Exception:
    BOT_AVAILABLE = False

app = Flask(__name__)
bot = None
bot_lock = threading.Lock()


def get_bot():
    global bot
    with bot_lock:
        if bot is None and BOT_AVAILABLE:
            bot = Bot()
        return bot


HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bot Monitor - Minecraft Dashboard</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Courier New', monospace;
    background: #0a0a0f;
    color: #c8c8c8;
    min-height: 100vh;
    padding: 20px;
    background-image: radial-gradient(rgba(0,255,0,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    padding: 15px 25px;
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    border: 2px solid #2a2a4a;
    border-radius: 8px;
    margin-bottom: 25px;
    box-shadow: 0 0 20px rgba(0,255,0,0.05);
}

.header h1 {
    font-family: 'Press Start 2P', monospace;
    font-size: 16px;
    color: #55ff55;
    text-shadow: 0 0 10px rgba(85,255,85,0.3);
}

.header h1 span { color: #ffaa00; text-shadow: 0 0 10px rgba(255,170,0,0.3); }

.header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.status-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.status-badge.online { background: rgba(85,255,85,0.15); color: #55ff55; border: 1px solid rgba(85,255,85,0.3); }
.status-badge.offline { background: rgba(255,85,85,0.15); color: #ff5555; border: 1px solid rgba(255,85,85,0.3); }
.status-badge.connecting { background: rgba(255,170,0,0.15); color: #ffaa00; border: 1px solid rgba(255,170,0,0.3); }

.status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    animation: pulse 1.5s ease-in-out infinite;
}
.status-badge.online .status-dot { background: #55ff55; box-shadow: 0 0 6px #55ff55; }
.status-badge.offline .status-dot { background: #ff5555; box-shadow: 0 0 6px #ff5555; }
.status-badge.connecting .status-dot { background: #ffaa00; box-shadow: 0 0 6px #ffaa00; }

@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.btn {
    padding: 8px 16px;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1px solid;
}

.btn-primary {
    background: linear-gradient(180deg, #1a4a1a 0%, #0d2a0d 100%);
    border-color: #2a6a2a;
    color: #55ff55;
}
.btn-primary:hover { background: linear-gradient(180deg, #2a6a2a 0%, #1a4a1a 100%); border-color: #55ff55; box-shadow: 0 0 10px rgba(85,255,85,0.15); }

.btn-danger {
    background: linear-gradient(180deg, #4a1a1a 0%, #2a0d0d 100%);
    border-color: #6a2a2a;
    color: #ff5555;
}
.btn-danger:hover { background: linear-gradient(180deg, #6a2a2a 0%, #4a1a1a 100%); border-color: #ff5555; box-shadow: 0 0 10px rgba(255,85,85,0.15); }

.btn-gold {
    background: linear-gradient(180deg, #4a3a1a 0%, #2a1a0d 100%);
    border-color: #6a5a2a;
    color: #ffaa00;
}
.btn-gold:hover { background: linear-gradient(180deg, #6a5a2a 0%, #4a3a1a 100%); border-color: #ffaa00; box-shadow: 0 0 10px rgba(255,170,0,0.15); }

.btn:active { transform: scale(0.98); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

.card {
    background: linear-gradient(180deg, #12121e 0%, #0d0d18 100%);
    border: 2px solid #2a2a4a;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 0 15px rgba(0,0,0,0.3);
    transition: border-color 0.3s;
}
.card:hover { border-color: #3a3a6a; }

.card h2 {
    font-family: 'Press Start 2P', monospace;
    font-size: 11px;
    color: #ffaa00;
    text-shadow: 0 0 8px rgba(255,170,0,0.2);
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid #2a2a4a;
    letter-spacing: 0.5px;
}

.full-width { grid-column: 1 / -1; }

.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
@media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }

.info-grid { display: grid; grid-template-columns: auto 1fr; gap: 8px 15px; font-size: 13px; }
.info-label { color: #8888aa; font-weight: bold; }
.info-value { color: #e0e0e0; font-family: 'Courier New', monospace; }
.info-value.green { color: #55ff55; }
.info-value.gold { color: #ffaa00; }

.player-list { max-height: 200px; overflow-y: auto; padding-right: 5px; }
.player-list::-webkit-scrollbar { width: 4px; }
.player-list::-webkit-scrollbar-track { background: #1a1a2e; border-radius: 2px; }
.player-list::-webkit-scrollbar-thumb { background: #3a3a6a; border-radius: 2px; }

.player-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 10px; margin-bottom: 4px;
    background: rgba(255,255,255,0.03); border-radius: 4px;
    font-size: 13px; transition: background 0.2s;
}
.player-item:hover { background: rgba(85,255,85,0.05); }
.player-name { color: #55ff55; }
.player-latency { color: #888; font-size: 12px; }
.player-empty { color: #666; font-style: italic; font-size: 13px; padding: 10px 0; }

.chat-box { display: flex; flex-direction: column; height: 250px; }
.chat-messages {
    flex: 1; overflow-y: auto; margin-bottom: 10px;
    padding: 8px; background: rgba(0,0,0,0.3); border-radius: 4px;
    border: 1px solid #1a1a2e; font-size: 13px; line-height: 1.6;
}
.chat-messages::-webkit-scrollbar, .console-log::-webkit-scrollbar, .player-list::-webkit-scrollbar { width: 4px; }
.chat-messages::-webkit-scrollbar-track, .console-log::-webkit-scrollbar-track { background: #1a1a2e; border-radius: 2px; }
.chat-messages::-webkit-scrollbar-thumb, .console-log::-webkit-scrollbar-thumb { background: #3a3a6a; border-radius: 2px; }

.chat-msg { padding: 2px 0; word-break: break-word; }
.chat-msg .time { color: #555; margin-right: 6px; font-size: 11px; }
.chat-msg .sender { margin-right: 6px; }

.chat-input-group { display: flex; gap: 8px; }
.chat-input {
    flex: 1; padding: 8px 12px;
    background: #0a0a14; border: 1px solid #2a2a4a; border-radius: 4px;
    color: #e0e0e0; font-family: 'Courier New', monospace; font-size: 13px;
    outline: none; transition: border-color 0.3s;
}
.chat-input:focus { border-color: #55ff55; box-shadow: 0 0 8px rgba(85,255,85,0.1); }
.chat-input::placeholder { color: #555; }

.console { height: 200px; display: flex; flex-direction: column; }
.console-log {
    flex: 1; overflow-y: auto; padding: 10px;
    background: #050510; border-radius: 4px; border: 1px solid #1a1a2e;
    font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.7;
}
.console-line { color: #55ff55; white-space: pre-wrap; word-break: break-word; }
.console-line.error { color: #ff5555; }
.console-line.chat { color: #55ffff; }
.console-line.auth { color: #ffaa00; }

/* Config panel */
.config-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px 20px;
    font-size: 13px;
}
@media (max-width: 768px) { .config-grid { grid-template-columns: 1fr; } }

.config-group { display: flex; flex-direction: column; gap: 4px; }
.config-group label { color: #8888aa; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
.config-group input, .config-group select {
    padding: 7px 10px;
    background: #0a0a14; border: 1px solid #2a2a4a; border-radius: 4px;
    color: #e0e0e0; font-family: 'Courier New', monospace; font-size: 12px;
    outline: none; transition: border-color 0.3s;
}
.config-group input:focus { border-color: #55ff55; box-shadow: 0 0 8px rgba(85,255,85,0.1); }

.config-divider {
    grid-column: 1 / -1;
    border: none; border-top: 1px solid #2a2a4a; margin: 4px 0;
}

.toggle-group {
    display: flex; align-items: center; gap: 10px;
    grid-column: 1 / -1;
}

.toggle {
    position: relative; width: 44px; height: 24px;
    background: #2a2a4a; border-radius: 12px; cursor: pointer;
    transition: background 0.3s; flex-shrink: 0;
}
.toggle.active { background: #2a6a2a; }
.toggle::after {
    content: ''; position: absolute; top: 2px; left: 2px;
    width: 20px; height: 20px; background: #e0e0e0;
    border-radius: 50%; transition: transform 0.3s;
}
.toggle.active::after { transform: translateX(20px); background: #55ff55; }

.config-actions {
    grid-column: 1 / -1;
    display: flex; gap: 10px; margin-top: 4px;
}
</style>
</head>
<body>

<div class="header">
    <h1>⚡ <span>BOT</span> DASHBOARD</h1>
    <div class="header-actions">
        <div class="status-badge offline" id="statusBadge">
            <span class="status-dot"></span>
            <span id="statusText">Desconectado</span>
        </div>
        <button class="btn btn-primary" id="btnConnect" onclick="connectBot()">▶ CONECTAR</button>
        <button class="btn btn-danger" id="btnDisconnect" onclick="disconnectBot()">■ DESCONECTAR</button>
    </div>
</div>

<div class="card full-width" style="margin-bottom:20px">
    <h2>⚙️ CONFIGURACIÓN</h2>
    <div class="config-grid">
        <div class="config-group">
            <label>IP del servidor</label>
            <input type="text" id="cfgHost" placeholder="ej. testsmc.aternos.me">
        </div>
        <div class="config-group">
            <label>Puerto</label>
            <input type="number" id="cfgPort" placeholder="31230">
        </div>
        <div class="config-group">
            <label>Versión</label>
            <input type="text" id="cfgVersion" placeholder="1.16.5">
        </div>
        <div class="config-group">
            <label>Nombre del Bot</label>
            <input type="text" id="cfgUsername" placeholder="MonitorBot">
        </div>

        <hr class="config-divider">

        <div class="toggle-group">
            <div class="toggle" id="toggleAuth" onclick="this.classList.toggle('active'); updateToggleState();"></div>
            <span style="color:#ffaa00;font-size:12px">Auto-register / Login</span>
        </div>

        <div class="config-group">
            <label>Contraseña</label>
            <input type="text" id="cfgPassword" placeholder="contraseña">
        </div>
        <div class="config-group">
            <label>Delay después de unir (seg)</label>
            <input type="number" id="cfgDelay" placeholder="3">
        </div>
        <div class="config-group">
            <label>Comando /register</label>
            <input type="text" id="cfgRegister" placeholder="/register $password $password">
        </div>
        <div class="config-group">
            <label>Comando /login</label>
            <input type="text" id="cfgLogin" placeholder="/login $password">
        </div>

    </div>
</div>

<div class="grid">
    <div class="card">
        <h2>🌐 SERVIDOR</h2>
        <div class="info-grid">
            <span class="info-label">IP:</span>
            <span class="info-value green" id="serverIp">-</span>
            <span class="info-label">Puerto:</span>
            <span class="info-value gold" id="serverPort">-</span>
            <span class="info-label">Versión:</span>
            <span class="info-value" id="serverVersion">-</span>
            <span class="info-label">Bot:</span>
            <span class="info-value gold" id="botName">-</span>
        </div>
    </div>

    <div class="card">
        <h2>👥 JUGADORES (<span id="playerCount">0</span>)</h2>
        <div class="player-list" id="playerList">
            <div class="player-empty">Esperando jugadores...</div>
        </div>
    </div>
</div>

<div class="grid">
    <div class="card full-width">
        <h2>💬 CHAT</h2>
        <div class="chat-box">
            <div class="chat-messages" id="chatMessages"></div>
            <div class="chat-input-group">
                <input type="text" class="chat-input" id="chatInput" placeholder="Escribe un mensaje o /comando..." autocomplete="off">
                <button class="btn btn-primary" id="chatSend">▶ ENVIAR</button>
            </div>
        </div>
    </div>
</div>

<div class="grid">
    <div class="card full-width">
        <h2>📋 CONSOLA / LOGS</h2>
        <div class="console">
            <div class="console-log" id="consoleLog">
                <div class="console-line">[SISTEMA] Dashboard iniciado...</div>
            </div>
        </div>
    </div>
</div>

<script>
const chatInput = document.getElementById('chatInput');
const chatSend = document.getElementById('chatSend');
const chatMessages = document.getElementById('chatMessages');
const consoleLog = document.getElementById('consoleLog');
const playerList = document.getElementById('playerList');
const playerCount = document.getElementById('playerCount');
const serverIp = document.getElementById('serverIp');
const serverPort = document.getElementById('serverPort');
const serverVersion = document.getElementById('serverVersion');
const botName = document.getElementById('botName');
const statusBadge = document.getElementById('statusBadge');
const statusText = document.getElementById('statusText');
const btnConnect = document.getElementById('btnConnect');
const btnDisconnect = document.getElementById('btnDisconnect');

let lastLogCount = 0;
let lastChatCount = 0;
let lastPlayerCount = 0;

function getStatusClass(line) {
    if (line.includes('[ERROR]') || line.includes('[RECHAZADO]') || line.includes('[DESCONECTADO]'))
        return 'error';
    if (line.includes('[CHAT]'))
        return 'chat';
    if (line.includes('[AUTH]'))
        return 'auth';
    return '';
}

async function updateStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();

        serverIp.textContent = data.host;
        serverPort.textContent = data.port;
        serverVersion.textContent = data.version || '-';
        botName.textContent = data.username;

        if (data.connected) {
            statusBadge.className = 'status-badge online';
            statusText.textContent = 'Conectado';
            btnConnect.disabled = true;
            btnDisconnect.disabled = false;
        } else {
            statusBadge.className = 'status-badge offline';
            statusText.textContent = 'Desconectado';
            btnConnect.disabled = false;
            btnDisconnect.disabled = true;
        }

        if (data.players.length !== lastPlayerCount) {
            lastPlayerCount = data.players.length;
            renderPlayers(data.players);
        }
        playerCount.textContent = data.player_count;

        if (data.logs.length !== lastLogCount) {
            lastLogCount = data.logs.length;
            renderLogs(data.logs);
        }
        if (data.chat_messages.length !== lastChatCount) {
            lastChatCount = data.chat_messages.length;
            renderChat(data.chat_messages);
        }
    } catch (e) {
        statusBadge.className = 'status-badge offline';
        statusText.textContent = 'Error conexión';
    }
}

function renderPlayers(players) {
    if (players.length === 0) {
        playerList.innerHTML = '<div class="player-empty">Esperando jugadores...</div>';
        return;
    }
    playerList.innerHTML = players.map(p =>
        `<div class="player-item">
            <span class="player-name">${escapeHtml(p.name)}</span>
            <span class="player-latency">${p.latency} ms</span>
        </div>`
    ).join('');
}

function renderLogs(logs) {
    const container = consoleLog;
    const isAtBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 20;
    container.innerHTML = logs.slice(-100).map(line =>
        `<div class="console-line ${getStatusClass(line)}">${escapeHtml(line)}</div>`
    ).join('');
    if (isAtBottom) container.scrollTop = container.scrollHeight;
}

function renderChat(messages) {
    const container = chatMessages;
    const isAtBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 20;
    container.innerHTML = messages.slice(-50).map(m => {
        const isOwn = m.position === 2;
        return `<div class="chat-msg">
            <span class="time">${escapeHtml(m.time)}</span>
            <span class="sender" style="color:${isOwn?'#ffaa00':'#55ffff'}">${isOwn?'→':'<'} ${escapeHtml(m.sender||'?')}:</span>
            <span>${escapeHtml(m.message)}</span>
        </div>`;
    }).join('');
    if (isAtBottom) container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

async function sendMessage() {
    const msg = chatInput.value.trim();
    if (!msg) return;
    chatInput.value = '';
    try {
        await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg }),
        });
    } catch (e) { console.error('Error:', e); }
}

chatSend.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

async function connectBot() {
    btnConnect.disabled = true;
    statusBadge.className = 'status-badge connecting';
    statusText.textContent = 'Conectando...';
    try {
        const res = await fetch('/api/connect', { method: 'POST' });
        const data = await res.json();
        if (!data.ok) {
            statusBadge.className = 'status-badge offline';
            statusText.textContent = data.error || 'Error';
            btnConnect.disabled = false;
        }
    } catch (e) {
        statusBadge.className = 'status-badge offline';
        statusText.textContent = 'Error conexión';
        btnConnect.disabled = false;
    }
}

async function disconnectBot() {
    try {
        await fetch('/api/disconnect', { method: 'POST' });
    } catch (e) { console.error('Error:', e); }
}

let saveTimer = null;

function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveConfig, 400);
}

async function loadConfig() {
    try {
        const res = await fetch('/api/config');
        const cfg = await res.json();
        document.getElementById('cfgHost').value = cfg.server.host;
        document.getElementById('cfgPort').value = cfg.server.port;
        document.getElementById('cfgVersion').value = cfg.server.version;
        document.getElementById('cfgUsername').value = cfg.bot.username;
        const auth = cfg.auth || {};
        document.getElementById('toggleAuth').classList.toggle('active', auth.enabled);
        document.getElementById('cfgPassword').value = auth.password || '';
        document.getElementById('cfgDelay').value = auth.delay_after_join || 3;
        document.getElementById('cfgRegister').value = (auth.register && auth.register.enabled ? (auth.register.command || '') : '');
        document.getElementById('cfgLogin').value = (auth.login && auth.login.enabled ? (auth.login.command || '') : '');
    } catch (e) { console.error('Error loading config:', e); }
}

async function saveConfig() {
    const authEnabled = document.getElementById('toggleAuth').classList.contains('active');
    const registerCmd = document.getElementById('cfgRegister').value.trim();
    const loginCmd = document.getElementById('cfgLogin').value.trim();
    const cfg = {
        server: {
            host: document.getElementById('cfgHost').value.trim(),
            port: parseInt(document.getElementById('cfgPort').value) || 25565,
            version: document.getElementById('cfgVersion').value.trim(),
        },
        bot: {
            username: document.getElementById('cfgUsername').value.trim(),
        },
        auth: {
            enabled: authEnabled,
            password: document.getElementById('cfgPassword').value,
            delay_after_join: parseInt(document.getElementById('cfgDelay').value) || 3,
            register: {
                enabled: !!registerCmd,
                command: registerCmd || '/register $password $password',
            },
            login: {
                enabled: !!loginCmd,
                command: loginCmd || '/login $password',
            },
        },
    };
    try {
        await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cfg),
        });
    } catch (e) { console.error('Error saving config:', e); }
}

function updateToggleState() {
    scheduleSave();
}

document.querySelectorAll('.config-group input').forEach(el => {
    el.addEventListener('input', scheduleSave);
});

function addLog(msg) {
    const ts = new Date().toTimeString().slice(0, 8);
    const container = consoleLog;
    container.innerHTML += `<div class="console-line">[${ts}] ${escapeHtml(msg)}</div>`;
    container.scrollTop = container.scrollHeight;
}

setInterval(updateStatus, 2000);
loadConfig();
updateStatus();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/ping")
def ping():
    return "pong"


@app.route("/api/status")
def api_status():
    b = get_bot()
    return jsonify(b.get_status() if b else {
        "connected": False, "spawned": False,
        "host": "-", "port": "-", "username": "-", "version": "-",
        "players": [], "player_count": 0,
        "logs": [], "chat_messages": [], "pos": {},
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    b = get_bot()
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"ok": False, "error": "Mensaje vacío"}), 400
    if not b.connected:
        return jsonify({"ok": False, "error": "Bot no conectado"}), 400
    b.send_chat(message)
    return jsonify({"ok": True})


@app.route("/api/logs")
def api_logs():
    b = get_bot()
    return jsonify(b.get_status()["logs"] if b else [])


@app.route("/api/health")
def api_health():
    return jsonify({"ok": True, "bot_available": BOT_AVAILABLE})


@app.route("/api/connect", methods=["POST"])
def api_connect():
    global bot
    with bot_lock:
        if bot and bot.connected:
            return jsonify({"ok": False, "error": "Ya conectado"})
        bot = Bot()
    t = threading.Thread(target=bot.connect, daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/api/disconnect", methods=["POST"])
def api_disconnect():
    global bot
    with bot_lock:
        if not bot or not bot.connected:
            return jsonify({"ok": False, "error": "No conectado"})
        bot.disconnect()
    return jsonify({"ok": True})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "GET":
        with open("config.json", "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "error": "JSON inválido"}), 400
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
