# Resumen del Proyecto de Red Doméstica con Dual ISP

## Descripción General

Aplicación PyQt6 integrada con scripts de router para gestionar una red doméstica
con doble conexión a internet. El sistema coordina un router Asus RT-BE50 WiFi 7,
un servidor Home Assistant en Hyper-V y automatización Zigbee.

## Infraestructura de Hardware

- **WAN1:** DiGi fibra simétrica 1 Gbps (Cat 8.1 SFTP al puerto WAN 2.5G del Asus)
- **WAN2:** Vodafone cable 600 Mbps (Cat 8.1 SFTP al puerto LAN3 reconfigurado como WAN2)
- **Router Asus RT-BE50:** 192.168.50.1 — WiFi activo (routers ISP con WiFi apagada)
- **Servidor HA:** HP Pro Mini 400 G9 — Home Assistant OS en Hyper-V → VM: 192.168.50.10 / Host: 192.168.50.20
- **Coordinador Zigbee:** Sonoff Dongle Max conectado al puerto USB del Asus, expuesto vía ser2net en TCP puerto 6638
- **Google TV Streamer:** 192.168.50.30 — conectado a la TV Philips del dormitorio

## Topología de red (doble NAT)

```
Internet
├── DiGi router (192.168.1.1) ──── WAN1 ──→ Asus RT-BE50
└── Vodafone router (192.168.1.1) ─ WAN2 ──→ Asus RT-BE50
                                                ↓ LAN 192.168.50.x
                               HA Hyper-V (.10) · HP Mini (.20) · Google TV (.30)
```

## Lógica de Enrutamiento (scripts `jffs/`)

Los scripts `nat-start` y `wan-event` implementan la política de routing:

- **HA server (192.168.50.10):** forzado a WAN1 (DiGi) tanto como origen como destino
- **Puertos de subida** (21, 22, 990, 2283, 8123): forzados a WAN1 para toda la LAN
- **Puerto 443 (HTTPS):** en round-robin intencionalmente (preservar velocidad de descarga HTTPS)
- **Resto del tráfico:** round-robin entre WAN1 y WAN2

## Port Forwarding (tres capas)

Para que el acceso externo funcione es necesario configurar port forwarding en:
1. **Router DiGi** (puertos 443, 2283, 8123 → IP WAN1 del Asus)
2. **Router Vodafone** (puertos 443, 2283, 8123 → IP WAN2 del Asus)
3. **Asus RT-BE50** (443→HA:8123, 2283→HA:2283, 8123→HA:8123)

## Arquitectura de la Aplicación

Cinco pestañas en PyQt6:
- **Escaner de red:** ping sweep de la subred 192.168.50.0/24
- **Configuracion:** gestión SSH del router (subir scripts, verificar iptables)
- **Historial:** registro con código de colores de todas las acciones
- **Navegador:** web embebida para acceder al admin del router
- **Guia + Mapa:** mapa de red interactivo + guía de configuración por secciones

## Tests

69 tests automatizados (pytest + pytest-qt, plataforma offscreen):
- `tests/test_config.py`: validación de IPs, URLs, puertos, rutas de ficheros
- `tests/test_historial.py`: lógica de colores, almacenamiento y limpieza
- `tests/test_scan_worker.py`: comandos ping, flag stop, emisión de señales
- `tests/test_ssh_worker.py`: despacho de comandos SSH, SFTP, guards de la UI
- `tests/test_yaml.py`: validación del YAML de configuración de HA
