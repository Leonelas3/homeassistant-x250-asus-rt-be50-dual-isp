# Log de Ejecución — Red Dual ISP / Bridge Migration

> Actualizado automáticamente por Claude Code cada sesión.  
> Leer este archivo para retomar el trabajo en cualquier momento.

---

## Sesión activa: 2026-05-30 (continuación)

### Estado actual del proyecto

| Componente | Estado |
|---|---|
| Tab "Migracion Bridge" | CREADA — `app/tab_bridge.py` |
| `main_window.py` | ACTUALIZADO — tab Bridge es el primero |
| WebScrapeWorker | **NUEVO** — escaneo HTTP directo de la web del Movistar |
| `requirements.txt` | ACTUALIZADO — añadidos `requests` y `beautifulsoup4` |
| Paso 1 — Backup Asus nvram | PENDIENTE — usuario aún no lo ejecutó |
| Paso 2 — Extraer PPPoE Movistar | SSH falló (nvram inaccesible en HGU) — usar botón web |
| Paso 3 — Configurar PPPoE Asus | PENDIENTE — necesita credenciales PPPoE |
| Paso 4 — Bridge mode Movistar | PENDIENTE — SSH probablemente fallará en HGU |
| Paso 5 — Reiniciar WAN Asus | PENDIENTE |

---

## Acciones realizadas en esta sesión

### 2026-05-29 — Sesión anterior (ID: 8388d4a4)
- Creado `app/tab_bridge.py` con los 5 pasos guiados
- Modificado `app/main_window.py` para añadir el tab Bridge primero
- Creado `LOG_EJECUCION.md`

### 2026-05-29 — Segunda sesión (continuación)
- El usuario ejecutó la app y probó el Paso 2 (SSH a Movistar 192.168.1.1)
- SSH conectó correctamente con las credenciales del router (etiqueta)
- `nvram` no es accesible en el GPT-2742GX4X5v6 (firmware propietario Askey/Movistar)
- No se encontraron credenciales PPPoE via SSH (esperado para este modelo)
- **AÑADIDO** `WebScrapeWorker` en `tab_bridge.py`:
  - Hace login HTTP al router (Basic Auth + varios formularios POST)
  - Descarga ~20 URLs conocidas de Movistar HGU / ZTE / Askey
  - Guarda cada página HTML en `backups/movistar_web_*.html`
  - Extrae credenciales PPPoE con 8 patrones regex
  - Resultado en `backups/movistar_pppoe_web_TIMESTAMP.txt`
- **AÑADIDO** botón "Escanear interfaz web → extraer PPPoE [RECOMENDADO]" en Paso 2
- `requests` y `beautifulsoup4` instalados y añadidos a `requirements.txt`
- **ANALIZADO** el JS del router: mecanismo de login es `MD5(password + ":" + sid)` donde `sid` está embebido en el HTML de `/`
- **ACTUALIZADO** `WebScrapeWorker._do_login`: ahora usa el mecanismo real (extrae SID + MD5)
- **ACTUALIZADO** `WebScrapeWorker._PAGES`: ahora usa las rutas CGI reales del router (descubiertas en `main.js`)
  - `/cgi-bin/mhs/returnInternetJSON.asp` — JSON con usuario/clave PPPoE ← objetivo principal
  - `/cgi-bin/backupRestoreSetting.cgi` — backup completo
  - `/cgi-bin/deviceinfo.cgi`, `/cgi-bin/sysinfo.cgi` — estado del router
- **CREADO** `test_login_movistar.py` — script standalone que prueba el login y muestra el JSON de WAN

---

## Descripción del WebScrapeWorker (Paso 2 — método web)

Rutas que intenta descargar del router Movistar:
- `/`, `/wan.html`, `/internet.html`, `/status.html`, `/advanced.html`
- `/html/internet/index.html`, `/html/wan/index.html`
- `/cgi-bin/gui.cgi?file=wan.html` y variantes
- `/getpage.gch`, `/goform/WanInfo`, `/api/v1/wan`

Patrones PPPoE que busca en el HTML:
- `pppoe_username`, `wan_username`, `value="adslppp..."`, `adslppp@...`
- JSON keys: `pppoeUsername`, `wanUsername`

---

## ✅ CREDENCIALES PPPoE MOVISTAR — CONFIRMADAS

| Campo | Valor |
|---|---|
| **Usuario PPPoE** | `adslppp@telefonicanetpa` |
| **Contraseña PPPoE** | `adslppp` |
| **Encapsulación** | PPPoE VC-Mux |
| **MTU/MRU** | 1492 |
| **IP pública actual** | 95.123.129.163 |

Fuente: `/etc/isp0.conf` y `/etc/ppp/options_nas0` via SSH (usuario `1234`, contraseña `Habana1211`)
Backup guardado en: `backups/movistar_pppoe_20260530_012206.txt`

---

## Credenciales de acceso al router Movistar (NO guardar en memoria)

| Acceso | Usuario | Contraseña |
|---|---|---|
| Web básica (http://192.168.1.1/cgi-bin/logIn_mhs.cgi) | *(solo contraseña)* | `habana1211.` **(con punto al final)** |
| Web avanzada (/cgi-bin/login_advance.cgi) | `1234` | `habana1211` (sin punto) |
| SSH (puerto 22) | `1234` | desconocida post-cambio — SSH falla con habana1211/habana1211. |

---

## Sesión 2026-05-30 — Problema activo: sin internet tras activar monopuerto

### Situación
- Movistar HGU puesto en modo monopuerto/bridge ✓
- Asus RT-BE50 con PPPoE configurado (credenciales correctas) ✓
- **Sin internet** — PPPoE no establece sesión

### Causa probable: VLAN 6
Movistar España FTTH etiqueta el tráfico de internet en VLAN 6 (802.1q).
En modo monopuerto el HGU puede pasar los frames CON la etiqueta puesta.
El Asus necesita usar la interfaz `eth0.6` como WAN, no `eth0`.

### Comandos diagnóstico (SSH Asus — leonel / as3Las3.*)
```bash
nvram get wan0_state_t        # 2 = conectado, 0/1/3 = fallo
nvram get wan0_ifname         # debe ser eth0.6 para VLAN6
nvram get wan0_pppoe_username # verificar credenciales activas
cat /tmp/pppoe.log 2>/dev/null
```

### Fix — forzar VLAN 6 en WAN
```bash
nvram set wan0_ifname=eth0.6
nvram set wan0_gw_ifname=eth0.6
nvram commit
service restart_wan
```

### Acciones realizadas
- Accedido a `http://192.168.50.1` → LAN → pestaña **IPTV**
- ISP Profile: Manual, **Internet VID: 6**, Internet Priority: 0
- El firmware avisó que forzaría el uso del puerto WAN físico 2.5G (desactiva el LAN-como-WAN2 de Vodafone)
- Usuario confirmó y aceptó → router reiniciando
- Nota: RT-BE50 tiene 1x WAN 2.5G físico + 3x LAN (uno era WAN2/Vodafone en multi-WAN)
- Cable Movistar debe estar en el **puerto WAN físico 2.5G**
- WiFi aún no aparece (reinicio en curso, normal hasta 5 min)

### Diagnóstico adicional (revisión backups 2026-05-30)

**Problema 1 — MAC address del HGU Movistar**
- MAC WAN del HGU: `44:3B:14:51:4A:89` (extraída de `isp0.conf`)
- El BRAS de Movistar/O2 puede tener cacheada esta MAC y rechazar PPPoE del Asus (MAC diferente)
- Fix: clonar MAC en Asus → WAN → Internet Connection → "Special Requirement for ISP" → MAC = `44:3B:14:51:4A:89`

**Problema 2 — VLAN 6 probablemente no corresponde**
- `multipuesto.cgi` backup confirma que en modo Monopuesto el HGU usa `1483 Bridged Only LLC` (bridge puro)
- El HGU probablemente QUITA la etiqueta VLAN 6 antes de entregar al puerto LAN
- Si el Asus también usa VLAN 6, los frames quedan mal encapsulados
- Fix: LAN → IPTV → Internet VID = 0 (sin VLAN)

### Resultado final sesión 2026-05-30

**PPPoE directo (monopuesto) NO funcionó** — PADO timeout en todos los intentos.
Diagnóstico: la OLT de O2 no pasa frames PPPoE discovery al dispositivo en bridge.
Para PPPoE directo hay que llamar a O2 y pedir "modo bridge en la línea FTTH".

**Solución activa — doble NAT:**
- Movistar vuelto a Multipuesto (router normal, hace PPPoE con O2)
- Asus WAN en Automatic IP (DHCP) → recibe 192.168.1.102 del Movistar
- **Internet funcionando** — ping 8.8.8.8 → 13ms, 0% pérdida, gateway 192.168.50.1 ✓
- Toda la casa en LAN 192.168.50.x del Asus

### Estado
- [x] VLAN 6, MAC clone, PAP — probados, todos fallaron (PADO timeout)
- [x] Movistar vuelto a Multipuesto
- [x] Asus WAN = Automatic IP / DHCP → 192.168.1.102
- [x] **Internet funcionando en toda la casa**
- [ ] DMZ en Movistar apuntando a 192.168.1.102 → eliminar doble NAT para acceso externo
- [ ] Llamar a O2 para bridge mode real en la línea (largo plazo)
- [ ] Reconfigurar WAN2 Vodafone (multi-WAN)

---

## Siguiente sesión — Pasos pendientes

1. **Ejecutar la app**: `run.bat` o `python app\main.py`
2. **Paso 1**: Conectado a WiFi Asus → botón "Backup nvram Asus"
3. **Paso 2**: YA COMPLETADO — credenciales extraídas
4. **Paso 3**: ✅ COMPLETADO — PPPoE configurado en Asus via SSH
   - `wan0_proto = pppoe`
   - `wan0_pppoe_username = adslppp@telefonicanetpa`
   - `wan0_pppoe_passwd = adslppp`
   - `wan0_pppoe_mtu / mru = 1492`
   - SSH Asus: usuario `leonel`, contraseña `as3Las3.*`, puerto 22
4b. **Backup completado** (2026-05-30): `backups/movistar_romfile_20260530_021310.cfg` (164KB) — restaurable desde web básica → Mantenimiento → Backup/Restore
5. **Paso 4**: Cambiar a WiFi Movistar → activar bridge mode
   - ⚠️ SSH (`nvram set`) no funcionará — firmware propietario
   - Ruta web manual: http://192.168.1.1/cgi-bin/Aviso.cgi → Aceptar → `indexmain.cgi` → Red → Banda ancha → Editar interfaz Internet → Modo: Puente
   - O bien llamar a Movistar para activar modo bridge (alternativa más fiable)
6. **Paso 5**: Volver a WiFi Asus → reiniciar WAN → verificar PPPoE activo

---

## Cómo ejecutar la app

```
Opción A (doble clic):
  run.bat

Opción B (terminal):
  cd "C:\Users\leone\OneDrive\Documentos\GitHub\homeassistant-x250-asus-rt-be50-dual-isp"
  python -m pip install -r requirements.txt
  python app\main.py
```

> PyQt6, PyQt6-WebEngine, paramiko, requests y beautifulsoup4 instalados en Python 3.14 (verificado 2026-05-29).

---

## Configuración de red objetivo (post-migración)

```
Internet (FTTH Movistar)
        │
        │ Fibra óptica
        ▼
┌─────────────────────────────────┐
│  Movistar GPT-2742GX4X5v6       │
│  Modo: BRIDGE (transparente)    │
│  Solo convierte fibra → Ethernet│
└────────────┬────────────────────┘
             │ Ethernet (PPPoE frames)
             ▼
┌─────────────────────────────────┐
│  Asus RT-BE50 (192.168.50.1)   │
│  WAN0: PPPoE directo a Movistar │
│  LAN: 192.168.50.0/24           │
│  WAN2: Vodafone (mantener si ok)│
└──────┬──────────────┬───────────┘
       │              │
       ▼              ▼
ThinkPad X250    HP Mini 400 G9
192.168.50.10    192.168.50.20
Home Assistant   Windows 11
```

---

## Configuración LAN del Movistar (antes del bridge mode)

Capturada el 2026-05-30. Necesaria si se quiere restaurar o configurar IPTV en el Asus.

| Parámetro | Valor |
|---|---|
| IP LAN | 192.168.1.1 / 255.255.255.0 |
| DHCP pool principal | 192.168.1.33, 167 hosts |
| **DHCP condicional VendorID `[IAL]`** (Movistar TV) | pool 200–223, GW 192.168.1.1, DNS 172.23.101.98, **Option240: `::::239.0.2.29:22222`** |
| DHCP condicional VendorID `TEF_IOT` | pool 230–250, DNS 1.1.1.1 / 9.9.9.9 |
| DHCP lease | 43200 s |
| DNS global | 1.1.1.1 / 9.9.9.9 |

> ⚠️ **Si hay Movistar TV**: el Option240 `::::239.0.2.29:22222` es la dirección IPTV multicast.
> En bridge mode el decodificador necesitará que el Asus tenga IPTV VLAN configurado.

---

## Notas importantes

- Las credenciales PPPoE de Movistar en España suelen ser:
  - Usuario: `adslppp@movistar.es` (o similar, ver en backup)
  - Contraseña: genérica por operador (no la del router, la del ISP)
- El Movistar GPT-2742GX4X5v6 en bridge mode puede mantener IP de gestión en 192.168.1.1 desde los puertos LAN, pero la IP WAN del Asus cambiará de privada (192.168.1.x) a pública (IP asignada por Movistar ISP).
- Los scripts JFFS (nat-start, wan-event) siguen siendo válidos. Si se abandona Vodafone como WAN2, se pueden simplificar eliminando referencias a WAN2.
