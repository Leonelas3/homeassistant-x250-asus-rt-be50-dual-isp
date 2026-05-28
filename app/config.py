ROUTER_IP = "192.168.50.1"
ROUTER_USER = "admin"
HAOS_IP = "192.168.50.10"
HP_MINI_IP = "192.168.50.20"
LAN_SUBNET = "192.168.50"
DUCKDNS_DOMAIN = "leonelastres"
HA_LOCAL_URL = f"http://{HAOS_IP}:8123"
HA_EXTERNAL_URL = f"https://{DUCKDNS_DOMAIN}.duckdns.org"
ROUTER_URL = f"http://{ROUTER_IP}"
UPLOAD_PORTS = "21,22,990,2283,8123"

KNOWN_DEVICES = {
    ROUTER_IP:  ("Router Asus RT-BE50",            "Router"),
    HAOS_IP:    ("ThinkPad X250 — Home Assistant",  "Servidor HA"),
    HP_MINI_IP: ("HP Pro Mini 400 G9 — Windows 11", "PC Windows"),
}

REPO_ROOT = __import__("pathlib").Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "jffs"
GUIDE_FILE  = REPO_ROOT / "ROUTER-SETUP-GUIDE.md"
