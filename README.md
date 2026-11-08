# Optcg-calendar-europe

Calendario (`.ics`) con los lanzamientos y eventos europeos de ONE PIECE CARD GAME, generado a partir de la web oficial [en.onepiece-cardgame.com](https://en.onepiece-cardgame.com/events/).

- `calendario.py` — scraper (solo biblioteca estándar de Python). Genera `docs/optcg-europa.ics` y guarda el historial en `estado.json`.
- `.github/workflows/actualizar.yml` — lo ejecuta cada día y commitea el `.ics` actualizado.

Para suscribirse: Google Calendar → *Otros calendarios* → **+** → *Desde URL* → `https://calendar.poordevelopers.com/optcg-eu.ics`
(dirección directa, sin el Worker: `https://raw.githubusercontent.com/cdelgado813/Optcg-calendar-europe/main/docs/optcg-europa.ics`).

## Worker `calendar.poordevelopers.com`

`worker/` es un Worker de Cloudflare (`poordev-wrkr-cal-1-pro`) que da una URL amigable y sirve el `.ics` con `Content-Type: text/calendar`, cacheado 1 h en el borde. Para añadir otro calendario basta con una entrada en `CALENDARIOS` de `worker/src/index.js`.

Despliegue (crea el Worker, el registro DNS y el certificado; sin Terraform, decisión consciente por ser un recurso único y trivial):

- Con Node ≥ 22: `cd worker && npx wrangler deploy`
- Sin wrangler (p. ej. la Pi con Node 20): `worker/desplegar.sh`, con `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID` en el entorno.

Token mínimo (plantilla *Custom token*): **Account › Workers Scripts: Edit** + **Zone › Workers Routes: Edit**, **Zone › DNS: Edit** y **Zone › Zone: Read**, limitado a la zona `poordevelopers.com`.

Coste: plan Free de Workers (100k peticiones/día); con la caché de 1 h el uso real es mínimo.

Google relee los calendarios suscritos por su cuenta (normalmente cada 12-24 h), así que un cambio en la web puede tardar hasta un día en verse.

Ejecutar a mano: `python3 -I calendario.py`.
