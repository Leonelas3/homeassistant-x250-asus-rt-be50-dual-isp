# Resumen del Proyecto de Red Doméstica con Dual ISP

## Descripción General

Se trata de una aplicación PyQt6 integrada con scripts de router para gestionar una red doméstica en Zamora equipada con doble conexión a Internet. El sistema coordina un router Asus RT-BE50 WiFi 7, un servidor Home Assistant en ThinkPad X250 y automatización Zigbee.

## Infraestructura de Hardware

La red utiliza dos proveedores: O2 (fibra 1 Gbps simétrica) como WAN1 y Vodafone (cable 600/50 Mbps asimétrico) como WAN2. El coordinador Zigbee es un Sonoff Dongle Max conectado por Ethernet al puerto 6638, liberando puertos USB del servidor.

## Lógica de Enrutamiento

Los scripts `nat-start` y `wan-event` en el directorio `jffs/` del router implementan la estrategia de routing:

- Puertos específicos (21, 22, 990, 2283, 8123) se fuerzan hacia O2 (WAN1)
- ThinkPad X250 (192.168.50.10) forzado a WAN1 tanto como origen como destino
- El puerto 443 se excluye intencionalmente para preservar el balanceo de descargas HTTPS

## Arquitectura de la Aplicación

La aplicación modular divide funcionalidades en cinco pestañas: escaneo de dispositivos, configuración por equipo, historial con deshacer, navegador web integrado y guía interactiva con mapa de red arrastrable.

## Estado de Implementación

La mayoría de componentes están completos excepto la instalación de Vodafone, que está pendiente tras el cambio de domicilio.
