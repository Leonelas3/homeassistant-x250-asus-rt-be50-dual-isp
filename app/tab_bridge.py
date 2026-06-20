"""
Tab de migración: Movistar GPT-2742GX4X5v6 → bridge mode, PPPoE en Asus RT-BE50.

Flujo de uso (requiere cambiar de WiFi entre pasos):
  Paso 1  — WiFi Asus   → backup nvram Asus
  Paso 2  — WiFi Movistar → backup config + extraer PPPoE
  Paso 3  — cualquier WiFi (Asus accesible) → configurar PPPoE en Asus
  Paso 4  — WiFi Movistar → activar bridge mode
  Paso 5  — WiFi Asus   → reiniciar WAN y verificar PPPoE
"""
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QTextEdit, QLabel, QSplitter, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

import config

try:
    import paramiko
    PARAMIKO_OK = True
except ImportError:
    PARAMIKO_OK = False

try:
    import requests as _req
    _req.packages.urllib3.disable_warnings()
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

BACKUPS_DIR = config.REPO_ROOT / "backups"

# Credenciales Movistar conocidas por defecto (el usuario las puede cambiar en la UI)
MOVISTAR_DEFAULT_IP   = "192.168.1.1"
MOVISTAR_DEFAULT_USER = "admin"


# ── Worker SSH genérico ────────────────────────────────────────────────────────

class SSHWorker(QThread):
    output = pyqtSignal(str)
    done   = pyqtSignal(bool, str)

    def __init__(self, host, user, password, task, extra=None):
        super().__init__()
        self._host  = host
        self._user  = user
        self._pwd   = password
        self._task  = task
        self._extra = extra or {}

    # ── helpers ───────────────────────────────────────────────────────────────

    def _connect(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self._host, username=self._user, password=self._pwd,
                    timeout=12, banner_timeout=15)
        self.output.emit(f"[+] Conectado a {self._host}\n")
        return ssh

    def _cmd(self, ssh, cmd):
        _, out, err = ssh.exec_command(cmd, timeout=20)
        return out.read().decode(errors="replace"), err.read().decode(errors="replace")

    def _emit_var(self, ssh, var, label=None):
        val, _ = self._cmd(ssh, f"nvram get {var}")
        self.output.emit(f"    {label or var} = {val.strip()}\n")
        return val.strip()

    # ── tareas ────────────────────────────────────────────────────────────────

    def run(self):
        if not PARAMIKO_OK:
            self.done.emit(False, "paramiko no instalado — ejecuta: pip install paramiko")
            return
        try:
            getattr(self, f"_task_{self._task}")()
        except Exception as exc:
            self.done.emit(False, str(exc))

    # Paso 1 ─────────────────────────────────────────────────────────────────
    def _task_backup_asus(self):
        ssh = self._connect()
        BACKUPS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.output.emit("\n>> nvram show completo...\n")
        full, _ = self._cmd(ssh, "nvram show 2>/dev/null")
        fpath = BACKUPS_DIR / f"asus_nvram_{ts}.txt"
        fpath.write_text(full, encoding="utf-8")
        self.output.emit(f"    Guardado: {fpath}\n")

        self.output.emit("\n>> Resumen WAN actual:\n")
        for var in [
            "wan0_proto", "wan0_ipaddr", "wan0_gateway",
            "wan0_pppoe_username", "wan0_netmask", "wan0_dns",
            "wan1_proto", "wan1_ipaddr",
        ]:
            self._emit_var(ssh, var)

        ssh.close()
        self.done.emit(True, f"Backup Asus guardado → {fpath.name}")

    # Paso 2 ─────────────────────────────────────────────────────────────────
    def _task_backup_movistar(self):
        ssh = self._connect()
        BACKUPS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.output.emit("\n>> Intentando nvram show en Movistar...\n")
        full, err = self._cmd(ssh, "nvram show 2>/dev/null || cat /proc/nvram 2>/dev/null || echo 'nvram no disponible'")
        if full.strip() and "no disponible" not in full:
            fpath = BACKUPS_DIR / f"movistar_nvram_{ts}.txt"
            fpath.write_text(full, encoding="utf-8")
            self.output.emit(f"    Guardado: {fpath}\n")
        else:
            self.output.emit(f"    nvram no accesible por SSH.\n")

        self.output.emit("\n>> Buscando credenciales PPPoE...\n")
        pppoe_cmds = [
            "nvram get wan0_pppoe_username",
            "nvram get wan0_pppoe_passwd",
            "nvram get ppp_username",
            "nvram get ppp_passwd",
            "cat /etc/ppp/peers/wan 2>/dev/null",
            "cat /var/tmp/ppp/options 2>/dev/null",
            r"grep -i 'user\|pass\|pppoe' /etc/pppoe.conf 2>/dev/null",
        ]
        creds_lines = []
        for cmd in pppoe_cmds:
            val, _ = self._cmd(ssh, cmd)
            if val.strip():
                line = f"    [{cmd.split()[0]} {cmd.split()[-1] if len(cmd.split()) > 1 else ''}] → {val.strip()}"
                self.output.emit(line + "\n")
                creds_lines.append(line)

        if creds_lines:
            cpath = BACKUPS_DIR / f"movistar_pppoe_{ts}.txt"
            cpath.write_text("\n".join(creds_lines), encoding="utf-8")
            self.output.emit(f"\n    Credenciales guardadas: {cpath}\n")
        else:
            self.output.emit("    No se encontraron credenciales PPPoE via SSH.\n")
            self.output.emit("    → Ve a http://192.168.1.1 y anota manualmente el usuario PPPoE.\n")

        # Intentar descarga backup web
        self.output.emit("\n>> Intentando backup via HTTP (curl local)...\n")
        for url_path in ["/backupsettings.conf", "/backup.conf", "/cgi-bin/backup.cgi"]:
            out, _ = self._cmd(ssh,
                f"curl -sk --max-time 8 -u {self._user}:{self._pwd} "
                f"http://127.0.0.1{url_path} -o /tmp/mov_bak.bin -w '%{{http_code}}'"
            )
            if out.strip() == "200":
                sftp = ssh.open_sftp()
                bpath = BACKUPS_DIR / f"movistar_web_backup_{ts}.bin"
                try:
                    sftp.get("/tmp/mov_bak.bin", str(bpath))
                    self.output.emit(f"    Web backup descargado: {bpath}\n")
                except Exception as e:
                    self.output.emit(f"    Error descargando backup: {e}\n")
                finally:
                    sftp.close()
                break
        else:
            self.output.emit("    Web backup no disponible (normal si el router lo requiere via interfaz gráfica).\n")

        ssh.close()
        self.done.emit(True, "Backup Movistar completado")

    # Paso 3 ─────────────────────────────────────────────────────────────────
    def _task_set_pppoe_asus(self):
        pppoe_user = self._extra.get("pppoe_user", "").strip()
        pppoe_pass = self._extra.get("pppoe_pass", "").strip()
        if not pppoe_user or not pppoe_pass:
            self.done.emit(False, "Introduce usuario y contraseña PPPoE antes de continuar")
            return

        ssh = self._connect()

        self.output.emit("\n>> Backup nvram previo a cambios...\n")
        full, _ = self._cmd(ssh, "nvram show 2>/dev/null")
        BACKUPS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pre = BACKUPS_DIR / f"asus_pre_pppoe_{ts}.txt"
        pre.write_text(full, encoding="utf-8")
        self.output.emit(f"    Backup previo: {pre.name}\n")

        self.output.emit("\n>> Configurando PPPoE en WAN0...\n")
        nvram_cmds = [
            ("protocolo",        f"nvram set wan0_proto=pppoe"),
            ("usuario PPPoE",    f"nvram set wan0_pppoe_username={pppoe_user}"),
            ("contraseña PPPoE", f"nvram set wan0_pppoe_passwd={pppoe_pass}"),
            ("MTU PPPoE",        "nvram set wan0_pppoe_mtu=1492"),
            ("MRU PPPoE",        "nvram set wan0_pppoe_mru=1492"),
            ("service name",     "nvram set wan0_pppoe_service="),
            ("guardar flash",    "nvram commit"),
        ]
        for label, cmd in nvram_cmds:
            self.output.emit(f"    {label}... ")
            out, err = self._cmd(ssh, cmd)
            self.output.emit("OK\n" if not err.strip() else f"WARN: {err.strip()}\n")

        self.output.emit("\n>> Verificación post-config:\n")
        for var in ["wan0_proto", "wan0_pppoe_username", "wan0_pppoe_mtu"]:
            self._emit_var(ssh, var)

        self.output.emit(
            "\nNOTA: PPPoE configurado pero WAN no reiniciada todavía.\n"
            "Activa el bridge en Movistar (Paso 4) y luego reinicia la WAN (Paso 5).\n"
        )
        ssh.close()
        self.done.emit(True, "PPPoE configurado en Asus — pendiente: bridge Movistar + reinicio WAN")

    # Paso 4 ─────────────────────────────────────────────────────────────────
    def _task_bridge_movistar(self):
        ssh = self._connect()
        self.output.emit("\n>> Intentando activar bridge mode via SSH...\n")

        # Intentar varios métodos según firmware
        methods = [
            # Método nvram genérico (muchos routers ZTE/ASUS-derivados)
            (
                "nvram (método 1)",
                [
                    "nvram set wan0_proto=bridge",
                    "nvram set wan_proto=bridge",
                    "nvram commit",
                ]
            ),
            # Método UCI (OpenWrt-derivados)
            (
                "uci (método 2)",
                [
                    "uci set network.wan.proto=none",
                    "uci commit network",
                ]
            ),
        ]

        success = False
        for name, cmds in methods:
            self.output.emit(f"\n  Probando {name}...\n")
            try:
                for cmd in cmds:
                    out, err = self._cmd(ssh, cmd)
                    status = "OK" if not err.strip() else f"({err.strip()[:60]})"
                    self.output.emit(f"    {cmd[:50]} → {status}\n")
                success = True
                break
            except Exception as e:
                self.output.emit(f"  Error en {name}: {e}\n")

        if success:
            self.output.emit("\n>> Reiniciando Movistar para aplicar bridge mode...\n")
            self._cmd(ssh, "reboot &")
            self.output.emit(
                "    Movistar reiniciando. Espera ~60 segundos.\n"
                "    Después, cambia a WiFi Asus y ejecuta el Paso 5.\n"
            )
            self.done.emit(True, "Bridge mode enviado — Movistar reiniciando")
        else:
            self.output.emit(
                "\nNo se pudo activar bridge mode por SSH.\n"
                "ACCION MANUAL: abre http://192.168.1.1 en el navegador\n"
                "y busca: Configuracion avanzada → WAN → Modo de conexion → Puente (Bridge)\n"
            )
            self.done.emit(False, "Bridge mode requiere configuracion manual via web")

        try:
            ssh.close()
        except Exception:
            pass

    # Paso 5 ─────────────────────────────────────────────────────────────────
    def _task_restart_wan_asus(self):
        ssh = self._connect()
        self.output.emit("\n>> Reiniciando WAN0 del Asus...\n")

        # service restart_wan es el comando oficial de AsusWRT
        out, err = self._cmd(ssh, "service restart_wan 2>&1")
        self.output.emit(f"    {out.strip() or 'Comando enviado'}\n")

        self.output.emit("\n>> Esperando 15 s para que se establezca PPPoE...\n")
        import time; time.sleep(15)

        self.output.emit("\n>> Estado PPPoE:\n")
        out2, _ = self._cmd(ssh, "ifconfig ppp0 2>/dev/null || echo 'ppp0 aun no activo'")
        self.output.emit(out2 + "\n")

        out3, _ = self._cmd(ssh, "nvram get wan0_ipaddr")
        self.output.emit(f"    IP WAN0: {out3.strip()}\n")

        out4, _ = self._cmd(ssh, "nvram get wan0_proto")
        self.output.emit(f"    Protocolo: {out4.strip()}\n")

        if "ppp0" in out2 and "inet addr" in out2:
            self.done.emit(True, "PPPoE activo — conexion establecida")
        else:
            self.output.emit(
                "\nSi ppp0 no esta activo todavia, espera 30 s mas y pulsa\n"
                "'Verificar estado PPPoE' para comprobar de nuevo.\n"
            )
            self.done.emit(True, "WAN reiniciada — verifica PPPoE en unos segundos")

    def _task_check_pppoe(self):
        ssh = self._connect()
        self.output.emit("\n>> Estado PPPoE / WAN0:\n")
        for cmd, label in [
            ("nvram get wan0_proto",           "Protocolo"),
            ("nvram get wan0_ipaddr",          "IP publica"),
            ("nvram get wan0_gateway",         "Gateway"),
            ("nvram get wan0_dns",             "DNS"),
            ("nvram get wan0_pppoe_username",  "PPPoE usuario"),
            ("ifconfig ppp0 2>/dev/null || echo 'ppp0 no activo'", "Interfaz ppp0"),
        ]:
            out, _ = self._cmd(ssh, cmd)
            self.output.emit(f"    {label}: {out.strip()}\n")
        ssh.close()
        self.done.emit(True, "Diagnostico completado")


# ── Worker scraping HTTP ───────────────────────────────────────────────────────

class WebScrapeWorker(QThread):
    output = pyqtSignal(str)
    done   = pyqtSignal(bool, str)

    # Rutas reales del Movistar GPT-2742GX4X5v6 (Router Smart WiFi 6 Go)
    # Descubiertas analizando main.js del router (186 KB)
    _PAGES = [
        ("/cgi-bin/mhs/returnInternetJSON.asp",  "internet_json"),   # ← PPPoE user/pass en JSON
        ("/cgi-bin/mhs/returnRouterJSON.asp",    "router_json"),
        ("/cgi-bin/mhs/returnLANJSON.asp",       "lan_json"),
        ("/cgi-bin/mhs/returnPassJSON.asp",      "pass_json"),
        ("/cgi-bin/deviceinfo.cgi",              "deviceinfo"),
        ("/cgi-bin/sysinfo.cgi",                 "sysinfo"),
        ("/cgi-bin/Aviso.cgi",                   "aviso"),
        ("/cgi-bin/mhs.cgi",                     "mhs_wifi"),
        ("/cgi-bin/wifi5g.cgi",                  "wifi5g"),
        ("/cgi-bin/backupRestoreSetting.cgi",    "backup_restore"),
        ("/html/internet/index.html",            "internet_html"),
        ("/html/wan/index.html",                 "wan_html"),
        ("/cgi-bin/gui.cgi?file=wan.html",       "wan_cgi"),
    ]
    # Patrones regex para extraer credenciales PPPoE del HTML/JSON
    _PPPOE_RE = [
        r'(?i)"?PPP[_-]?USER(?:NAME)?"?\s*[=:,"\s]+([^\s"<>&;\n\}]{5,80})',
        r'(?i)"?wan[_-]?pppoe[_-]?user(?:name)?"?\s*[=:,"\s]+([^\s"<>&;\n\}]{5,80})',
        r'(?i)"?pppoe[_-]?user(?:name)?"?\s*[=:,"\s]+([^\s"<>&;\n\}]{5,80})',
        r'(?i)(adslppp@[^\s"<>&;\n\}]{3,60})',
        r'(?i)value="(adslppp[^"]{0,60})"',
        r'(?i)"USER"\s*:\s*"([^"]{5,80})"',
        r'(?i)"username"\s*:\s*"([^"@]{0,}@[^"]{3,})"',
    ]

    def __init__(self, host, user, password):
        super().__init__()
        self._host = host
        self._user = user
        self._pwd  = password

    def run(self):
        if not REQUESTS_OK:
            self.done.emit(False, "requests no instalado — ejecuta: pip install requests")
            return

        import re
        import requests

        base = f"http://{self._host}"
        s = requests.Session()
        s.verify = False
        s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; RouterScan/1.0)"})

        BACKUPS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ── Login ──────────────────────────────────────────────────────────────
        self.output.emit("\n>> Intentando login en interfaz web Movistar...\n")
        self._do_login(s, base)

        # ── Descargar páginas ──────────────────────────────────────────────────
        self.output.emit("\n>> Escaneando páginas del router...\n")
        all_html = ""
        found_creds = []

        for path, slug in self._PAGES:
            try:
                r = s.get(
                    f"{base}{path}",
                    timeout=8,
                    allow_redirects=True,
                    headers={"Referer": f"{base}/"},
                )
                if r.status_code == 200 and len(r.text) > 300:
                    fname = BACKUPS_DIR / f"movistar_web_{slug}_{ts}.html"
                    fname.write_text(r.text, encoding="utf-8", errors="replace")
                    self.output.emit(f"    {path:45s} → {len(r.text):6d} bytes → {fname.name}\n")
                    all_html += r.text

                    for pat in self._PPPOE_RE:
                        for m in re.findall(pat, r.text):
                            m = m.strip()
                            if m and m not in found_creds and len(m) > 4:
                                found_creds.append(m)
                                self.output.emit(f"    *** PPPoE encontrado: {m}\n")
                else:
                    self.output.emit(f"    {path:45s} → HTTP {r.status_code} (skip)\n")
            except Exception:
                pass

        # ── Guardar HTML combinado ─────────────────────────────────────────────
        if all_html:
            combined = BACKUPS_DIR / f"movistar_web_all_{ts}.html"
            combined.write_text(all_html, encoding="utf-8", errors="replace")
            self.output.emit(f"\n    HTML total guardado: {combined.name} ({len(all_html)//1024} KB)\n")

        # ── Resultado ─────────────────────────────────────────────────────────
        if found_creds:
            cpath = BACKUPS_DIR / f"movistar_pppoe_web_{ts}.txt"
            cpath.write_text("\n".join(found_creds), encoding="utf-8")
            self.output.emit(f"\n[+] Credenciales PPPoE encontradas en la web:\n")
            for c in found_creds:
                self.output.emit(f"    {c}\n")
            self.done.emit(True, f"PPPoE web: {found_creds[0]}")
        else:
            self.output.emit(
                "\n    No se extrajeron credenciales automáticamente.\n"
                "    Revisa los archivos .html en backups/ o usa el tab Navegador\n"
                "    para abrir http://192.168.1.1 manualmente.\n"
            )
            self.done.emit(True, "Escaneo web completado — revisa backups/*.html")

    def _do_login(self, s, base):
        import re, hashlib
        # Paso 1: obtener el SID embebido en la página de login
        try:
            r0 = s.get(f"{base}/", timeout=8,
                       headers={"Referer": f"{base}/", "User-Agent": "Mozilla/5.0"})
            html = r0.content.decode("utf-8", errors="replace")
            m = re.search(r"var sid = '([0-9a-fA-F]+)'", html)
            sid = m.group(1) if m else "1865e182"
            self.output.emit(f"    SID obtenido: {sid}\n")
        except Exception as e:
            sid = "1865e182"
            self.output.emit(f"    No se pudo obtener SID ({e}), usando valor por defecto\n")

        # Paso 2: calcular hash  →  hex_md5(password + ":" + sid)
        raw = f"{self._pwd}:{sid}".encode("utf-8")
        passwd_hash = hashlib.md5(raw).hexdigest()

        # Paso 3: POST del formulario de login
        # El endpoint real del Movistar GPT-2742GX4X5v6 es /cgi-bin/logIn_mhs.cgi
        # (la raíz / también acepta el POST pero redirige allí)
        data = {
            "sessionKey":   "",
            "submitValue":  "1",
            "syspasswd":    passwd_hash,
            "syspasswd_1":  "",
            "fake_syspasswd": "",
            "leaveBlur":    "0",
            "Submit":       "Entrar",
        }
        login_urls = [f"{base}/cgi-bin/logIn_mhs.cgi", f"{base}/"]
        for login_url in login_urls:
            try:
                r1 = s.post(login_url, data=data, timeout=10, allow_redirects=True,
                            headers={"Referer": f"{base}/",
                                     "Content-Type": "application/x-www-form-urlencoded"})
                body = r1.content.decode("utf-8", errors="replace")
                if "autorizacion fallo" in body or "intentar" in body.lower():
                    self.output.emit(f"    BLOQUEADO — demasiados intentos fallidos. Espera 5 min.\n")
                    return
                elif r1.status_code == 200 and 'id="login"' not in body:
                    self.output.emit(f"    Login exitoso vía {login_url.split('/')[-1]} (HTTP {r1.status_code})\n")
                    return
                elif r1.status_code in (301, 302):
                    self.output.emit(f"    Login redirige → HTTP {r1.status_code} (ok)\n")
                    return
                else:
                    self.output.emit(f"    {login_url.split('/')[-1]}: HTTP {r1.status_code} — contraseña incorrecta o bloqueado\n")
            except Exception as e:
                self.output.emit(f"    Error POST {login_url}: {e}\n")


# ── Tab principal ──────────────────────────────────────────────────────────────

class BridgeSetupTab(QWidget):
    def __init__(self, historial):
        super().__init__()
        self._historial = historial
        self._worker = None
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)

        # ── Credenciales ──
        creds_box = QGroupBox("Credenciales SSH")
        creds_form = QFormLayout(creds_box)

        self._asus_ip   = QLineEdit(config.ROUTER_IP)
        self._asus_user = QLineEdit(config.ROUTER_USER)
        self._asus_pass = QLineEdit()
        self._asus_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._asus_pass.setPlaceholderText("password Asus")

        self._mov_ip   = QLineEdit(MOVISTAR_DEFAULT_IP)
        self._mov_user = QLineEdit(MOVISTAR_DEFAULT_USER)
        self._mov_pass = QLineEdit()
        self._mov_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._mov_pass.setPlaceholderText("password Movistar (etiqueta del router)")

        creds_form.addRow(QLabel("— Asus RT-BE50 —"))
        creds_form.addRow("IP Asus:",       self._asus_ip)
        creds_form.addRow("Usuario:",       self._asus_user)
        creds_form.addRow("Password Asus:", self._asus_pass)
        creds_form.addRow(_separator())
        creds_form.addRow(QLabel("— Movistar GPT-2742GX4X5v6 —"))
        creds_form.addRow("IP Movistar:",       self._mov_ip)
        creds_form.addRow("Usuario:",           self._mov_user)
        creds_form.addRow("Password Movistar:", self._mov_pass)

        left_layout.addWidget(creds_box)

        # ── Paso 1 ──
        p1 = QGroupBox("Paso 1 — Backup Asus  [WiFi: Asus]")
        p1_l = QVBoxLayout(p1)
        p1_l.addWidget(QLabel("Conectado a la WiFi del Asus RT-BE50."))
        btn_bk_asus = QPushButton("Hacer backup nvram Asus → archivo")
        btn_bk_asus.clicked.connect(lambda: self._run(
            self._asus_ip, self._asus_user, self._asus_pass,
            "backup_asus", "Backup Asus"
        ))
        p1_l.addWidget(btn_bk_asus)
        left_layout.addWidget(p1)

        # ── Paso 2 ──
        p2 = QGroupBox("Paso 2 — Backup Movistar  [WiFi: Movistar]")
        p2_l = QVBoxLayout(p2)
        p2_l.addWidget(_wifi_label("Cambia a la WiFi del Movistar antes de este paso."))
        btn_bk_mov = QPushButton("Backup via SSH (nvram)")
        btn_bk_mov.clicked.connect(lambda: self._run(
            self._mov_ip, self._mov_user, self._mov_pass,
            "backup_movistar", "Backup Movistar SSH"
        ))
        btn_web_scan = QPushButton("Escanear interfaz web → extraer PPPoE  [RECOMENDADO]")
        btn_web_scan.setStyleSheet("font-weight: bold; color: #1565C0;")
        btn_web_scan.clicked.connect(self._run_web_scan)
        p2_l.addWidget(btn_bk_mov)
        p2_l.addWidget(btn_web_scan)
        if not REQUESTS_OK:
            p2_l.addWidget(QLabel("⚠ requests no instalado — pip install requests beautifulsoup4"))
        left_layout.addWidget(p2)

        # ── Paso 3 ──
        p3 = QGroupBox("Paso 3 — Configurar PPPoE en Asus  [WiFi: Asus]")
        p3_l = QVBoxLayout(p3)
        p3_l.addWidget(_wifi_label("Vuelve a la WiFi del Asus."))
        pppoe_form = QFormLayout()
        self._pppoe_user = QLineEdit()
        self._pppoe_user.setPlaceholderText("usuario PPPoE (del backup Movistar)")
        self._pppoe_pass = QLineEdit()
        self._pppoe_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._pppoe_pass.setPlaceholderText("contraseña PPPoE")
        pppoe_form.addRow("Usuario PPPoE:", self._pppoe_user)
        pppoe_form.addRow("Password PPPoE:", self._pppoe_pass)
        p3_l.addLayout(pppoe_form)
        btn_pppoe = QPushButton("Aplicar PPPoE en Asus (sin reiniciar WAN aun)")
        btn_pppoe.clicked.connect(self._apply_pppoe)
        p3_l.addWidget(btn_pppoe)
        left_layout.addWidget(p3)

        # ── Paso 4 ──
        p4 = QGroupBox("Paso 4 — Activar Bridge Mode en Movistar  [WiFi: Movistar]")
        p4_l = QVBoxLayout(p4)
        p4_l.addWidget(_wifi_label("Vuelve a la WiFi del Movistar."))
        p4_l.addWidget(QLabel(
            "Esto intentará activar bridge mode via SSH.\n"
            "Si falla, abre http://192.168.1.1 manualmente."
        ))
        btn_bridge = QPushButton("Activar bridge mode en Movistar")
        btn_bridge.clicked.connect(lambda: self._run(
            self._mov_ip, self._mov_user, self._mov_pass,
            "bridge_movistar", "Bridge mode Movistar"
        ))
        p4_l.addWidget(btn_bridge)
        left_layout.addWidget(p4)

        # ── Paso 5 ──
        p5 = QGroupBox("Paso 5 — Activar PPPoE en Asus  [WiFi: Asus]")
        p5_l = QVBoxLayout(p5)
        p5_l.addWidget(_wifi_label("Vuelve a la WiFi del Asus."))
        p5_l.addWidget(QLabel(
            "Espera ~60 s tras el reboot del Movistar antes de continuar."
        ))
        btn_restart = QPushButton("Reiniciar WAN Asus (activa PPPoE)")
        btn_restart.clicked.connect(lambda: self._run(
            self._asus_ip, self._asus_user, self._asus_pass,
            "restart_wan_asus", "Reinicio WAN Asus"
        ))
        btn_verify = QPushButton("Verificar estado PPPoE")
        btn_verify.clicked.connect(lambda: self._run(
            self._asus_ip, self._asus_user, self._asus_pass,
            "check_pppoe", "Verificacion PPPoE"
        ))
        p5_l.addWidget(btn_restart)
        p5_l.addWidget(btn_verify)
        left_layout.addWidget(p5)

        left_layout.addStretch()

        if not PARAMIKO_OK:
            w = QLabel("AVISO: paramiko no instalado\npip install paramiko")
            w.setStyleSheet("color:red; font-weight:bold;")
            left_layout.addWidget(w)

        # ── Panel derecho: output ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Salida SSH:"))
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Consolas", 9))
        btn_clear = QPushButton("Limpiar")
        btn_clear.clicked.connect(self._output.clear)
        right_layout.addWidget(self._output)
        right_layout.addWidget(btn_clear)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([380, 580])

        main = QVBoxLayout(self)
        main.addWidget(splitter)

    # ── Lanzamiento de tareas ─────────────────────────────────────────────────

    def _run(self, ip_field, user_field, pass_field, task, label, extra=None):
        host = ip_field.text().strip()
        user = user_field.text().strip()
        pwd  = pass_field.text()

        if not pwd:
            self._output.append(f"ERROR: introduce la contraseña para {host}.\n")
            return
        if self._worker and self._worker.isRunning():
            self._output.append("Ya hay una operacion SSH en curso...\n")
            return

        self._output.append(f"\n{'─'*60}\n[{label}] → {host}\n")
        self._worker = SSHWorker(host, user, pwd, task, extra)
        self._worker.output.connect(self._output.append)
        self._worker.done.connect(lambda ok, msg: self._done(ok, msg, label))
        self._worker.start()

    def _apply_pppoe(self):
        self._run(
            self._asus_ip, self._asus_user, self._asus_pass,
            "set_pppoe_asus", "Config PPPoE Asus",
            extra={
                "pppoe_user": self._pppoe_user.text(),
                "pppoe_pass": self._pppoe_pass.text(),
            }
        )

    def _run_web_scan(self):
        host = self._mov_ip.text().strip()
        user = self._mov_user.text().strip()
        pwd  = self._mov_pass.text()

        if not pwd:
            self._output.append(f"ERROR: introduce la contraseña Movistar antes de escanear.\n")
            return
        if self._worker and self._worker.isRunning():
            self._output.append("Ya hay una operación en curso...\n")
            return

        self._output.append(f"\n{'─'*60}\n[Escaneo Web Movistar] → http://{host}\n")
        self._worker = WebScrapeWorker(host, user, pwd)
        self._worker.output.connect(self._output.append)
        self._worker.done.connect(lambda ok, msg: self._done(ok, msg, "Escaneo Web Movistar"))
        self._worker.start()

    def _done(self, ok, msg, label):
        status = "OK" if ok else "ERROR"
        self._output.append(f"\n[{status}] {msg}\n")
        self._historial.add_entry(label, f"{status}: {msg}")


# ── helpers de UI ──────────────────────────────────────────────────────────────

def _wifi_label(text):
    lbl = QLabel(f"⬡ {text}")
    lbl.setStyleSheet("color: #1565C0; font-weight: bold;")
    return lbl

def _separator():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    return line
