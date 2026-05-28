from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel
)
from PyQt6.QtCore import QUrl

import config

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_OK = True
except ImportError:
    WEBENGINE_OK = False


class NavegadorTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Barra de direccion
        bar = QHBoxLayout()
        btn_back    = QPushButton("<")
        btn_forward = QPushButton(">")
        btn_reload  = QPushButton("↺")
        self._url_input = QLineEdit(config.ROUTER_URL)
        self._url_input.returnPressed.connect(self._navigate)
        btn_go = QPushButton("Ir")
        btn_go.clicked.connect(self._navigate)

        for w in [btn_back, btn_forward, btn_reload]:
            w.setFixedWidth(32)
        bar.addWidget(btn_back)
        bar.addWidget(btn_forward)
        bar.addWidget(btn_reload)
        bar.addWidget(self._url_input)
        bar.addWidget(btn_go)

        # Accesos rapidos
        quick = QHBoxLayout()
        quick.addWidget(QLabel("Accesos rapidos:"))
        links = [
            ("Router",     config.ROUTER_URL),
            ("HA local",   config.HA_LOCAL_URL),
            ("HA externo", config.HA_EXTERNAL_URL),
            ("DuckDNS",    "https://www.duckdns.org"),
        ]
        for label, url in links:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, u=url: self._goto(u))
            quick.addWidget(btn)
        quick.addStretch()

        layout.addLayout(bar)
        layout.addLayout(quick)

        if WEBENGINE_OK:
            self._browser = QWebEngineView()
            self._browser.load(QUrl(config.ROUTER_URL))
            btn_back.clicked.connect(self._browser.back)
            btn_forward.clicked.connect(self._browser.forward)
            btn_reload.clicked.connect(self._browser.reload)
            self._browser.urlChanged.connect(
                lambda url: self._url_input.setText(url.toString()))
            layout.addWidget(self._browser)
        else:
            msg = QLabel(
                "PyQt6-WebEngine no esta instalado.\n\n"
                "Instala con:  pip install PyQt6-WebEngine\n\n"
                "Mientras tanto, usa los accesos rapidos para abrir en el navegador del sistema."
            )
            msg.setAlignment(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("color: #666; font-size: 13px;")
            layout.addWidget(msg)
            btn_back.setEnabled(False)
            btn_forward.setEnabled(False)
            btn_reload.setEnabled(False)

            import webbrowser
            for label, url in links:
                pass
            btn_go.clicked.disconnect()
            btn_go.clicked.connect(
                lambda: __import__("webbrowser").open(self._url_input.text()))

    def _navigate(self):
        url = self._url_input.text().strip()
        if not url.startswith("http"):
            url = "http://" + url
        self._goto(url)

    def _goto(self, url):
        self._url_input.setText(url)
        if WEBENGINE_OK:
            self._browser.load(QUrl(url))
        else:
            import webbrowser
            webbrowser.open(url)
