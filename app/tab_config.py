import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QTextEdit, QLabel, QCheckBox, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

import config

try:
    import paramiko
    PARAMIKO_OK = True
except ImportError:
    PARAMIKO_OK = False


class SSHWorker(QThread):
    output  = pyqtSignal(str)
    done    = pyqtSignal(bool, str)

    def __init__(self, host, user, password, commands):
        super().__init__()
        self._host     = host
        self._user     = user
        self._password = password
        self._commands = commands  # list of (label, cmd_or_callable)

    def run(self):
        if not PARAMIKO_OK:
            self.done.emit(False, "paramiko no instalado. Ejecuta: pip install paramiko")
            return
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self._host, username=self._user, password=self._password, timeout=10)
            self.output.emit(f"Conectado a {self._host}\n")

            for label, action in self._commands:
                self.output.emit(f"\n>> {label}\n")
                if callable(action):
                    action(ssh, self.output)
                else:
                    _, stdout, stderr = ssh.exec_command(action)
                    out = stdout.read().decode(errors="replace")
                    err = stderr.read().decode(errors="replace")
                    if out:
                        self.output.emit(out)
                    if err:
                        self.output.emit(f"[stderr] {err}")

            ssh.close()
            self.done.emit(True, "Operacion completada.")
        except Exception as e:
            self.done.emit(False, str(e))


def _upload_script(ssh, signal, local_path, remote_path):
    sftp = ssh.open_sftp()
    sftp.put(str(local_path), remote_path)
    sftp.close()
    ssh.exec_command(f"chmod +x {remote_path}")
    signal.emit(f"Subido: {remote_path}\n")


class ConfigTab(QWidget):
    def __init__(self, historial):
        super().__init__()
        self._historial = historial
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # — Panel izquierdo: formulario —
        left = QWidget()
        left_layout = QVBoxLayout(left)

        # Credenciales SSH
        creds = QGroupBox("Credenciales SSH del router")
        form = QFormLayout(creds)
        self._inp_ip   = QLineEdit(config.ROUTER_IP)
        self._inp_user = QLineEdit(config.ROUTER_USER)
        self._inp_pass = QLineEdit()
        self._inp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._inp_pass.setPlaceholderText("Contrasena del router")
        form.addRow("IP router:", self._inp_ip)
        form.addRow("Usuario:",   self._inp_user)
        form.addRow("Contrasena:", self._inp_pass)

        # Acciones de scripts
        scripts = QGroupBox("Scripts de routing (JFFS)")
        s_layout = QVBoxLayout(scripts)
        btn_nat   = QPushButton("Subir nat-start al router")
        btn_wan   = QPushButton("Subir wan-event al router")
        btn_both  = QPushButton("Subir AMBOS scripts")
        btn_check = QPushButton("Verificar reglas iptables")
        btn_jffs  = QPushButton("Verificar estado JFFS")
        btn_nat.clicked.connect(lambda: self._run_ssh([
            ("Crear directorio scripts", "mkdir -p /jffs/scripts"),
            ("Subir nat-start", lambda ssh, sig: _upload_script(
                ssh, sig, config.SCRIPTS_DIR / "nat-start", "/jffs/scripts/nat-start")),
            ("Aplicar nat-start", "/jffs/scripts/nat-start"),
        ], "Subida nat-start"))
        btn_wan.clicked.connect(lambda: self._run_ssh([
            ("Crear directorio scripts", "mkdir -p /jffs/scripts"),
            ("Subir wan-event", lambda ssh, sig: _upload_script(
                ssh, sig, config.SCRIPTS_DIR / "wan-event", "/jffs/scripts/wan-event")),
        ], "Subida wan-event"))
        btn_both.clicked.connect(lambda: self._run_ssh([
            ("Crear directorio scripts", "mkdir -p /jffs/scripts"),
            ("Subir nat-start", lambda ssh, sig: _upload_script(
                ssh, sig, config.SCRIPTS_DIR / "nat-start", "/jffs/scripts/nat-start")),
            ("Subir wan-event", lambda ssh, sig: _upload_script(
                ssh, sig, config.SCRIPTS_DIR / "wan-event", "/jffs/scripts/wan-event")),
            ("Aplicar nat-start", "/jffs/scripts/nat-start"),
        ], "Subida ambos scripts"))
        btn_check.clicked.connect(lambda: self._run_ssh([
            ("Reglas mangle PREROUTING", "iptables -t mangle -L PREROUTING -n -v --line-numbers"),
            ("Reglas mangle POSTROUTING", "iptables -t mangle -L POSTROUTING -n -v --line-numbers"),
        ], "Verificacion iptables"))
        btn_jffs.clicked.connect(lambda: self._run_ssh([
            ("Estado JFFS", "mount | grep jffs"),
            ("Scripts en /jffs/scripts/", "ls -la /jffs/scripts/ 2>/dev/null || echo 'Directorio no existe'"),
        ], "Verificacion JFFS"))
        for btn in [btn_nat, btn_wan, btn_both, btn_check, btn_jffs]:
            s_layout.addWidget(btn)

        # Acciones extra
        extra = QGroupBox("Utilidades")
        e_layout = QVBoxLayout(extra)
        btn_logs = QPushButton("Ver logs nat-start / wan-event")
        btn_ip1  = QPushButton("Ver IP publica WAN1 (O2)")
        btn_ip2  = QPushButton("Ver IP publica WAN2 (Vodafone)")
        btn_logs.clicked.connect(lambda: self._run_ssh([
            ("Logs", "logread | grep -E 'nat-start|wan-event' | tail -30"),
        ], "Logs de scripts"))
        btn_ip1.clicked.connect(lambda: self._run_ssh([
            ("IP WAN1", "nvram get wan0_ipaddr"),
        ], "IP WAN1"))
        btn_ip2.clicked.connect(lambda: self._run_ssh([
            ("IP WAN2", "nvram get wan1_ipaddr"),
        ], "IP WAN2"))
        for btn in [btn_logs, btn_ip1, btn_ip2]:
            e_layout.addWidget(btn)

        left_layout.addWidget(creds)
        left_layout.addWidget(scripts)
        left_layout.addWidget(extra)
        left_layout.addStretch()

        if not PARAMIKO_OK:
            warn = QLabel("AVISO: paramiko no instalado.\nEjecuta: pip install paramiko")
            warn.setStyleSheet("color: red; font-weight: bold;")
            left_layout.addWidget(warn)

        # — Panel derecho: output —
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Salida SSH:"))
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Consolas", 9))
        btn_clear = QPushButton("Limpiar salida")
        btn_clear.clicked.connect(self._output.clear)
        right_layout.addWidget(self._output)
        right_layout.addWidget(btn_clear)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([350, 600])

        main = QVBoxLayout(self)
        main.addWidget(splitter)

    def _run_ssh(self, commands, label):
        host = self._inp_ip.text().strip()
        user = self._inp_user.text().strip()
        pwd  = self._inp_pass.text()

        if not pwd:
            self._output.append("ERROR: introduce la contrasena del router.\n")
            return

        if self._worker and self._worker.isRunning():
            self._output.append("Ya hay una operacion SSH en curso...\n")
            return

        self._output.append(f"--- {label} ---\n")
        self._worker = SSHWorker(host, user, pwd, commands)
        self._worker.output.connect(self._output.append)
        self._worker.done.connect(lambda ok, msg: self._ssh_done(ok, msg, label))
        self._worker.start()

    def _ssh_done(self, ok, msg, label):
        self._output.append(f"\n{'OK' if ok else 'ERROR'}: {msg}\n")
        self._historial.add_entry(label, "OK" if ok else f"ERROR: {msg}")
