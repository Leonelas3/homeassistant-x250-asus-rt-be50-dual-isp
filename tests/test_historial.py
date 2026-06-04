"""Tests for HistorialTab — entry storage, color coding, and clear behaviour."""
import pytest
from tab_historial import HistorialTab


@pytest.fixture
def historial(qtbot):
    tab = HistorialTab()
    qtbot.addWidget(tab)
    return tab


# ── add_entry: data storage ───────────────────────────────────────────────────

def test_add_entry_appends_to_internal_list(historial):
    historial.add_entry("Scan de red", "5 dispositivos encontrados")
    assert len(historial._entries) == 1
    _, action, result = historial._entries[0]
    assert action == "Scan de red"
    assert result == "5 dispositivos encontrados"


def test_add_entry_adds_row_to_list_widget(historial):
    historial.add_entry("Accion", "resultado")
    assert historial._list.count() == 1


def test_multiple_entries_accumulate(historial):
    historial.add_entry("A", "OK")
    historial.add_entry("B", "OK")
    historial.add_entry("C", "neutral")
    assert len(historial._entries) == 3
    assert historial._list.count() == 3


def test_count_label_reflects_entry_count(historial):
    assert historial._lbl_count.text() == "0 entradas"
    historial.add_entry("X", "Y")
    assert historial._lbl_count.text() == "1 entradas"
    historial.add_entry("X", "Y")
    assert historial._lbl_count.text() == "2 entradas"


def test_entry_text_contains_action_and_result(historial):
    historial.add_entry("Subida nat-start", "OK")
    text = historial._list.item(0).text()
    assert "Subida nat-start" in text
    assert "OK" in text


def test_timestamp_is_embedded_in_entry_text(historial):
    historial.add_entry("Algo", "resultado")
    text = historial._list.item(0).text()
    # Timestamp format is [HH:MM:SS]
    assert text.startswith("[")
    assert ":" in text


# ── add_entry: colour coding ──────────────────────────────────────────────────

def test_error_result_gets_red_colour(historial):
    historial.add_entry("SSH", "ERROR: connection refused")
    color = historial._list.item(0).foreground().color().name()
    assert color == "#c0392b"


def test_error_result_case_insensitive(historial):
    historial.add_entry("SSH", "error: timeout")
    color = historial._list.item(0).foreground().color().name()
    assert color == "#c0392b"


def test_ok_result_gets_green_colour(historial):
    historial.add_entry("Operacion", "OK")
    color = historial._list.item(0).foreground().color().name()
    assert color == "#27ae60"


def test_encontrado_result_gets_green_colour(historial):
    historial.add_entry("Scan", "12 dispositivos encontrados")
    color = historial._list.item(0).foreground().color().name()
    assert color == "#27ae60"


def test_neutral_result_is_neither_red_nor_green(historial):
    historial.add_entry("Browse", "visited page")
    color = historial._list.item(0).foreground().color().name()
    assert color not in ("#c0392b", "#27ae60")


# ── _clear ────────────────────────────────────────────────────────────────────

def test_clear_removes_all_entries(historial):
    historial.add_entry("A", "OK")
    historial.add_entry("B", "result")
    historial._clear()
    assert historial._entries == []


def test_clear_empties_list_widget(historial):
    historial.add_entry("A", "OK")
    historial._clear()
    assert historial._list.count() == 0


def test_clear_resets_count_label(historial):
    historial.add_entry("A", "OK")
    historial._clear()
    assert historial._lbl_count.text() == "0 entradas"


def test_clear_on_empty_historial_is_safe(historial):
    historial._clear()  # should not raise
    assert historial._entries == []
    assert historial._lbl_count.text() == "0 entradas"
