"""Tests for ScanWorker — ping command construction, stop flag, and signal emission."""
from unittest.mock import MagicMock, patch

import pytest
from tab_scanner import ScanWorker
import config


# Helper: run the worker synchronously with subprocess mocked.
# side_effect receives (cmd, **kwargs) and returns a mock result object.
def _run_worker(worker, subprocess_side_effect):
    with patch("subprocess.run", side_effect=subprocess_side_effect):
        worker.run()


# ── Stop flag ─────────────────────────────────────────────────────────────────

def test_stop_before_start_skips_all_pings():
    worker = ScanWorker("192.168.50")
    worker.stop()

    with patch("subprocess.run") as mock_run:
        worker.run()

    mock_run.assert_not_called()


def test_stop_mid_scan_halts_after_current_ip():
    worker = ScanWorker("192.168.50")
    call_count = [0]

    def side_effect(cmd, **kwargs):
        call_count[0] += 1
        worker.stop()  # stop on very first ping
        result = MagicMock()
        result.returncode = 1
        return result

    _run_worker(worker, side_effect)
    assert call_count[0] == 1  # only one ping was executed


# ── Ping command format ───────────────────────────────────────────────────────

def test_linux_ping_uses_c_and_W_flags():
    worker = ScanWorker("192.168.50")
    captured = []

    def side_effect(cmd, **kwargs):
        captured.append(cmd)
        worker.stop()
        result = MagicMock()
        result.returncode = 1
        return result

    with patch("platform.system", return_value="Linux"):
        _run_worker(worker, side_effect)

    assert captured[0] == ["ping", "-c", "1", "-W", "1", "192.168.50.1"]


def test_windows_ping_uses_n_and_w_flags():
    worker = ScanWorker("192.168.50")
    captured = []

    def side_effect(cmd, **kwargs):
        captured.append(cmd)
        worker.stop()
        result = MagicMock()
        result.returncode = 1
        return result

    with patch("platform.system", return_value="Windows"):
        _run_worker(worker, side_effect)

    assert captured[0] == ["ping", "-n", "1", "-w", "400", "192.168.50.1"]


def test_ping_target_ip_is_subnet_dot_i():
    worker = ScanWorker("10.0.0")
    captured = []

    def side_effect(cmd, **kwargs):
        captured.append(cmd)
        worker.stop()
        result = MagicMock()
        result.returncode = 1
        return result

    with patch("platform.system", return_value="Linux"):
        _run_worker(worker, side_effect)

    assert captured[0][-1] == "10.0.0.1"


# ── Signal emission ───────────────────────────────────────────────────────────

def test_device_found_emitted_on_returncode_zero():
    worker = ScanWorker("192.168.50")
    found = []
    worker.device_found.connect(lambda ip, reachable: found.append((ip, reachable)))

    def side_effect(cmd, **kwargs):
        worker.stop()
        result = MagicMock()
        result.returncode = 0
        return result

    with patch("platform.system", return_value="Linux"):
        _run_worker(worker, side_effect)

    assert found == [("192.168.50.1", True)]


def test_device_found_not_emitted_on_nonzero_returncode():
    worker = ScanWorker("192.168.50")
    found = []
    worker.device_found.connect(lambda ip, reachable: found.append((ip, reachable)))

    def side_effect(cmd, **kwargs):
        worker.stop()
        result = MagicMock()
        result.returncode = 1
        return result

    with patch("platform.system", return_value="Linux"):
        _run_worker(worker, side_effect)

    assert found == []


def test_progress_signal_emitted_per_ip():
    worker = ScanWorker("192.168.50")
    progress_values = []
    worker.progress.connect(progress_values.append)

    call_count = [0]

    def side_effect(cmd, **kwargs):
        call_count[0] += 1
        if call_count[0] >= 3:
            worker.stop()
        result = MagicMock()
        result.returncode = 1
        return result

    with patch("platform.system", return_value="Linux"):
        _run_worker(worker, side_effect)

    assert progress_values == [1, 2, 3]


def test_finished_signal_emitted_after_scan():
    worker = ScanWorker("192.168.50")
    worker.stop()  # no pings, goes straight to finished

    finished = []
    worker.finished.connect(lambda: finished.append(True))

    with patch("subprocess.run"):
        worker.run()

    assert finished == [True]


# ── _add_device integration (ScannerTab) ─────────────────────────────────────

def test_add_device_known_ip_fills_all_columns(qtbot):
    from tab_historial import HistorialTab
    from tab_scanner import ScannerTab

    historial = HistorialTab()
    qtbot.addWidget(historial)
    tab = ScannerTab(historial)
    qtbot.addWidget(tab)

    tab._add_device(config.ROUTER_IP, True)

    assert tab._table.rowCount() == 1
    assert tab._table.item(0, 0).text() == config.ROUTER_IP
    assert tab._table.item(0, 1).text() == "Activo"
    assert tab._table.item(0, 2).text() == config.KNOWN_DEVICES[config.ROUTER_IP][0]
    assert tab._table.item(0, 3).text() == config.KNOWN_DEVICES[config.ROUTER_IP][1]


def test_add_device_unknown_ip_shows_desconocido(qtbot):
    from tab_historial import HistorialTab
    from tab_scanner import ScannerTab

    historial = HistorialTab()
    qtbot.addWidget(historial)
    tab = ScannerTab(historial)
    qtbot.addWidget(tab)

    tab._add_device("192.168.50.99", True)

    assert tab._table.item(0, 2).text() == ""
    assert tab._table.item(0, 3).text() == "Desconocido"


def test_scan_done_records_entry_in_historial(qtbot):
    from tab_historial import HistorialTab
    from tab_scanner import ScannerTab

    historial = HistorialTab()
    qtbot.addWidget(historial)
    tab = ScannerTab(historial)
    qtbot.addWidget(tab)

    tab._scan_done()

    assert len(historial._entries) == 1
    _, action, _ = historial._entries[0]
    assert action == "Scan de red"
