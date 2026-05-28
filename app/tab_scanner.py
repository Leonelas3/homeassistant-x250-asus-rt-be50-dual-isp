import subprocess
import platform
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QProgressBar, QLabel, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

import config


class ScanWorker(QThread):
    device_found = pyqtSignal(str, bool)
    progress     = pyqtSignal(int)
    finished     = pyqtSignal()

    def __init__(self, subnet):
        super().__init__()
        self._subnet = subnet
        self._stop = False

    def run(self):
        is_windows = platform.system() == "Windows"
        for i in range(1, 255):
            if self._stop:
                break
            ip = f"{self._subnet}.{i}"
            if is_windows:
                cmd = ["ping", "-n", "1", "-w", "400", ip]
            else:
                cmd = ["ping", "-c", "1", "-W", "1", ip]
            result = subprocess.run(cmd, capture_output=True)
            reachable = result.returncode == 0
            if reachable:
                self.device_found.emit(ip, True)
            self.progress.emit(i)
        self.finished.emit()

    def stop(self):
        self._stop = True


class ScannerTab(QWidget):
    def __init__(self, historial):
        super().__init__()
        self._historial = historial
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self._btn_scan = QPushButton("Escanear red (192.168.50.0/24)")
        self._btn_scan.clicked.connect(self._toggle_scan)
        self._lbl_status = QLabel("Sin escanear")
        top.addWidget(self._btn_scan)
        top.addWidget(self._lbl_status)
        top.addStretch()

        self._progress = QProgressBar()
        self._progress.setRange(0, 253)
        self._progress.setValue(0)
        self._progress.setVisible(False)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["IP", "Estado", "Dispositivo conocido", "Tipo"])
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)

        layout.addLayout(top)
        layout.addWidget(self._progress)
        layout.addWidget(self._table)

    def _toggle_scan(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._btn_scan.setText("Escanear red (192.168.50.0/24)")
            return

        self._table.setRowCount(0)
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._btn_scan.setText("Detener escaneo")
        self._lbl_status.setText("Escaneando...")

        self._worker = ScanWorker(config.LAN_SUBNET)
        self._worker.device_found.connect(self._add_device)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._scan_done)
        self._worker.start()

    def _add_device(self, ip, reachable):
        row = self._table.rowCount()
        self._table.insertRow(row)

        known = config.KNOWN_DEVICES.get(ip)
        nombre = known[0] if known else ""
        tipo   = known[1] if known else "Desconocido"

        items = [
            QTableWidgetItem(ip),
            QTableWidgetItem("Activo" if reachable else "Sin respuesta"),
            QTableWidgetItem(nombre),
            QTableWidgetItem(tipo),
        ]
        for col, item in enumerate(items):
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if known:
                item.setBackground(QColor("#d4edda"))
            self._table.setItem(row, col, item)

    def _scan_done(self):
        count = self._table.rowCount()
        self._lbl_status.setText(f"Scan completo — {count} dispositivos encontrados")
        self._btn_scan.setText("Escanear red (192.168.50.0/24)")
        self._progress.setVisible(False)
        self._historial.add_entry("Scan de red", f"{count} dispositivos encontrados")
