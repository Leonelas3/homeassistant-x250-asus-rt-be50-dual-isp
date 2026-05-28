# Entra a la carpeta del repo nuevo (ajusta la ruta si es diferente)
cd C:\Users\TuUsuario\homeassistant-x250-asus-rt-be50-dual-isp

# Descarga el archivo desde el repo original
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Leonelas3/ThinkPad-X240-WINDOWS-LINUX-APPLE/claude/router-cable-compatibility-pZ0K7/network-config/EXPLICA_CLAUDE_PC.md" -OutFile "EXPLICA_CLAUDE_PC.md"

# Sube al nuevo repo
git add EXPLICA_CLAUDE_PC.md
git commit -m "Add project context file"
git push
