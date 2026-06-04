"""Tests for app/config.py — constants, derived URLs, and filesystem paths."""
import re

import config

IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


# ── IP address format ───────────────────────────────────────────────────────

def test_router_ip_is_valid():
    assert IP_RE.match(config.ROUTER_IP), f"ROUTER_IP invalid: {config.ROUTER_IP}"


def test_haos_ip_is_valid():
    assert IP_RE.match(config.HAOS_IP), f"HAOS_IP invalid: {config.HAOS_IP}"


def test_hp_mini_ip_is_valid():
    assert IP_RE.match(config.HP_MINI_IP), f"HP_MINI_IP invalid: {config.HP_MINI_IP}"


def test_google_tv_ip_is_valid():
    assert IP_RE.match(config.GOOGLE_TV_IP), f"GOOGLE_TV_IP invalid: {config.GOOGLE_TV_IP}"


def test_sonoff_ip_is_valid():
    assert IP_RE.match(config.SONOFF_IP), f"SONOFF_IP invalid: {config.SONOFF_IP}"


# ── Derived URLs contain the right IPs/domains ──────────────────────────────

def test_ha_local_url_embeds_haos_ip():
    assert config.HAOS_IP in config.HA_LOCAL_URL


def test_ha_local_url_uses_expected_port():
    assert ":8123" in config.HA_LOCAL_URL


def test_router_url_embeds_router_ip():
    assert config.ROUTER_IP in config.ROUTER_URL


def test_ha_external_url_contains_duckdns_domain():
    assert config.DUCKDNS_DOMAIN in config.HA_EXTERNAL_URL


def test_ha_external_url_uses_https():
    assert config.HA_EXTERNAL_URL.startswith("https://")


# ── KNOWN_DEVICES dictionary ─────────────────────────────────────────────────

def test_known_devices_includes_all_static_ips():
    for ip in (config.ROUTER_IP, config.HAOS_IP, config.HP_MINI_IP):
        assert ip in config.KNOWN_DEVICES, f"{ip} missing from KNOWN_DEVICES"


def test_known_devices_values_are_two_string_tuples():
    for ip, val in config.KNOWN_DEVICES.items():
        assert isinstance(val, tuple), f"KNOWN_DEVICES[{ip}] is not a tuple"
        assert len(val) == 2, f"KNOWN_DEVICES[{ip}] should have 2 elements"
        name, kind = val
        assert isinstance(name, str) and name, f"Empty name for {ip}"
        assert isinstance(kind, str) and kind, f"Empty kind for {ip}"


# ── Upload ports ─────────────────────────────────────────────────────────────

def test_upload_ports_are_all_numeric():
    for port in config.UPLOAD_PORTS.split(","):
        assert port.strip().isdigit(), f"Non-numeric port: {port!r}"


def test_upload_ports_includes_ssh():
    assert "22" in config.UPLOAD_PORTS.split(",")


def test_upload_ports_includes_home_assistant():
    assert "8123" in config.UPLOAD_PORTS.split(",")


# ── Filesystem paths ─────────────────────────────────────────────────────────

def test_scripts_dir_exists():
    assert config.SCRIPTS_DIR.is_dir(), f"SCRIPTS_DIR missing: {config.SCRIPTS_DIR}"


def test_nat_start_script_exists():
    path = config.SCRIPTS_DIR / "nat-start"
    assert path.exists(), f"nat-start not found: {path}"


def test_wan_event_script_exists():
    path = config.SCRIPTS_DIR / "wan-event"
    assert path.exists(), f"wan-event not found: {path}"


def test_guide_file_exists():
    assert config.GUIDE_FILE.exists(), f"Guide file missing: {config.GUIDE_FILE}"
