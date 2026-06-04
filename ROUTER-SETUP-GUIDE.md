# Guía de configuración — Asus RT-BE50 Dual WAN + Home Assistant

**Red LAN:** 192.168.50.0/24  
**Router (admin):** http://192.168.50.1  
**WAN1:** DiGi fibra simétrica 1 Gbps — puerto WAN 2.5G (Cat 8.1 SFTP)  
**WAN2:** Vodafone cable 600 Mbps — puerto LAN3 reconfigurado como WAN2 (Cat 8.1 SFTP)  
**HA Server:** HP Pro Mini 400 G9 — Hyper-V → VM: 192.168.50.10 / Host: 192.168.50.20  
**Google TV Streamer:** Philips dormitorio → 192.168.50.30  

---

## Sección 1 — Port Forwarding en los routers ISP (DiGi y Vodafone)

Esta sección es el **primer paso imprescindible**. La topología usa doble NAT:

```
Internet → Router DiGi ──── WAN1 ──→ Asus RT-BE50 → LAN (192.168.50.x)
Internet → Router Vodafone ─ WAN2 ──→ Asus RT-BE50
```

Sin port forwarding en los routers ISP, el tráfico entrante de internet nunca llega al Asus.

### Paso 1 — Obtén las IPs WAN del Asus RT-BE50

Averigua qué IP asignó cada router ISP al Asus:

```sh
ssh admin@192.168.50.1
nvram get wan0_ipaddr   # IP que el router DiGi asignó al Asus (WAN1)
nvram get wan1_ipaddr   # IP que el router Vodafone asignó al Asus (WAN2)
```

O desde la interfaz web del Asus: **WAN → Internet Status**. Apunta ambas IPs.

### Paso 2 — Port forwarding en el router DiGi

Accede al router DiGi **conectando un cable directamente a uno de sus puertos LAN**
(o WiFi DiGi si la activas temporalmente):

- Admin: habitualmente **http://192.168.1.1** — credenciales en la etiqueta del router
- Sección: Port Forwarding / Virtual Server / NAT (varía según modelo)

Crea tres reglas apuntando a `wan0_ipaddr` (IP WAN1 del Asus):

| Nombre    | Protocolo | Puerto externo | IP destino      | Puerto destino |
|-----------|-----------|----------------|-----------------|----------------|
| HA_HTTPS  | TCP       | 443            | `<wan0_ipaddr>` | 443            |
| HA_Immich | TCP       | 2283           | `<wan0_ipaddr>` | 2283           |
| HA_8123   | TCP       | 8123           | `<wan0_ipaddr>` | 8123           |

Guarda y aplica. DuckDNS apunta a la IP pública de DiGi, así que estos forwards son los críticos para el acceso externo.

### Paso 3 — Port forwarding en el router Vodafone

Accede al router Vodafone directamente:

- Admin: habitualmente **http://192.168.1.1** o **http://192.168.0.1**
- Sección: Port Forwarding / Reenvío de puertos / NAT

Crea las mismas reglas apuntando a `wan1_ipaddr` (IP WAN2 del Asus):

| Nombre    | Protocolo | Puerto externo | IP destino      | Puerto destino |
|-----------|-----------|----------------|-----------------|----------------|
| HA_HTTPS  | TCP       | 443            | `<wan1_ipaddr>` | 443            |
| HA_Immich | TCP       | 2283           | `<wan1_ipaddr>` | 2283           |
| HA_8123   | TCP       | 8123           | `<wan1_ipaddr>` | 8123           |

> **Nota:** El forward en Vodafone sólo sirve si DuckDNS apunta a WAN2 (failover manual) o si añades un segundo dominio para WAN2. El tráfico habitual va por DiGi (WAN1).

---

## Sección 2 — Configuración Dual WAN en el Asus RT-BE50

1. Accede: `http://192.168.50.1`
2. Ve a **WAN → Dual WAN**.
3. Activa **Enable Dual WAN → Yes**.
4. Configura las interfaces:
   - **Primary WAN:** `WAN` (puerto físico WAN 2.5G) → DiGi fibra
   - **Secondary WAN:** `LAN3` → Vodafone cable
5. **Dual WAN Mode:** `Load Balance`
6. **Load Balance Algorithm:** `Round Robin`
   - Round Robin alterna conexiones nuevas entre ambas WANs. En descargas multi-hilo (torrents, actualizaciones simultáneas) cada hilo puede ir por una WAN distinta, agregando ancho de banda efectivo.
7. Activa **Network Monitoring** (failover automático):
   - **WAN1 ping target:** `8.8.8.8`
   - **WAN2 ping target:** `1.1.1.1`
   - Intervalo recomendado: 5 s, umbral de fallo: 3 pings fallidos consecutivos.
8. Pulsa **Apply**.

> **Nota de firmware:** En algunas versiones de AsusWRT el algoritmo aparece como
> "By Traffic" en lugar de "Round Robin". Son equivalentes para este uso.

---

## Sección 3 — IPs estáticas (DHCP Reservations)

Las IPs de los dispositivos deben ser fijas para que el port forwarding y las
reglas de routing del script funcionen siempre con la misma dirección.

**Dónde configurarlo:** LAN → DHCP Server → pestaña "Manually Assigned IP around
the DHCP list" (o "Static IP list" según versión de firmware).

| Nombre de host      | IP a asignar   | Cómo obtener la MAC                                                                         |
|---------------------|----------------|---------------------------------------------------------------------------------------------|
| HA-HyperV-VM        | 192.168.50.10  | Consola HA: Settings → System → Network → adaptador de red → MAC                           |
| HP-Mini-400G9       | 192.168.50.20  | Windows cmd: `ipconfig /all` → Physical Address de la NIC activa                           |
| Google-TV-Streamer  | 192.168.50.30  | Google TV: Settings → Network & internet → Wi-Fi → tu red → ⓘ → MAC address               |

> **Importante — Hyper-V:** La VM de HA debe estar conectada a un **External Virtual Switch**
> (no al Default Switch) para que sea accesible desde la red 192.168.50.x.
> Compruébalo en Hyper-V Manager → Virtual Switch Manager. Si está en el Default Switch
> (172.x.x.x) crea uno nuevo tipo External vinculado a la NIC física del HP Mini.

---

## Sección 4 — Port Forwarding en el Asus RT-BE50 para Home Assistant

**Dónde configurarlo:** WAN → Virtual Server / Port Forwarding

| Service Name | Protocol | External Port | Internal IP   | Internal Port |
|--------------|----------|---------------|---------------|---------------|
| HA_HTTPS     | TCP      | 443           | 192.168.50.10 | 8123          |
| HA_Immich    | TCP      | 2283          | 192.168.50.10 | 2283          |
| HA_8123      | TCP      | 8123          | 192.168.50.10 | 8123          |

- **HA_HTTPS:** captura el tráfico HTTPS estándar (puerto 443) y lo redirige al
  puerto 8123 de HA. La URL `https://leonelastres.duckdns.org` (sin puerto) funciona así.
- **HA_Immich:** expone Immich (gestión de fotos) al exterior para sync móvil.
- **HA_8123:** compatibilidad directa con la app móvil y acceso con `:8123` explícito.

> Estas reglas del Asus actúan en combinación con los forwards de los routers ISP (Sección 1).

---

## Sección 5 — Habilitar JFFS y SSH

JFFS es la partición flash del router donde se almacenan los scripts personalizados.
Sin habilitarla, los scripts se pierden en cada reinicio.

1. Ve a **Administration → System**.
2. **Enable JFFS custom scripts and configs:** `Yes`.
3. **Format JFFS partition at next boot:**
   - Primera vez: `Yes` (formateará una sola vez y creará la estructura).
   - En activaciones posteriores: `No` (para no borrar scripts existentes).
4. **Enable SSH:** `Yes`
5. **SSH Access from:** `LAN only` — nunca expongas SSH a WAN.
6. **SSH Port:** 22 (o cambia por seguridad, opcional).
7. **Apply** y **reinicia el router**.

Tras el reinicio, verifica que JFFS está activo:
```sh
ssh admin@192.168.50.1 "mount | grep jffs"
# Debe aparecer: /dev/mtdblock... on /jffs type jffs2
```

---

## Sección 6 — Instalar los scripts de routing

Los scripts en `jffs/` implementan la política dual-WAN:
- El servidor HA (192.168.50.10) siempre usa WAN1 (DiGi)
- Los uploads (puertos 21, 22, 990, 2283, 8123) van por WAN1
- El resto del tráfico se balancea en round-robin entre WAN1 y WAN2

```sh
# 1. Crea el directorio de scripts en el router (si no existe)
ssh admin@192.168.50.1 "mkdir -p /jffs/scripts"

# 2. Copia los scripts
scp jffs/nat-start  admin@192.168.50.1:/jffs/scripts/nat-start
scp jffs/wan-event  admin@192.168.50.1:/jffs/scripts/wan-event

# 3. Hazlos ejecutables
ssh admin@192.168.50.1 "chmod +x /jffs/scripts/nat-start /jffs/scripts/wan-event"

# 4. Aplica las reglas ahora sin necesidad de reiniciar
ssh admin@192.168.50.1 "/jffs/scripts/nat-start"
```

**Verificar que las reglas de mangle están activas:**
```sh
ssh admin@192.168.50.1 "iptables -t mangle -L PREROUTING -n -v --line-numbers"
```
Debes ver líneas con `MARK set 0x1` (WAN1) asociadas a:
- La IP `192.168.50.10` (HA Hyper-V, tanto como origen como destino)
- Puertos 21, 22, 990, 2283, 8123 (TCP y UDP) — el 443 queda en round-robin intencionalmente
- Una regla `CONNMARK restore` en la posición 1 (primera de la cadena)
- Una regla `CONNMARK save` en POSTROUTING

**Verificar que el tráfico del servidor HA sale por WAN1:**
```sh
# Desde la consola de HA (Settings → System → Hardware → Terminal):
curl -4 https://ifconfig.me
# El resultado debe ser la IP pública de DiGi (WAN1).
```

**Ver logs del script:**
```sh
ssh admin@192.168.50.1 "logread | grep -E 'nat-start|wan-event'"
```

---

## Sección 7 — Configurar DDNS / DuckDNS

DuckDNS debe apuntar a la IP pública de **WAN1 (DiGi)** porque el port forwarding
para HA está configurado sobre esa interfaz.

### Opción A — Cliente DDNS integrado en AsusWRT (recomendado)

1. Ve a **WAN → DDNS**.
2. **Enable the DDNS Client:** `Yes`.
3. **Server:** `WWW.DUCKDNS.ORG`.
4. **Host Name:** `leonelastres` (solo la parte antes de `.duckdns.org`).
5. **Username or key:** tu token de DuckDNS.
   - Encuéntralo en duckdns.org → sección "domains" → columna "token".
6. Si hay opción "WAN interface for DDNS": selecciona `WAN1` / `wan0`.
7. Pulsa **Apply**.

**Verificar:**
```sh
curl -s "https://www.duckdns.org/update?domains=leonelastres&token=TU_TOKEN&verbose=true"
# La IP devuelta debe coincidir con: nvram get wan0_ipaddr
```

### Opción B — Script en JFFS (si el cliente integrado actualiza con IP de WAN2)

```sh
cat > /jffs/scripts/duckdns.sh << 'EOF'
#!/bin/sh
TOKEN="TU_TOKEN_AQUI"
DOMAIN="leonelastres"
WAN1_IP=$(nvram get wan0_ipaddr)
if [ -z "$WAN1_IP" ] || [ "$WAN1_IP" = "0.0.0.0" ]; then
    logger -t duckdns "WAN1 sin IP válida, omitiendo actualización."
    exit 1
fi
curl -sk "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip=${WAN1_IP}" \
    -o /tmp/duckdns_result.txt
logger -t duckdns "IP=$WAN1_IP Resultado=$(cat /tmp/duckdns_result.txt)"
EOF
chmod +x /jffs/scripts/duckdns.sh
```

Añade cron en `/jffs/scripts/services-start`:
```sh
cru a duckdns "*/5 * * * * /jffs/scripts/duckdns.sh"
```

---

## Sección 8 — Home Assistant OS en Hyper-V (HP Pro Mini 400 G9)

### Requisito previo: External Virtual Switch en Hyper-V

La VM de HA debe estar en la misma red 192.168.50.x que el resto de dispositivos.
Si está en el Default Switch de Hyper-V (172.x.x.x), **no será accesible desde la LAN**.

1. Hyper-V Manager → **Virtual Switch Manager** → **New virtual network switch** → **External**
2. Selecciona la NIC física del HP Mini (la conectada al Asus RT-BE50)
3. Nombre: "LAN-Asus" o similar → **Apply**
4. En la VM de HA: **Settings → Network Adapter** → cambia al nuevo External Switch

### Asignar IP fija a la VM

1. Arranca la VM y obtén la MAC: Hyper-V Manager → VM → Settings → Network Adapter → MAC Address
2. En el Asus: LAN → DHCP Server → reserva `192.168.50.10` para esa MAC (Sección 3)
3. Reinicia la VM para que tome la IP reservada

### Configurar configuration.yaml

1. Instala el add-on **File Editor**: Settings → Add-ons → Add-on Store → File Editor → Install → Start
2. Certifcado TLS: instala el add-on **DuckDNS** que gestiona Let's Encrypt automáticamente
3. Navega a `/config/configuration.yaml` y añade el contenido de `homeassistant/configuration_additions.yaml`:

   ```yaml
   homeassistant:
     external_url: "https://leonelastres.duckdns.org"
     internal_url: "http://192.168.50.10:8123"

   http:
     use_x_forwarded_for: true
     trusted_proxies:
       - 127.0.0.1
       - ::1
   ```

4. **Developer Tools → YAML → Check Configuration** → sin errores → **Restart Home Assistant**

### Verificar acceso externo

Prueba **desde fuera de tu red** (desactiva el WiFi del móvil y usa datos móviles):

| URL | Esperado |
|---|---|
| `https://leonelastres.duckdns.org` | Login de HA sin errores de certificado |
| `https://leonelastres.duckdns.org:8123` | Ídem — misma instancia |
| `https://leonelastres.duckdns.org:2283` | Login de Immich |

### Reconfigurar integraciones (Google, Apple, Amazon)

Al cambiar de IP o de máquina, las integraciones cloud deben revincularse:

**Google Home:**
1. App Google Home → Add → Set up device → Works with Google → Home Assistant
2. Si ya estaba vinculado: desvincula primero (Home → más opciones → Unlink) y vuelve a vincular
3. Google Home llama a `https://leonelastres.duckdns.org/auth/...` (sin puerto) → funciona con el forward 443

**Apple Home (HomeKit):**
1. HA: Settings → Integrations → HomeKit → Reconfigure
2. iPhone/iPad: escanea el nuevo código QR que aparece en las notificaciones de HA

**Amazon Alexa:**
1. App Alexa → Skills → "Home Assistant"
2. Si hay error de autenticación: desvincula el skill y vuelve a vincularlo

---

## Sección 9 — Coordinador Zigbee: Sonoff Dongle Max vía red

La VM de Hyper-V no tiene acceso USB directo. El Sonoff Dongle Max, conectado
al puerto USB del Asus RT-BE50, se expone como dispositivo de red usando **ser2net**.
HA se conecta a él vía TCP (`socket://192.168.50.1:6638`).

### Paso 1 — Instalar Entware en el Asus RT-BE50

Entware es el gestor de paquetes para firmware Merlin/AsusWRT. Requiere JFFS activo (Sección 5).

```sh
ssh admin@192.168.50.1

# Instala Entware (una sola vez)
entware-setup.sh
# Si el script no existe, primero inicia sesión y busca la versión de tu router:
# uname -m   → armv7l (RT-BE50)
# wget -O - https://bin.entware.net/armv7sf-k3.10/installer/generic.sh | sh

# Actualiza repositorios e instala ser2net
opkg update
opkg install ser2net
```

### Paso 2 — Verificar dispositivo USB

```sh
# Verifica que el dongle aparece como dispositivo serial
ls -la /dev/ttyUSB*
dmesg | grep -E 'tty|USB' | tail -20
```

El Sonoff Dongle Max aparece habitualmente como `/dev/ttyUSB0`. Si hay otros dispositivos USB
podría ser `/dev/ttyUSB1`.

### Paso 3 — Configurar ser2net

```sh
cat > /opt/etc/ser2net.conf << 'EOF'
# Puerto TCP 6638 → Sonoff Zigbee Dongle Max (coordinador ZHA)
6638:raw:0:/dev/ttyUSB0:115200 8DATABITS NONE 1STOPBIT
EOF
```

Inicia y verifica:
```sh
/opt/etc/init.d/S50ser2net start

# Confirma que está escuchando
netstat -ln | grep 6638
# Debe aparecer: tcp  0  0 0.0.0.0:6638  0.0.0.0:*  LISTEN
```

El script `S50ser2net` arranca automáticamente con el router gracias al sistema init de Entware.

### Paso 4 — Configurar ZHA en Home Assistant

1. Settings → Integrations → Add Integration → **Zigbee Home Automation (ZHA)**
2. **Serial device path:** `socket://192.168.50.1:6638`
3. **Radio type:** EZSP (para Sonoff Dongle Max con firmware EFR32)
4. Completa el asistente

> **Si ZHA ya estaba configurado** con un path USB local: Settings → Integrations → ZHA → Configure
> → cambia el path a `socket://192.168.50.1:6638`.

### Paso 5 — Re-emparejar bombillas Zigbee (si es necesario)

Si el coordinador fue reiniciado o reconfigurado, puede ser necesario re-emparejar:

1. ZHA → **Add Device** (HA entra en modo pairing durante 60 s)
2. En cada bombilla: ciclo rápido de encendido/apagado ×5 o ×6 hasta que parpadee (modo pairing)
3. La bombilla aparecerá automáticamente en ZHA

---

## Sección 10 — Google TV Streamer (Philips TV dormitorio)

### Configuración inicial

1. Conecta el Google TV Streamer al puerto HDMI de la Philips y al enchufe
2. Sigue el asistente inicial con la app **Google Home**
3. Conéctalo a la WiFi del Asus RT-BE50

### IP estática

Asigna `192.168.50.30` por DHCP reservation en el Asus (Sección 3).
MAC: Settings → Network & internet → Wi-Fi → tu red → icono ⓘ → MAC address

### Integración con Home Assistant

#### Google Cast (automática, sin configuración)

HA detecta automáticamente dispositivos Cast en la misma red LAN.
Si no aparece: Settings → Integrations → Add Integration → **Google Cast**

#### Android TV (control avanzado: encender/apagar, lanzar apps)

1. En el Google TV Streamer: **Settings → System → About → Build number** (pulsa 7 veces → activa Developer Options)
2. **Settings → System → Developer options → Network debugging → On** (anota el puerto, normalmente `5555`)
3. En HA: Settings → Integrations → Add Integration → **Android TV**
4. Host: `192.168.50.30`, Puerto: `5555`
5. En el Google TV Streamer aparecerá un diálogo de autorización → acepta

### Control de la TV Philips vía HDMI-CEC

El Google TV Streamer puede controlar la Philips mediante CEC (encendido, volumen,
cambio de entrada). Desde HA, controlando el Google TV Streamer controlas también la TV.

Si la Philips es un modelo Android TV: puedes añadir también la propia TV como
entidad separada con la integración **Android TV** o **Philips Android TV** usando la IP de la TV.

---

## Sección 11 — Limitaciones conocidas

### Por qué las subidas del HP Mini pueden salir por Vodafone

TCP es bidireccional sobre un único socket. Cuando se establece una conexión,
el router asigna un WAN al primer paquete SYN, y **toda la sesión — subida y bajada —
usa ese mismo WAN**. No existe en TCP ningún mecanismo para enviar la subida
de una sesión por un camino y la bajada por otro.

En modo Round Robin, el router alterna sesiones entre WANs. Una sesión de
descarga grande asignada a WAN2 (Vodafone) también enviará sus ACKs y datos de subida
de esa sesión por Vodafone.

**Comportamiento garantizado por los scripts:**

| Dispositivo / Tráfico | Comportamiento |
|---|---|
| Servidor HA (192.168.50.10 — Hyper-V) | **Todo su tráfico siempre por WAN1 (DiGi).** Sin excepción. |
| HP Mini y resto de LAN — puertos 21, 22, 990, 2283, 8123 | → WAN1 (DiGi) |
| HP Mini y resto de LAN — puerto 443 (HTTPS) | → Round robin (para preservar velocidad de descarga HTTPS) |
| HP Mini y resto de LAN — resto del tráfico | → Round robin entre WAN1 y WAN2 |

**Lo que no se puede garantizar sin hardware adicional:**
- Subidas en sesiones que no estén en la lista de puertos conocidos pueden ir por Vodafone
- No es posible distinguir upload de download dentro de una misma sesión TCP

### DiGi simétrica vs Vodafone asimétrica

DiGi ofrece 1 Gbps simétrico. Vodafone ofrece 600 Mbps de bajada pero con subida limitada.
En modo round-robin, los uploads que caigan en WAN2 estarán limitados a la subida de Vodafone.
Por eso es importante que los puertos de subida (SSH, Immich, HA) estén en la lista `UPLOAD_PORTS`
del script `nat-start` para que siempre vayan por DiGi (WAN1).

### Solución futura: segunda NIC en el HP Mini

Si añades una segunda NIC al HP Mini (USB-Ethernet, PCIe, etc.):

1. Conecta esa NIC a un puerto LAN del Asus configurado en una VLAN separada (ej. 192.168.51.0/24)
2. En el Asus: crea una regla que fuerce esa subred siempre por WAN1
3. En Windows: configura la métrica o usa `--bind <IP>` en herramientas como rclone, wget, curl

El HP Mini tendría así una NIC para descargas (round-robin) y otra para subidas (WAN1 forzado).

---

## Referencia rápida

| Recurso | Valor |
|---|---|
| Router web admin | http://192.168.50.1 |
| HA — acceso local | http://192.168.50.10:8123 |
| Immich — acceso local | http://192.168.50.10:2283 |
| HA — acceso externo | https://leonelastres.duckdns.org |
| Immich — acceso externo | https://leonelastres.duckdns.org:2283 |
| Google TV Streamer | 192.168.50.30 |
| Sonoff Dongle Max (Zigbee) | socket://192.168.50.1:6638 |
| nvram WAN1 IP (DiGi) | `nvram get wan0_ipaddr` |
| nvram WAN2 IP (Vodafone) | `nvram get wan1_ipaddr` |
| Marca iptables WAN1 | `0x01/0x0f` |
| Marca iptables WAN2 | `0x02/0x0f` |
| Ver reglas mangle | `iptables -t mangle -L PREROUTING -n -v` |
| Ver logs scripts | `logread \| grep -E 'nat-start\|wan-event'` |
