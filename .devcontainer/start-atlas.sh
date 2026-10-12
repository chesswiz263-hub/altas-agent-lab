#!/usr/bin/env bash
set -euo pipefail
# Codespaces forwards port 8000 privately to the account owner.
# Do not publish the port: this dev environment has no login by default.
python - <<'PY'
import socket, subprocess, sys
sock = socket.socket()
sock.settimeout(0.2)
try:
    if sock.connect_ex(('127.0.0.1', 8000)) == 0:
        print('ATLAS is already running on port 8000')
        sys.exit(0)
finally:
    sock.close()
with open('/tmp/atlas-codespace.log', 'a', encoding='utf8') as logfile:
    subprocess.Popen(['uvicorn', 'atlas.api:app', '--host', '0.0.0.0', '--port', '8000', '--workers', '1'],
                     stdin=subprocess.DEVNULL, stdout=logfile, stderr=subprocess.STDOUT,
                     start_new_session=True)
print('Started ATLAS. Open the forwarded private port 8000 from the PORTS panel.')
PY
