import json
import math
import os
import time
import threading
from minecraft.networking.connection import Connection
from minecraft.networking.packets import clientbound, serverbound


def parse_chat_json(data):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return data
    if isinstance(data, str):
        return data
    if "translate" in data:
        args = [parse_chat_json(a) for a in data.get("with", [])]
        key = data["translate"]
        if key == "chat.type.text" and len(args) >= 2:
            return f"<{args[0]}> {args[1]}"
        if key == "multiplayer.player.joined" and args:
            return f"{args[0]} joined the game"
        if key == "multiplayer.player.left" and args:
            return f"{args[0]} left the game"
        if args:
            return " ".join(str(a) for a in args)
        return key
    if "text" in data:
        return data["text"]
    if "extra" in data:
        return "".join(parse_chat_json(item) for item in data["extra"])
    return str(data)


class Bot:
    def __init__(self, config_path="config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        srv = self.config["server"]
        bot_cfg = self.config["bot"]

        srv["host"] = os.environ.get("SERVER_HOST", srv["host"])
        srv["port"] = int(os.environ.get("SERVER_PORT", str(srv["port"])))
        srv["version"] = os.environ.get("SERVER_VERSION", srv["version"])
        bot_cfg["username"] = os.environ.get("BOT_USERNAME", bot_cfg["username"])

        self.host = srv["host"]
        self.port = srv["port"]
        self.version = srv["version"]
        self.username = bot_cfg["username"]

        self.connection = None
        self.connected = False
        self.spawned = False

        self.players = {}
        self.logs = []
        self.chat_messages = []
        self.pos = {"x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0.0, "pitch": 0.0}
        self.angle = 0.0
        self.walking = False
        self._lock = threading.Lock()

    def log(self, message):
        with self._lock:
            ts = time.strftime("%H:%M:%S")
            entry = f"[{ts}] {message}"
            self.logs.append(entry)
            if len(self.logs) > 200:
                self.logs = self.logs[-200:]

    def add_chat(self, sender, message, position=0):
        with self._lock:
            entry = {
                "sender": sender,
                "message": message,
                "time": time.strftime("%H:%M:%S"),
                "position": position,
            }
            self.chat_messages.append(entry)
            if len(self.chat_messages) > 100:
                self.chat_messages = self.chat_messages[-100:]

    def connect(self):
        self.log(f"Conectando a {self.host}:{self.port} como '{self.username}'...")

        self.connection = Connection(
            address=self.host,
            port=self.port,
            username=self.username,
            initial_version=self.version,
        )

        self.connection.register_packet_listener(
            self._on_login_disconnect, clientbound.login.DisconnectPacket
        )
        self.connection.register_packet_listener(
            self._on_disconnect, clientbound.play.DisconnectPacket
        )
        self.connection.register_packet_listener(
            self._on_join_game, clientbound.play.JoinGamePacket
        )
        self.connection.register_packet_listener(
            self._on_position_look, clientbound.play.PlayerPositionAndLookPacket
        )
        self.connection.register_packet_listener(
            self._on_player_list, clientbound.play.PlayerListItemPacket
        )
        self.connection.register_packet_listener(
            self._on_chat, clientbound.play.ChatMessagePacket
        )

        try:
            self.connection.connect()
        except Exception as e:
            self.log(f"Error de conexión: {e}")
            return

        timeout = 15
        start = time.time()
        while not self.connection.spawned and time.time() - start < timeout:
            time.sleep(0.5)

        if not self.connection.spawned:
            self.log("No se pudo conectar (tiempo de espera agotado).")
            self.connected = False
            return

        self.spawned = True
        self.connected = True
        self.log("¡Conectado al servidor!")

        self._do_auth()

        self.walking = True
        threading.Thread(target=self._walk_loop, daemon=True).start()
        self.log("Bot caminando en círculos.")

        threading.Thread(target=self._keep_alive, daemon=True).start()

    def _do_auth(self):
        auth = self.config.get("auth", {})
        if not auth.get("enabled", False):
            return

        pwd = os.environ.get("AUTH_PASSWORD", auth.get("password", ""))
        delay = int(os.environ.get("AUTH_DELAY", str(auth.get("delay_after_join", 3))))
        time.sleep(delay)

        reg = auth.get("register", {})
        if reg.get("enabled", False):
            cmd = os.environ.get("AUTH_REGISTER_CMD", reg["command"]).replace("$password", pwd)
            pkt = serverbound.play.ChatPacket()
            pkt.message = cmd
            self.connection.write_packet(pkt)
            self.log("[AUTH] Registro enviado")

        log = auth.get("login", {})
        if log.get("enabled", False):
            cmd = os.environ.get("AUTH_LOGIN_CMD", log["command"]).replace("$password", pwd)
            pkt = serverbound.play.ChatPacket()
            pkt.message = cmd
            self.connection.write_packet(pkt)
            self.log("[AUTH] Login enviado")

    def send_chat(self, message):
        if not self.connected:
            return False
        pkt = serverbound.play.ChatPacket()
        pkt.message = message
        self.connection.write_packet(pkt)
        self.log(f"[ENVIADO] {message}")
        return True

    def _on_login_disconnect(self, packet):
        self.log(f"[RECHAZADO] {packet.json_data}")

    def _on_disconnect(self, packet):
        msg = parse_chat_json(packet.json_data)
        self.log(f"[DESCONECTADO] {msg}")
        self.connected = False

    def _on_join_game(self, packet):
        settings = serverbound.play.ClientSettingsPacket()
        settings.locale = "es_ES"
        settings.view_distance = 4
        settings.chat_mode = 0
        settings.chat_colors = True
        settings.displayed_skin_parts = 0xFF
        settings.main_hand = 0
        self.connection.write_packet(settings)

        status = serverbound.play.ClientStatusPacket()
        status.action_id = 0
        self.connection.write_packet(status)

        brand_str = "pyCraft"
        brand_data = len(brand_str).to_bytes(1, "big") + brand_str.encode("utf-8")
        brand = serverbound.play.PluginMessagePacket()
        brand.channel = "minecraft:brand"
        brand.data = brand_data
        self.connection.write_packet(brand)

    def _on_position_look(self, packet):
        self.pos["x"] = packet.x
        self.pos["y"] = packet.y
        self.pos["z"] = packet.z
        self.pos["yaw"] = packet.yaw
        self.pos["pitch"] = packet.pitch

    def _on_player_list(self, packet):
        for action in packet.actions:
            uuid = str(action.uuid)
            if packet.action_type.action_id == 0:
                self.players[uuid] = {"name": action.name, "latency": action.ping}
                self.log(f"Jugador conectado: {action.name}")
            elif packet.action_type.action_id == 4:
                if uuid in self.players:
                    name = self.players[uuid]["name"]
                    del self.players[uuid]
                    self.log(f"Jugador desconectado: {name}")
            elif packet.action_type.action_id == 2:
                if uuid in self.players:
                    self.players[uuid]["latency"] = action.ping

    def _on_chat(self, packet):
        raw = packet.json_data
        data = json.loads(raw) if isinstance(raw, str) else raw
        sender = "?"
        msg = str(raw)
        if isinstance(data, dict) and "translate" in data:
            args = [parse_chat_json(a) for a in data.get("with", [])]
            if data["translate"] == "chat.type.text" and len(args) >= 2:
                sender, msg = args[0], args[1]
        if sender == "?":
            msg = parse_chat_json(raw)
        position = packet.position if hasattr(packet, "position") else 0
        if sender == self.username:
            position = 2
        self.add_chat(sender, msg, position)
        self.log(f"[CHAT] {sender}: {msg}")

    def _walk_loop(self):
        while self.connected:
            if self.walking:
                cx, cz = self.pos["x"], self.pos["z"]
                self.angle += 0.05
                r = 2.0
                nx = cx + r * math.cos(self.angle)
                nz = cz + r * math.sin(self.angle)

                pkt = serverbound.play.PositionAndLookPacket()
                pkt.x = nx
                pkt.feet_y = self.pos["y"]
                pkt.z = nz
                pkt.yaw = math.degrees(-self.angle) % 360
                pkt.pitch = 0.0
                pkt.on_ground = True
                self.connection.write_packet(pkt)
            time.sleep(0.05)

    def _keep_alive(self):
        while self.connected:
            time.sleep(1)

    def get_status(self):
        with self._lock:
            players = [{"name": p["name"], "latency": p["latency"]} for p in self.players.values()]
            return {
                "connected": self.connected,
                "spawned": self.spawned,
                "host": self.host,
                "port": self.port,
                "username": self.username,
                "version": self.version,
                "players": players,
                "player_count": len(players),
                "logs": list(self.logs),
                "chat_messages": list(self.chat_messages),
                "pos": dict(self.pos),
            }

    def disconnect(self):
        self.walking = False
        self.connected = False
        if self.connection:
            try:
                self.connection.disconnect()
            except Exception:
                pass
            self.log("Bot desconectado.")


if __name__ == "__main__":
    bot = Bot()
    try:
        bot.connect()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDesconectando...")
    finally:
        bot.disconnect()
