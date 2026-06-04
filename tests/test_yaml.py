"""Tests for homeassistant/configuration_additions.yaml — syntax and required keys."""
from pathlib import Path

import pytest
import yaml

YAML_FILE = Path(__file__).parent.parent / "homeassistant" / "configuration_additions.yaml"


@pytest.fixture(scope="module")
def ha_config():
    with open(YAML_FILE) as f:
        return yaml.safe_load(f)


def test_yaml_file_exists():
    assert YAML_FILE.exists(), f"Config file missing: {YAML_FILE}"


def test_yaml_parses_without_error(ha_config):
    assert ha_config is not None


def test_homeassistant_section_present(ha_config):
    assert "homeassistant" in ha_config


def test_external_url_present(ha_config):
    assert "external_url" in ha_config["homeassistant"]


def test_internal_url_present(ha_config):
    assert "internal_url" in ha_config["homeassistant"]


def test_external_url_uses_https(ha_config):
    url = ha_config["homeassistant"]["external_url"]
    assert url.startswith("https://"), f"external_url must use HTTPS, got: {url}"


def test_internal_url_uses_http(ha_config):
    url = ha_config["homeassistant"]["internal_url"]
    assert url.startswith("http://"), f"internal_url should use HTTP, got: {url}"


def test_internal_url_contains_ha_port(ha_config):
    url = ha_config["homeassistant"]["internal_url"]
    assert ":8123" in url, f"internal_url should include port 8123, got: {url}"


def test_http_section_present(ha_config):
    assert "http" in ha_config


def test_trusted_proxies_is_a_list(ha_config):
    proxies = ha_config.get("http", {}).get("trusted_proxies")
    assert isinstance(proxies, list), "trusted_proxies must be a list"


def test_trusted_proxies_includes_localhost(ha_config):
    proxies = ha_config["http"]["trusted_proxies"]
    assert "127.0.0.1" in proxies, "localhost (127.0.0.1) must be a trusted proxy"
