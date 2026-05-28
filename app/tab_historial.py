from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel
)
from PyQt6.QtGui import QColor


class HistorialTab(QWidget):
    def __init__(self):
        super().__init__()
        self._entries = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Registro de acciones realizadas:"))

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        layout.addWidget(self._list)

        bottom = QHBoxLayout()
        btn_clear = QPushButton("Limpiar historial")
        btn_clear.clicked.connect(self._clear)
        self._lbl_count = QLabel("0 entradas")
        bottom.addWidget(btn_clear)
        bottom.addStretch()
        bottom.addWidget(self._lbl_count)
        layout.addLayout(bottom)

    def add_entry(self, action: str, result: str):
        ts = datetime.now().strftime("%H:%M:%S")
        text = f"[{ts}]  {action}  →  {result}"
        self._entries.append((ts, action, result))

        item = QListWidgetItem(text)
        if "ERROR" in result.upper():
            item.setForeground(QColor("#c0392b"))
        elif "OK" in result.upper() or "encontrado" in result.lower():
            item.setForeground(QColor("#27ae60"))
        self._list.addItem(item)
        self._list.scrollToBottom()
        self._lbl_count.setText(f"{len(self._entries)} entradas")

    def _clear(self):
        self._list.clear()
        self._entries.clear()
        self._lbl_count.setText("0 entradas")
