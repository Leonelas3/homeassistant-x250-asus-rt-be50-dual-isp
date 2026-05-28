from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextBrowser, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QPainterPath

import config


# ── Nodos del mapa ───────────────────────────────────────────────────────────

class NetworkNode(QGraphicsItem):
    COLORS = {
        "isp":     "#2980b9",
        "router":  "#27ae60",
        "server":  "#8e44ad",
        "pc":      "#e67e22",
        "internet":"#7f8c8d",
    }

    def __init__(self, label, sublabel="", kind="pc", x=0, y=0, section=None):
        super().__init__()
        self.label    = label
        self.sublabel = sublabel
        self.kind     = kind
        self.section  = section
        self.w, self.h = 170, 65
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

    def center(self):
        return self.pos() + QPointF(self.w / 2, self.h / 2)

    def boundingRect(self):
        return QRectF(0, 0, self.w, self.h)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self.COLORS.get(self.kind, "#555"))
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(140), 2))
        painter.drawRoundedRect(0, 0, self.w, self.h, 12, 12)

        painter.setPen(QPen(QColor("white")))
        f1 = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(f1)
        painter.drawText(QRectF(4, 8, self.w - 8, 26),
                         Qt.AlignmentFlag.AlignCenter, self.label)
        if self.sublabel:
            f2 = QFont("Segoe UI", 8)
            painter.setFont(f2)
            painter.drawText(QRectF(4, 36, self.w - 8, 20),
                             Qt.AlignmentFlag.AlignCenter, self.sublabel)


class Edge(QGraphicsItem):
    def __init__(self, src: NetworkNode, dst: NetworkNode, label="", wired=True):
        super().__init__()
        self.src   = src
        self.dst   = dst
        self.label = label
        self.wired = wired
        self.setZValue(-1)

    def boundingRect(self):
        s, d = self.src.center(), self.dst.center()
        return QRectF(min(s.x(), d.x()) - 30, min(s.y(), d.y()) - 20,
                      abs(s.x() - d.x()) + 60, abs(s.y() - d.y()) + 40)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        s, d = self.src.center(), self.dst.center()
        color = QColor("#2c3e50") if self.wired else QColor("#95a5a6")
        pen = QPen(color, 2, Qt.PenStyle.SolidLine if self.wired else Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(s.toPoint(), d.toPoint())

        if self.label:
            mid = QPointF((s.x() + d.x()) / 2, (s.y() + d.y()) / 2)
            painter.setPen(QPen(color))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(mid + QPointF(4, -4), self.label)


# ── Mapa de red ──────────────────────────────────────────────────────────────

class NetworkMap(QGraphicsView):
    def __init__(self, on_select):
        super().__init__()
        self._on_select = on_select
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setBackgroundBrush(QBrush(QColor("#f0f4f8")))
        self.setMinimumWidth(420)

        scene = QGraphicsScene(self)
        self.setScene(scene)

        # Nodos
        n_internet = NetworkNode("Internet",        kind="internet", x=170, y=10)
        n_o2       = NetworkNode("O2",  "WAN1 — Fibra 1 Gbps",   kind="isp",    x=30,  y=120)
        n_voda     = NetworkNode("Vodafone", "WAN2 — Cable 600 Mbps", kind="isp", x=310, y=120)
        n_router   = NetworkNode("RT-BE50",  "192.168.50.1",      kind="router", x=170, y=240, section=1)
        n_haos     = NetworkNode("ThinkPad X250", "HA · 192.168.50.10", kind="server", x=30,  y=370, section=7)
        n_hp       = NetworkNode("HP Mini 400 G9", "Win11 · 192.168.50.20", kind="pc", x=310, y=370, section=2)

        self._nodes = [n_internet, n_o2, n_voda, n_router, n_haos, n_hp]
        for n in self._nodes:
            scene.addItem(n)

        # Edges
        edges = [
            Edge(n_internet, n_o2,     ""),
            Edge(n_internet, n_voda,   ""),
            Edge(n_o2,       n_router, "WAN1"),
            Edge(n_voda,     n_router, "WAN2", wired=False),
            Edge(n_router,   n_haos,   "LAN · siempre WAN1"),
            Edge(n_router,   n_hp,     "LAN · round-robin"),
        ]
        for e in edges:
            scene.addItem(e)

        scene.setSceneRect(-20, -10, 600, 470)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        item = self.itemAt(event.pos())
        if isinstance(item, NetworkNode) and item.section:
            self._on_select(item.section)


# ── Tab principal ─────────────────────────────────────────────────────────────

SECTION_TITLES = {
    1: "Seccion 1 — Configuracion Dual WAN",
    2: "Seccion 2 — IPs estaticas (DHCP Reservations)",
    3: "Seccion 3 — Port Forwarding para Home Assistant",
    4: "Seccion 4 — Habilitar JFFS y SSH",
    5: "Seccion 5 — Instalar los scripts de routing",
    6: "Seccion 6 — Configurar DDNS / DuckDNS",
    7: "Seccion 7 — Configurar Home Assistant",
    8: "Seccion 8 — Limitaciones conocidas",
}


class GuiaTab(QWidget):
    def __init__(self):
        super().__init__()
        self._sections = self._load_guide()
        self._build_ui()

    def _load_guide(self):
        sections = {}
        try:
            text = config.GUIDE_FILE.read_text(encoding="utf-8")
        except Exception:
            return {i: f"No se pudo leer {config.GUIDE_FILE}" for i in range(1, 9)}

        current = 0
        buf = []
        for line in text.splitlines():
            for n in range(1, 9):
                if line.startswith(f"## Sección {n}"):
                    if current:
                        sections[current] = "\n".join(buf)
                    current = n
                    buf = [line]
                    break
            else:
                if current:
                    buf.append(line)
        if current:
            sections[current] = "\n".join(buf)
        return sections

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Selector de sección
        top = QHBoxLayout()
        top.addWidget(QLabel("Ir a seccion:"))
        self._combo = QComboBox()
        for n, title in SECTION_TITLES.items():
            self._combo.addItem(title, n)
        self._combo.currentIndexChanged.connect(
            lambda: self._show_section(self._combo.currentData()))
        top.addWidget(self._combo)
        top.addStretch()
        layout.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._map = NetworkMap(on_select=self._jump_to)
        splitter.addWidget(self._map)

        right = QWidget()
        r_layout = QVBoxLayout(right)
        r_layout.addWidget(QLabel("Haz clic en un nodo del mapa para ver la seccion correspondiente."))
        self._guide = QTextBrowser()
        self._guide.setOpenExternalLinks(True)
        self._guide.setFont(QFont("Consolas", 9))
        r_layout.addWidget(self._guide)
        splitter.addWidget(right)

        splitter.setSizes([420, 580])
        layout.addWidget(splitter)

        self._show_section(1)

    def _jump_to(self, section):
        idx = list(SECTION_TITLES.keys()).index(section)
        self._combo.setCurrentIndex(idx)
        self._show_section(section)

    def _show_section(self, section):
        text = self._sections.get(section, "Seccion no disponible.")
        self._guide.setPlainText(text)
