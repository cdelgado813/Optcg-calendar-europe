# Optcg-calendar-europe

Calendario (`.ics`) con los lanzamientos y eventos europeos de ONE PIECE CARD GAME, generado a partir de la web oficial [en.onepiece-cardgame.com](https://en.onepiece-cardgame.com/events/).

- `calendario.py` — scraper (solo biblioteca estándar de Python). Genera `docs/optcg-europa.ics` y guarda el historial en `estado.json`.
- `.github/workflows/actualizar.yml` — lo ejecuta cada día y publica `docs/` en GitHub Pages.

Para suscribirse: Google Calendar → *Otros calendarios* → **+** → *Desde URL* → `https://cdelgado813.github.io/Optcg-calendar-europe/optcg-europa.ics`.

Google relee los calendarios suscritos por su cuenta (normalmente cada 12-24 h), así que un cambio en la web puede tardar hasta un día en verse.

Ejecutar a mano: `python3 -I calendario.py`.
