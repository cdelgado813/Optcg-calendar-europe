# 🏴‍☠️ One Piece TCG · Calendario de Europa

Calendario con los **lanzamientos y eventos europeos de ONE PIECE CARD GAME**, sacado de la [web oficial](https://en.onepiece-cardgame.com/events/) y **actualizado automáticamente cada día**.

### ➕ [Añadir a Google Calendar](https://calendar.google.com/calendar/render?cid=webcal%3A%2F%2Fraw.githubusercontent.com%2Fcdelgado813%2FOptcg-calendar-europe%2Fmain%2Fdocs%2Foptcg-europa.ics)

O copia esta dirección:

```
https://raw.githubusercontent.com/cdelgado813/Optcg-calendar-europe/main/docs/optcg-europa.ics
```

## Qué incluye

| | |
|---|---|
| 📦 **Lanzamientos** | Boosters (OP, EB, PRB…) y Starter Decks, con su fecha oficial |
| 🏆 **Regionales** | Cada Regional europeo con ciudad, sede y organizador |
| 🏪 **Store Championships** y eventos de tienda | Store Treasure Cup, eventos de lanzamiento, Pirates Party… |
| 💰 **Treasure Cups** · ⚔️ **Extra Battle** · 🎲 **Side events** | Los que se juegan junto a los Regionales |
| 🏆 **Finals** · 🎟️ **LCQ** · 🎪 **BANDAI CARD GAMES Fest** | Finales de temporada y grandes eventos |
| 📝 **Inscripciones** | Cuándo abre el registro para Europa |

Cada evento lleva en la descripción el enlace a su página oficial. Cuando la web solo da el mes (p. ej. «August 2026 onwards»), el evento aparece el día 1 marcado como *(fecha aprox.: mes)*.

## Cómo suscribirse

- **Google Calendar** (desde el ordenador; la app del móvil no lo permite): usa el enlace de arriba, o *Otros calendarios* → **+** → *Desde URL* y pega la dirección. Una vez añadido, aparece también en el móvil.
- **iPhone / Mac**: Ajustes → Calendario → Cuentas → Añadir cuenta → Otra → *Añadir calendario suscrito*, y pega la dirección.
- **Outlook**: *Agregar calendario* → *Suscribirse desde la web*.

Es una suscripción: los cambios llegan solos. Google refresca los calendarios suscritos cuando quiere (normalmente cada 12-24 h), así que algo nuevo en la web puede tardar hasta un día en verse.

## Cómo funciona

- [`calendario.py`](calendario.py) lee la web oficial (edición en inglés NA/EU): el listado de productos y cada página de evento, quedándose con la sección **Europe**. Solo usa la biblioteca estándar de Python.
- Una [GitHub Action](.github/workflows/actualizar.yml) lo ejecuta cada día a las 05:17 UTC y guarda el resultado en [`docs/optcg-europa.ics`](docs/optcg-europa.ics).
- [`estado.json`](estado.json) guarda el historial: los eventos pasados se conservan y los futuros se rehacen en cada ejecución, así que un cambio de fecha o una cancelación se reflejan solos.

Para generarlo a mano: `python3 -I calendario.py`

¿Falta algún evento o hay uno mal? Abre un [issue](../../issues).

---

<sub>Proyecto de fans, no oficial. ONE PIECE CARD GAME © Eiichiro Oda/Shueisha, Toei Animation, BANDAI. Los datos son de la web oficial de Bandai; ante cualquier duda, manda lo que diga allí.</sub>
