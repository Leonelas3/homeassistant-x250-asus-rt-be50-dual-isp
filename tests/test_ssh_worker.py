"""Tests for SSHWorker and _upload_script — SSH command dispatch and error paths."""
from unittest.mock import MagicMock, patch, call

import pytest
import tab_config
from tab_config import SSHWorker, _upload_script


# ── SSHWorker: no-paramiko path ───────────────────────────────────────────────

def test_missing_paramiko_emits_done_false():
    worker = SSHWorker("192.168.50.1", "admin", "pass", [])
    done_calls = []
    worker.done.connect(lambda ok, msg: done_calls.append((ok, msg)))

    with patch.object(tab_config, "PARAMIKO_OK", False):
        worker.run()

    assert len(done_calls) == 1
    ok, msg = done_calls[0]
    assert ok is False
    assert "paramiko" in msg.lower()


# ── SSHWorker: connection failure ─────────────────────────────────────────────

def test_ssh_connect_exception_emits_done_false():
    worker = SSHWorker("192.168.50.1", "admin", "wrongpass", [])
    done_calls = []
    worker.done.connect(lambda ok, msg: done_calls.append((ok, msg)))

    mock_client = MagicMock()
    mock_client.connect.side_effect = Exception("Authentication failed")

    with patch.object(tab_config, "PARAMIKO_OK", True), \
         patch("paramiko.SSHClient", return_value=mock_client):
        worker.run()

    assert len(done_calls) == 1
    ok, msg = done_calls[0]
    assert ok is False
    assert "Authentication failed" in msg


# ── SSHWorker: string commands ────────────────────────────────────────────────

def test_string_command_is_passed_to_exec_command():
    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b"output text"
    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b""
    mock_client = MagicMock()
    mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

    worker = SSHWorker("192.168.50.1", "admin", "pass", [
        ("Check JFFS", "ls /jffs/scripts"),
    ])
    output_lines = []
    done_calls = []
    worker.output.connect(output_lines.append)
    worker.done.connect(lambda ok, msg: done_calls.append((ok, msg)))

    with patch.object(tab_config, "PARAMIKO_OK", True), \
         patch("paramiko.SSHClient", return_value=mock_client):
        worker.run()

    mock_client.exec_command.assert_called_once_with("ls /jffs/scripts")
    assert any("output text" in line for line in output_lines)
    assert done_calls[0][0] is True


def test_stderr_output_is_prefixed(qtbot):
    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b""
    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b"command not found"
    mock_client = MagicMock()
    mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

    worker = SSHWorker("192.168.50.1", "admin", "pass", [
        ("Bad cmd", "bogus"),
    ])
    output_lines = []
    worker.output.connect(output_lines.append)

    with patch.object(tab_config, "PARAMIKO_OK", True), \
         patch("paramiko.SSHClient", return_value=mock_client):
        worker.run()

    assert any("[stderr]" in line for line in output_lines)


# ── SSHWorker: callable commands ──────────────────────────────────────────────

def test_callable_command_receives_ssh_client_and_signal():
    mock_client = MagicMock()
    callable_action = MagicMock()

    worker = SSHWorker("192.168.50.1", "admin", "pass", [
        ("Upload", callable_action),
    ])

    with patch.object(tab_config, "PARAMIKO_OK", True), \
         patch("paramiko.SSHClient", return_value=mock_client):
        worker.run()

    callable_action.assert_called_once()
    ssh_arg, signal_arg = callable_action.call_args[0]
    assert ssh_arg is mock_client
    # Verify the second argument is a Qt signal (has an emit method)
    assert hasattr(signal_arg, "emit")


def test_string_and_callable_commands_are_both_executed():
    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b""
    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b""
    mock_client = MagicMock()
    mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)
    callable_action = MagicMock()

    worker = SSHWorker("192.168.50.1", "admin", "pass", [
        ("Run cmd", "ls /"),
        ("Upload", callable_action),
    ])

    with patch.object(tab_config, "PARAMIKO_OK", True), \
         patch("paramiko.SSHClient", return_value=mock_client):
        worker.run()

    mock_client.exec_command.assert_called_once_with("ls /")
    callable_action.assert_called_once()


# ── SSHWorker: successful completion ─────────────────────────────────────────

def test_successful_run_emits_done_true():
    mock_client = MagicMock()

    worker = SSHWorker("192.168.50.1", "admin", "pass", [])
    done_calls = []
    worker.done.connect(lambda ok, msg: done_calls.append((ok, msg)))

    with patch.object(tab_config, "PARAMIKO_OK", True), \
         patch("paramiko.SSHClient", return_value=mock_client):
        worker.run()

    assert done_calls[0][0] is True


def test_ssh_connection_is_closed_after_commands():
    mock_client = MagicMock()

    worker = SSHWorker("192.168.50.1", "admin", "pass", [])

    with patch.object(tab_config, "PARAMIKO_OK", True), \
         patch("paramiko.SSHClient", return_value=mock_client):
        worker.run()

    mock_client.close.assert_called_once()


# ── _upload_script ────────────────────────────────────────────────────────────

def test_upload_script_calls_sftp_put():
    mock_ssh = MagicMock()
    mock_sftp = MagicMock()
    mock_ssh.open_sftp.return_value = mock_sftp
    mock_signal = MagicMock()

    _upload_script(mock_ssh, mock_signal, "/local/nat-start", "/jffs/scripts/nat-start")

    mock_sftp.put.assert_called_once_with("/local/nat-start", "/jffs/scripts/nat-start")


def test_upload_script_closes_sftp():
    mock_ssh = MagicMock()
    mock_sftp = MagicMock()
    mock_ssh.open_sftp.return_value = mock_sftp
    mock_signal = MagicMock()

    _upload_script(mock_ssh, mock_signal, "/local/nat-start", "/jffs/scripts/nat-start")

    mock_sftp.close.assert_called_once()


def test_upload_script_sets_executable_permission():
    mock_ssh = MagicMock()
    mock_sftp = MagicMock()
    mock_ssh.open_sftp.return_value = mock_sftp
    mock_signal = MagicMock()

    _upload_script(mock_ssh, mock_signal, "/local/nat-start", "/jffs/scripts/nat-start")

    mock_ssh.exec_command.assert_called_once_with("chmod +x /jffs/scripts/nat-start")


def test_upload_script_emits_confirmation_signal():
    mock_ssh = MagicMock()
    mock_sftp = MagicMock()
    mock_ssh.open_sftp.return_value = mock_sftp
    mock_signal = MagicMock()

    _upload_script(mock_ssh, mock_signal, "/local/nat-start", "/jffs/scripts/nat-start")

    mock_signal.emit.assert_called_once()
    emitted_text = mock_signal.emit.call_args[0][0]
    assert "/jffs/scripts/nat-start" in emitted_text


# ── ConfigTab: guard conditions ───────────────────────────────────────────────

def test_run_ssh_rejects_empty_password(qtbot):
    from tab_historial import HistorialTab
    from tab_config import ConfigTab

    historial = HistorialTab()
    qtbot.addWidget(historial)
    tab = ConfigTab(historial)
    qtbot.addWidget(tab)

    tab._inp_pass.setText("")  # no password
    tab._run_ssh([("cmd", "ls")], "Test")

    # No worker should have been created
    assert tab._worker is None
    assert "ERROR" in tab._output.toPlainText()


def test_run_ssh_rejects_concurrent_operation(qtbot):
    from tab_historial import HistorialTab
    from tab_config import ConfigTab

    historial = HistorialTab()
    qtbot.addWidget(historial)
    tab = ConfigTab(historial)
    qtbot.addWidget(tab)

    tab._inp_pass.setText("somepass")

    # Simulate a running worker
    fake_worker = MagicMock()
    fake_worker.isRunning.return_value = True
    tab._worker = fake_worker

    tab._run_ssh([("cmd", "ls")], "Test")

    assert "en curso" in tab._output.toPlainText()
