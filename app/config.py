ROUTER_IP    = "192.168.50.1"
ROUTER_USER  = "admin"
HAOS_IP      = "192.168.50.10"   # HA OS en Hyper-V (HP Pro Mini) — reservar en DHCP
HP_MINI_IP   = "192.168.50.20"   # HP Pro Mini 400 G9 — Windows 11, host Hyper-V
GOOGLE_TV_IP = "192.168.50.30"   # Google TV Streamer (Philips dormitorio) — reservar en DHCP
LAN_SUBNET   = "192.168.50"
DUCKDNS_DOMAIN = "leonelastres"
HA_LOCAL_URL    = f"http://{HAOS_IP}:8123"
HA_EXTERNAL_URL = f"https://{DUCKDNS_DOMAIN}.duckdns.org"
ROUTER_URL      = f"http://{ROUTER_IP}"
UPLOAD_PORTS    = "21,22,990,2283,8123"

KNOWN_DEVICES = {
    ROUTER_IP:    ("Router Asus RT-BE50",                   "Router"),
    HAOS_IP:      ("Home Assistant OS — Hyper-V (HP Mini)", "Servidor HA"),
    HP_MINI_IP:   ("HP Pro Mini 400 G9 — Windows 11",       "PC Windows"),
    GOOGLE_TV_IP: ("Google TV Streamer — Philips dormit.",   "Smart TV"),
}

REPO_ROOT   = __import__("pathlib").Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "jffs"
GUIDE_FILE  = REPO_ROOT / "ROUTER-SETUP-GUIDE.md"
