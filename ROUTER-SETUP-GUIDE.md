# Guía de configuración — Asus RT-BE50 Dual WAN + Home Assistant

**Red LAN:** 192.168.50.0/24  
**Router (admin):** http://192.168.50.1  
**WAN1:** O2/Movistar fibra simétrica 1 Gbps — puerto WAN 2.5G  
**WAN2:** Vodafone cable 600/50 Mbps — puerto LAN3 reconfigurado como WAN2  
**HA Server:** ThinkPad X250 con Home Assistant OS → 192.168.50.10  
**PC Windows:** HP Pro Mini 400 G9 → 192.168.50.20  

---

## Sección 1 — Configuración Dual WAN

1. Accede a la interfaz web del router: `http://192.168.50.1`
2. Ve a **WAN → Dual WAN**.
3. Activa **Enable Dual WAN → Yes**.
4. Configura las interfaces:
   - **Primary WAN:** `WAN` (el puerto físico WAN 2.5G) → O2/Movistar
   - **Secondary WAN:** `LAN3` (el puerto que conectas a Vodafone) → Vodafone cable
5. **Dual WAN Mode:** `Load Balance`
6. **Load Balance Algorithm:** `Round Robin`
   - Round Robin distribuye conexiones nuevas alternando entre ambas WANs. En descargas multi-hilo (torrents, gestores de descarga, actualizaciones simultáneas) cada hilo puede ir por una WAN distinta, agregando ancho de banda efectivo.
7. Activa **Network Monitoring** (o "Allow failover") para detectar caídas automáticamente.
   - **WAN1 ping target:** `8.8.8.8` (DNS de Google, muy estable)
   - **WAN2 ping target:** `1.1.1.1` (DNS de Cloudflare)
   - Intervalo recomendado: 5 s, umbral de fallo: 3 pings consecutivos fallidos.
8. Pulsa **Apply**.

> **Nota de firmware:** En algunas versiones de AsusWRT el algoritmo aparece como
> "By Traffic" en lugar de "Round Robin". Son equivalentes para este uso.

---

## Sección 2 — IPs estáticas (DHCP Reservations)

Las IPs de los dispositivos deben ser fijas para que el port forwarding y las
reglas de routing del script funcionen siempre con la misma dirección.

**Antes de empezar: obtén las MAC addresses de cada dispositivo.**

- **ThinkPad X250 (HAOS):**
  En la consola de Home Assistant (Settings → System → Hardware → All Hardware)
  o desde terminal HAOS: `ip link show eth0` — la MAC aparece tras "link/ether".
- **HP Mini (Windows 11):**
  Abre cmd y ejecuta `ipconfig /all`. Busca la sección de tu NIC activa y
  copia el valor "Physical Address" (formato `XX-XX-XX-XX-XX-XX`).

**Dónde configurarlo:** LAN → DHCP Server → pestaña "Manually Assigned IP around
the DHCP list" (o "Static IP list" según versión de firmware).

| Nombre de host    | MAC Address     | IP asignada    | Uso                       |
|-------------------|-----------------|----------------|---------------------------|
| ThinkPad-X250-HA  | _rellenar_      | 192.168.50.10  | Home Assistant OS          |
| HP-Mini-400G9     | _rellenar_      | 192.168.50.20  | Windows 11                 |

Para cada dispositivo: introduce la MAC, la IP deseada, un nombre descriptivo →
**Add** → al terminar pulsa **Apply**.

---

## Sección 3 — Port Forwarding para Home Assistant

El objetivo es que:
- `https://leonelastres.duckdns.org` (sin puerto) funcione → Google Home y webhooks
- `https://leonelastres.duckdns.org:8123` funcione → app móvil de HA y acceso manual

**Dónde configurarlo:** WAN → Virtual Server / Port Forwarding

Añade las siguientes dos reglas:

| Service Name | Protocol | External Port | Internal IP   | Internal Port |
|--------------|----------|---------------|---------------|---------------|
| HA_HTTPS     | TCP      | 443           | 192.168.50.10 | 8123          |
| HA_8123      | TCP      | 8123          | 192.168.50.10 | 8123          |

- **HA_HTTPS** captura el tráfico HTTPS estándar (puerto 443) y lo redirige al
  puerto 8123 de Home Assistant. Así la URL sin puerto funciona.
- **HA_8123** pasa el tráfico del puerto 8123 directamente, manteniendo
  compatibilidad con la app móvil y usuarios que usan `:8123` explícito.

Para cada regla: rellena los campos → **Add** → al terminar pulsa **Apply**.

> **Importante:** estas reglas aplican sobre la IP pública de WAN1 (O2).
> DuckDNS debe apuntar a WAN1, no a WAN2 (ver Sección 6).

---

## Sección 4 — Habilitar JFFS y SSH

JFFS es la partición flash del router donde se almacenan los scripts personalizados.
Sin habilitarla, los scripts se pierden en cada reinicio.

1. Ve a **Administration → System**.
2. **Enable JFFS custom scripts and configs:** `Yes`.
3. **Format JFFS partition at next boot:**
   - Si es la primera vez que activas JFFS: `Yes` (formateará una vez y creará la estructura).
   - En activaciones posteriores: déjalo en `No` para no borrar scripts existentes.
4. **Enable SSH:** `Yes`
5. **SSH Access from:** `LAN only` — nunca expongas SSH a WAN.
6. **SSH Port:** puedes dejarlo en 22 o cambiarlo a otro puerto por seguridad (opcional).
7. Pulsa **Apply** y **reinicia el router**.

Tras el reinicio, verifica que JFFS está activo:
```sh
ssh admin@192.168.50.1 "mount | grep jffs"
# Debe aparecer una línea del tipo: /dev/mtdblock... on /jffs type jffs2
```

---

## Sección 5 — Instalar los scripts de routing

Los scripts están en `network-config/jffs/` en este repositorio.
Ejecútalos desde un equipo en la LAN (Linux, macOS o WSL en Windows).

```sh
# 1. Crea el directorio de scripts en el router (si no existe)
ssh admin@192.168.50.1 "mkdir -p /jffs/scripts"

# 2. Copia los scripts
scp network-config/jffs/nat-start  admin@192.168.50.1:/jffs/scripts/nat-start
scp network-config/jffs/wan-event  admin@192.168.50.1:/jffs/scripts/wan-event

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
- La IP `192.168.50.10` (ThinkPad HA, tanto como origen como destino)
- Puertos 21, 22, 443, 990, 2283, 8123 (TCP y UDP)
- Una regla `CONNMARK restore` en la posición 1 (primera de la cadena)
- Una regla `CONNMARK save` en POSTROUTING

**Verificar que el tráfico del HA server sale por WAN1:**
```sh
# Desde la consola de HAOS (Settings → System → Hardware → Terminal, o SSH a HAOS):
curl -4 https://ifconfig.me
# El resultado debe ser la IP pública de O2 (WAN1).
# Para confirmar cuál es WAN2: compárala con la IP que muestra
# el router en WAN → Internet Status → WAN2.
```

**Ver logs del script:**
```sh
ssh admin@192.168.50.1 "logread | grep -E 'nat-start|wan-event'"
```

**Verificar que wan-event se ejecuta en reconexiones:**
Simula un evento desconectando y reconectando el cable de Vodafone.
En el log del router debes ver líneas de `wan-event` seguidas de `nat-start`.

---

## Sección 6 — Configurar DDNS / DuckDNS

DuckDNS debe apuntar a la IP pública de **WAN1 (O2)** porque el port forwarding
para HA está configurado sobre esa interfaz. Si apunta a WAN2 (Vodafone),
el acceso externo fallará aunque el port forwarding esté bien.

### Opción A — Cliente DDNS integrado en AsusWRT (recomendado)

1. Ve a **WAN → DDNS**.
2. **Enable the DDNS Client:** `Yes`.
3. **Server:** `WWW.DUCKDNS.ORG`.
4. **Host Name:** `leonelastres` (solo la parte antes de `.duckdns.org`).
5. **Username or key:** tu token de DuckDNS.
   - Encuéntralo en [duckdns.org](https://www.duckdns.org) → sección "domains" → columna "token".
6. Verifica que el campo de IP usa WAN1. En AsusWRT el cliente DDNS integrado
   usa la IP de WAN primaria por defecto. Si tu firmware muestra una opción
   "WAN interface for DDNS", selecciona `WAN1` / `wan0`.
7. Pulsa **Apply**.

**Verificar:**
```sh
# Consulta qué IP tiene registrada DuckDNS para tu dominio:
curl -s "https://www.duckdns.org/update?domains=leonelastres&token=TU_TOKEN&verbose=true"
# Compara con la IP que muestra el router en WAN → Internet Status → WAN1 IP.
# Deben coincidir.
```

### Opción B — Script propio en JFFS (si el cliente integrado no funciona bien con dual WAN)

Si el cliente integrado actualiza con la IP de WAN2 en lugar de WAN1, usa este script
que lee la IP de WAN1 explícitamente mediante `nvram`:

```sh
# Crea /jffs/scripts/duckdns.sh en el router:
cat > /jffs/scripts/duckdns.sh << 'EOF'
#!/bin/sh
TOKEN="TU_TOKEN_AQUI"
DOMAIN="leonelastres"
# nvram get wan0_ipaddr devuelve la IP actual de WAN1 en AsusWRT
WAN1_IP=$(nvram get wan0_ipaddr)
if [ -z "$WAN1_IP" ] || [ "$WAN1_IP" = "0.0.0.0" ]; then
    logger -t duckdns "WAN1 sin IP válida, omitiendo actualización."
    exit 1
fi
curl -sk "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip=${WAN1_IP}" \
    -o /tmp/duckdns_result.txt
logger -t duckdns "Actualización enviada. IP=$WAN1_IP Resultado=$(cat /tmp/duckdns_result.txt)"
EOF
chmod +x /jffs/scripts/duckdns.sh
```

Añade una tarea cron que lo ejecute cada 5 minutos. Edita o crea
`/jffs/scripts/services-start` con esta línea:
```sh
cru a duckdns "*/5 * * * * /jffs/scripts/duckdns.sh"
```

---

## Sección 7 — Configurar Home Assistant

### Requisitos previos

- Add-on **File Editor** instalado en HAOS
  (Settings → Add-ons → Add-on Store → busca "File Editor" → Install → Start).
- Certificado TLS válido para `leonelastres.duckdns.org`.
  La forma más sencilla es el add-on **Let's Encrypt** o la integración
  **DuckDNS** integrada en HAOS (Settings → Add-ons → DuckDNS), que gestiona
  el certificado automáticamente.

### Editar configuration.yaml

1. Abre Home Assistant → **Settings → Add-ons → File Editor → Open Web UI**.
2. Navega a `/config/configuration.yaml`.
3. Añade el contenido del archivo `network-config/homeassistant/configuration_additions.yaml`.

   **Si ya tienes un bloque `homeassistant:`**, fusiona las claves dentro del
   bloque existente. No dupliques el bloque: YAML no admite claves raíz repetidas.

   **Si ya tienes un bloque `http:`**, igual: fusiona las claves.

   Resultado esperado en `configuration.yaml`:
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

4. Guarda el archivo.
5. Valida la configuración: **Developer Tools → YAML → Check Configuration**.
   No continúes si hay errores.
6. Reinicia HA: **Settings → System → Restart Home Assistant**.

### Verificar acceso externo

Prueba **desde fuera de tu red** (desactiva el WiFi del móvil y usa datos móviles):

| URL a probar | Esperado |
|---|---|
| `https://leonelastres.duckdns.org` | Carga el login de HA sin errores de certificado |
| `https://leonelastres.duckdns.org:8123` | Igual — misma instancia de HA |

Si ves "Connection refused" en el puerto 443: verifica que la regla HA_HTTPS
esté activa en el router y que DuckDNS apunta a WAN1.

Si ves error de certificado (NET::ERR_CERT_INVALID): el add-on DuckDNS/Let's Encrypt
no ha emitido o renovado el certificado. Revisa su log en Settings → Add-ons → DuckDNS → Log.

### Verificar integración con Google Home

1. Abre la app **Google Home** en el móvil.
2. Ve a **Add → Set up device → Works with Google → Home Assistant**.
3. Inicia sesión en tu instancia de HA.
4. Google Home llamará a `https://leonelastres.duckdns.org/auth/...` (sin puerto).
   Si el port forward 443 funciona correctamente, la autenticación completará sin errores.

> Si Google Home ya estaba vinculado con una URL antigua (con `:8123`), desvincula
> la integración y vuelve a vincularla para que tome la nueva `external_url`.

---

## Sección 8 — Limitaciones conocidas

### Por qué las subidas del HP Mini pueden salir por Vodafone

Esta es la limitación más importante a entender antes de asumir que "todo el
upload va por O2".

**El problema técnico:**
TCP es bidireccional sobre un único socket. Cuando se establece una conexión,
el router asigna un WAN (WAN1 o WAN2) al primer paquete SYN, y **toda la sesión
— tanto los datos que subes como los que bajas — usa ese mismo WAN** durante
toda su vida. No existe en el stack TCP/IP ningún mecanismo para enviar la subida
de una sesión por un camino y la bajada por otro.

En modo Round Robin, el router alterna sesiones entre WANs. Una sesión de
descarga grande asignada a WAN2 (Vodafone) también enviará sus ACKs y cualquier
dato de subida de esa sesión por Vodafone. No hay forma de evitarlo sin hardware
adicional.

**Lo que SÍ consiguen los scripts de esta guía:**

| Dispositivo | Comportamiento garantizado |
|---|---|
| ThinkPad X250 (HA server) | Todo su tráfico — subida y bajada — **siempre por WAN1**. Sin excepción. |
| HP Mini y resto de LAN | Sesiones iniciadas hacia puertos de subida conocidos (22, 21, 990, 2283…) → WAN1. El resto → round robin entre WAN1 y WAN2. |

**Lo que NO se puede garantizar sin hardware adicional:**
- Las subidas del HP Mini en sesiones que no están en la lista de puertos
  conocidos pueden ir por Vodafone si el round robin asigna esa sesión a WAN2.
- No es posible distinguir upload de download dentro de una misma sesión TCP.

### Solución futura: segunda NIC en el HP Mini

Si en el futuro añades una segunda NIC al HP Mini (USB-Ethernet, PCIe, etc.):

1. Conecta esa segunda NIC a un puerto LAN del router diferente.
2. Configura ese puerto en una VLAN o subred separada (ej. 192.168.51.0/24).
3. En el router, crea una regla de routing que fuerce esa subred siempre por WAN1.
4. En Windows, configura la métrica de esa segunda NIC como la preferida para rutas
   específicas (rclone, clientes de backup, etc.), o usa `--bind <IP_segunda_NIC>`
   en herramientas que lo soporten (rclone, wget, curl con `--interface`).

De este modo, el HP Mini tendría una NIC para descarga (load balanced) y otra
para subida (forzada a WAN1), sin ninguna limitación de routing.

---

## Referencia rápida

| Recurso | Valor |
|---|---|
| Router web admin | http://192.168.50.1 |
| HA — acceso local | http://192.168.50.10:8123 |
| HA — acceso externo (sin puerto) | https://leonelastres.duckdns.org |
| HA — acceso externo (con puerto) | https://leonelastres.duckdns.org:8123 |
| nvram WAN1 IP | `nvram get wan0_ipaddr` |
| nvram WAN2 IP | `nvram get wan1_ipaddr` |
| Marca iptables WAN1 | `0x01/0x0f` |
| Marca iptables WAN2 | `0x02/0x0f` |
| Ver reglas mangle | `iptables -t mangle -L PREROUTING -n -v` |
| Ver logs scripts | `logread \| grep -E 'nat-start\|wan-event'` |
