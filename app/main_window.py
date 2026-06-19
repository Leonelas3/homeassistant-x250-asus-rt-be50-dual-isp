from PyQt6.QtWidgets import QMainWindow, QTabWidget, QStatusBar
from PyQt6.QtCore import Qt

from tab_scanner import ScannerTab
from tab_config import ConfigTab
from tab_historial import HistorialTab
from tab_navegador import NavegadorTab
from tab_guia import GuiaTab
from tab_bridge import BridgeSetupTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Red Dual ISP — Asus RT-BE50 + Home Assistant")
        self.setMinimumSize(1100, 750)

        self.historial = HistorialTab()
        self.scanner   = ScannerTab(self.historial)
        self.config    = ConfigTab(self.historial)
        self.bridge    = BridgeSetupTab(self.historial)
        self.navegador = NavegadorTab()
        self.guia      = GuiaTab()

        tabs = QTabWidget()
        tabs.addTab(self.bridge,    "Migracion Bridge")
        tabs.addTab(self.scanner,   "Escaner de red")
        tabs.addTab(self.config,    "Configuracion")
        tabs.addTab(self.historial, "Historial")
        tabs.addTab(self.navegador, "Navegador")
        tabs.addTab(self.guia,      "Guia + Mapa")

        self.setCentralWidget(tabs)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Listo")
