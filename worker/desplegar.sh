#!/usr/bin/env bash
# Despliega el Worker y su dominio con la API de Cloudflare, sin wrangler (la Pi tiene Node 20
# y wrangler 4 pide Node 22). Hace lo mismo que `npx wrangler deploy` con este wrangler.toml.
#
# Necesita en el entorno (nunca en el repo):
#   CLOUDFLARE_API_TOKEN   token con permisos minimos (ver README)
#   CLOUDFLARE_ACCOUNT_ID  ID de la cuenta
# Es idempotente: se puede relanzar tras cambiar src/index.js.
set -euo pipefail

NOMBRE="poordev-wrkr-cal-1-pro"
DOMINIO="calendar.poordevelopers.com"
ZONA="poordevelopers.com"
FECHA_COMPAT="2026-11-01"
API="https://api.cloudflare.com/client/v4"
AQUI="$(cd "$(dirname "$0")" && pwd)"

: "${CLOUDFLARE_API_TOKEN:?Falta CLOUDFLARE_API_TOKEN}"
: "${CLOUDFLARE_ACCOUNT_ID:?Falta CLOUDFLARE_ACCOUNT_ID}"
AUTH=(-H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}")

comprobar() {  # imprime el error de la API y sale si success != true
  python3 -I -c '
import json, sys
d = json.load(sys.stdin)
if not d.get("success"):
    print("ERROR:", json.dumps(d.get("errors"), ensure_ascii=False), file=sys.stderr); sys.exit(1)
print(json.dumps(d.get("result"))) if len(sys.argv) > 1 else None
' "$@"
}

echo "1/3 Subiendo el codigo del Worker ${NOMBRE}..."
curl -sS -X PUT "${API}/accounts/${CLOUDFLARE_ACCOUNT_ID}/workers/scripts/${NOMBRE}" "${AUTH[@]}" \
  -F "metadata={\"main_module\":\"index.js\",\"compatibility_date\":\"${FECHA_COMPAT}\"};type=application/json" \
  -F "index.js=@${AQUI}/src/index.js;type=application/javascript+module" | comprobar

echo "2/3 Buscando la zona ${ZONA}..."
ZONA_ID=$(curl -sS "${API}/zones?name=${ZONA}" "${AUTH[@]}" | comprobar r | python3 -I -c '
import json, sys
r = json.loads(sys.stdin.read())
if not r: sys.exit("ERROR: el token no ve la zona")
print(r[0]["id"])')

echo "3/3 Enlazando ${DOMINIO} (crea el DNS y el certificado)..."
curl -sS -X PUT "${API}/accounts/${CLOUDFLARE_ACCOUNT_ID}/workers/domains" "${AUTH[@]}" \
  -H "Content-Type: application/json" \
  -d "{\"hostname\":\"${DOMINIO}\",\"service\":\"${NOMBRE}\",\"zone_id\":\"${ZONA_ID}\",\"environment\":\"production\"}" \
  | comprobar

echo "Hecho: https://${DOMINIO}/optcg-eu.ics (el certificado puede tardar unos minutos)"
