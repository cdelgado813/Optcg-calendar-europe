#!/usr/bin/env python3
"""Calendario de eventos europeos de ONE PIECE CARD GAME a partir de la web oficial.

Lee https://en.onepiece-cardgame.com (la edicion NA/EU/OC/LATAM/ME) y genera un fichero .ics
al que Google Calendar se puede suscribir por URL. Solo biblioteca estandar: se ejecuta una vez
al dia y no necesita navegador, porque la web sirve el HTML ya montado.

Que se recoge:
  - Lanzamientos: listado de productos (boosters y barajas) con su "Release Date".
  - Eventos: cada tarjeta de /events/ y su pagina de detalle.
      * Si el detalle tiene seccion "Europe" con bloques "Date:/Venue:", se crea un evento por
        bloque (Regionales, Finals, Treasure Cups, LCQ...).
      * Si el detalle tiene bloques "Date:" pero ninguno de Europa (Mall Tour de EE. UU.,
        Coliseum de Oceania...), la pagina se descarta: no es un evento europeo.
      * Si no tiene bloques "Date:" (eventos de tienda, Store Championship...), se usa el
        periodo general de la tarjeta, que vale para todas las regiones.
      * Lineas de inscripcion para Europa ("EU September 4 at 5pm GMT...", "Europe: Starts
        October 25th...", "November 20 at 7pm (GMT)") se crean como eventos de inscripcion.

Estado: los eventos ya pasados se conservan (historial); los futuros se sustituyen por lo que
diga la web en cada ejecucion, asi un cambio de fecha o una cancelacion se reflejan solos.
Si una pagina falla al descargarse, se conservan los eventos que ya se tenian de ella.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE_URL = "https://en.onepiece-cardgame.com"
AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "docs" / "optcg-europa.ics"  # no mover: es la URL pública de suscripción
ESTADO = AQUI / "estado.json"
UA = "optcg-calendario/1.0 (calendario personal, 1 vez al dia)"
TIMEOUT = 30
PAUSA = 1.0  # segundos entre peticiones

MESES = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
MES_RE = "(" + "|".join(MESES) + "|sept|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)"
CORTO = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
         "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
REGIONES = {"north america", "europe", "oceania", "asia", "latin america",
            "southeast asia", "australia", "middle east"}
# Eventos sin sedes por region cuyo titulo ya dice que no son de Europa.
NO_EUROPA = ("orlando", "mall tour", "north america", "latin america", "oceania", "asia")


# ---- descarga y texto ---------------------------------------------------------

def descargar(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            datos = r.read().decode("utf-8", "replace")
    except Exception as e:  # red, 404, timeout... se registra y se sigue
        print(f"AVISO: no se pudo descargar {url}: {e}", file=sys.stderr)
        return None
    finally:
        time.sleep(PAUSA)
    return datos


def lineas(doc: str) -> list[str]:
    """HTML -> lineas de texto limpias; los enlaces quedan como '[url]' en su propia linea."""
    i, j = doc.find("<main"), doc.find("</main>")
    if i >= 0 and j > i:
        doc = doc[i:j]
    doc = re.sub(r"<script.*?</script>|<style.*?</style>", "", doc, flags=re.S | re.I)
    doc = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>', r"\n[\1]\n", doc)
    doc = re.sub(r"<br\s*/?>", "\n", doc, flags=re.I)
    doc = re.sub(r"<[^>]+>", "\n", doc)
    doc = html.unescape(doc).replace("\u200b", "").replace("\xa0", " ")
    return [re.sub(r"\s+", " ", l).strip() for l in doc.splitlines() if l.strip()]


# ---- fechas -------------------------------------------------------------------

def _mes(s: str) -> int:
    s = s.lower()
    return MESES.get(s) or CORTO[s]


def _anio_inferido(mes: int, dia: int, ref: date) -> int:
    """Fecha sin ano ("January 8"): el ano que la deja mas cerca de la fecha de referencia
    (el periodo del evento, o hoy si no se conoce)."""
    def distancia(anio: int) -> int:
        try:
            return abs((date(anio, mes, dia) - ref).days)
        except ValueError:
            return 10**6
    return min((ref.year - 1, ref.year, ref.year + 1), key=distancia)


def rango_fechas(texto: str, hoy: date) -> tuple[date, date, bool] | None:
    """Devuelve (inicio, fin_incluido, exacta). exacta=False si solo se conoce el mes."""
    t = texto.replace("–", "-").replace("—", "-").replace("～", "-").replace("~", "-")
    t = re.sub(r"\s+", " ", t)
    dia = r"(\d{1,2})(?:st|nd|rd|th)?(?!\d)"
    m = re.search(
        rf"\b{MES_RE}\.? {dia}(?:,? (\d{{4}}))?(?: ?- ?(?:{MES_RE}\.? )?{dia}(?!\d))?(?:,? (\d{{4}}))?",
        t, re.I)
    if m:
        m1, d1, y1, m2, d2, y2 = m.groups()
        mes1 = _mes(m1)
        anio_fin = int(y2[:4]) if y2 else (int(y1) if y1 else None)
        anio_ini = int(y1) if y1 else anio_fin
        mes2 = _mes(m2) if m2 else mes1
        try:
            if anio_ini is None:
                anio_ini = _anio_inferido(mes1, int(d1), hoy)
            if anio_fin is None:
                anio_fin = anio_ini
            # "December 28 - January 3, 2027": el inicio es del ano anterior
            if not y1 and mes2 < mes1:
                anio_ini = anio_fin - 1
            ini = date(anio_ini, mes1, int(d1))
            fin = date(anio_fin, mes2, int(d2)) if d2 else ini
        except ValueError:
            return None
        if fin < ini:
            fin = ini
        return ini, fin, True
    m = re.search(rf"\b{MES_RE}(?: ?- ?{MES_RE})? (\d{{4}})", t, re.I)
    if m:
        m1, m2, anio = _mes(m.group(1)), m.group(2), int(m.group(3))
        if m2 and _mes(m2) < m1:  # "December-January 2027"
            anio -= 1
        try:
            ini = date(anio, m1, 1)
        except ValueError:
            return None
        return ini, ini, False
    return None


# ---- modelo de evento ---------------------------------------------------------

def evento(clave: str, titulo: str, ini: date, fin: date, url: str, origen: str,
           lugar: str = "", notas: str = "", exacta: bool = True) -> dict:
    uid = hashlib.sha1(clave.encode()).hexdigest()[:20] + "@optcg-calendario"
    if not exacta:
        titulo += " (fecha aprox.: mes)"
    return {"uid": uid, "titulo": titulo, "inicio": ini.isoformat(), "fin": fin.isoformat(),
            "url": url, "lugar": lugar, "notas": notas, "origen": origen}


def categoria(titulo: str, url: str) -> str:
    t = (titulo + " " + url).lower()
    for patron, nombre in [
        ("last chance", "🎟️ LCQ"), ("lcq", "🎟️ LCQ"), ("extra grand battle", "⚔️ Extra Battle"),
        ("coliseum", "🔥 Coliseum"), ("heroines battle", "🏪 Heroines Battle"),
        ("side event", "🎲 Side event"), ("finals", "🏆 Finals"), ("world championship", "🌍 Worlds"),
        ("store championship", "🏪 Store Championship"), ("storecs", "🏪 Store Championship"),
        ("regional", "🏆 Regional"), ("store treasure", "🏪 Store Treasure Cup"),
        ("treasure cup", "💰 Treasure Cup"), ("bcgfest", "🎪 BCG Fest"),
        ("bandai card games fest", "🎪 BCG Fest"), ("championship", "🏆 Championship"),
        ("release event", "🏪 Evento de lanzamiento"), ("store", "🏪 Tienda"),
        ("pirates party", "🏪 Pirates Party"), ("pirates league", "🏪 Pirates League"),
    ]:
        if patron in t:
            return nombre
    return "📅 Evento"


# ---- productos ----------------------------------------------------------------

def productos(hoy: date) -> tuple[list[dict], bool]:
    eventos, ok = [], True
    for sub in ("boosters", "decks"):
        for pagina in (1, 2):
            doc = descargar(f"{BASE_URL}/products/?subcategory={sub}&page={pagina}")
            if doc is None:
                ok = False
                continue
            ls = lineas(doc)
            for i, l in enumerate(ls):
                if l != "Release Date" or i + 1 >= len(ls):
                    continue
                r = rango_fechas(ls[i + 1], hoy)
                if not r:
                    continue
                # hacia atras: nombre, categoria, [url]
                nombre, url = ls[i - 1], BASE_URL + "/products/"
                for k in range(i - 1, max(i - 6, -1), -1):
                    if ls[k].startswith("["):
                        url = ls[k][1:-1]
                        break
                nombre = re.sub(r"\s+", " ", nombre)
                codigo = re.search(r"\[([A-Z]+-?\d+)\]", nombre)
                corto = f"{codigo.group(1)} {nombre.split('[')[0].strip()}" if codigo else nombre
                eventos.append(evento(
                    f"producto|{url}", f"📦 Lanzamiento: {corto}", r[0], r[0], url, url,
                    notas=f"{nombre}\nFecha de lanzamiento oficial (edición inglesa NA/EU).",
                    exacta=r[2]))
    return eventos, ok


# ---- eventos ------------------------------------------------------------------

def tarjetas_eventos(hoy: date) -> list[dict] | None:
    doc = descargar(f"{BASE_URL}/events/")
    if doc is None:
        return None
    ls = lineas(doc)
    tarjetas, vistas = [], set()
    for i, l in enumerate(ls):
        if l != "Event Period:" or i + 1 >= len(ls):
            continue
        titulo = ls[i - 1]
        url = None
        for k in range(i - 1, max(i - 8, -1), -1):
            if ls[k].startswith("[") and "/events/" in ls[k]:
                url = ls[k][1:-1]
                break
        if not url or url in vistas or url.endswith("/events/"):
            continue
        if url.startswith("/"):
            url = BASE_URL + url
        vistas.add(url)
        periodo = ls[i + 1]
        if periodo.endswith("-") or periodo.endswith("–"):
            periodo += " " + ls[i + 2] if i + 2 < len(ls) else ""
        tarjetas.append({"titulo": titulo, "url": url, "periodo": periodo})
    return tarjetas


def es_region(linea: str) -> str | None:
    base = re.sub(r"[【\[(].*$", "", linea).strip().lower()
    return base if base in REGIONES else None


def detalle_evento(t: dict, hoy: date) -> list[dict] | None:
    doc = descargar(t["url"])
    if doc is None:
        return None
    ls = [l for l in lineas(doc) if not l.startswith("[")]
    titulo, url = t["titulo"], t["url"]
    cat = categoria(titulo, url)
    salida: list[dict] = []

    # 1) bloques "Date:" agrupados por region
    region, hay_bloques, bloques_eu = None, False, []
    for i, l in enumerate(ls):
        r = es_region(l)
        if r:
            region = r
            continue
        m = re.match(r"^(?:Event )?Dates?:\s*(.+)$", l)
        if not m:
            continue
        hay_bloques = True
        if region != "europe":
            continue
        org = ls[i - 1] if i > 0 else ""
        lugar = ""
        for k in range(i + 1, min(i + 4, len(ls))):
            mv = re.match(r"^(Venue|Location):\s*(.*)$", ls[k])
            if mv:
                lugar = mv.group(2).strip() or (ls[k + 1] if k + 1 < len(ls) else "")
                break
        bloques_eu.append((org, m.group(1), lugar))

    for org, fecha, lugar in bloques_eu:
        r = rango_fechas(fecha, hoy)
        if not r:
            continue
        partes = [p.strip() for p in lugar.split(",") if p.strip()]
        ciudad = partes[-2] if len(partes) >= 3 else (partes[0] if partes else "")
        ciudad = re.sub(r"^[\d\s]+(?=\D)", "", ciudad).strip()
        if org.lower().startswith("bcg fest"):
            ciudad = ciudad or org
        nombre = (f"{cat}: {ciudad}" + (f" ({org})" if org and org != ciudad else "")) if ciudad \
            else f"{cat}: {titulo}" + (f" ({org})" if org else "")
        salida.append(evento(
            f"evento|{url}|{org}|{r[0]}|{lugar}", nombre, r[0], r[1], url, url, lugar=lugar,
            notas=f"{titulo}\nOrganiza: {org}\nSede: {lugar}", exacta=r[2]))

    if hay_bloques and not bloques_eu:
        return []  # evento con sedes, pero ninguna en Europa

    # 2) sin sedes concretas: periodo general de la tarjeta (eventos de tienda, etc.)
    if not hay_bloques and any(k in titulo.lower() for k in NO_EUROPA):
        return []
    if not hay_bloques:
        r = rango_fechas(t["periodo"], hoy)
        for i, l in enumerate(ls[:-1]):
            if l.rstrip(":") in ("Period", "Event Period"):
                rd = rango_fechas(ls[i + 1], r[0] if r else hoy)
                if rd and rd[2]:
                    r = rd
                    break
        if r:
            salida.append(evento(
                f"periodo|{url}", f"{cat}: {titulo}",
                r[0], r[1], url, url,
                notas=f"{titulo}\nPeriodo: {t['periodo']}", exacta=r[2]))

    # 3) aperturas de inscripcion para Europa
    for i, l in enumerate(ls):
        if not (re.match(r"^(EU\b|■\s*Europe|Europe:)", l) or re.search(r"\(GMT\)|\bGMT\b.*-|\bCET\b", l)):
            continue
        if re.match(r"^(EU\b|■\s*Europe|Europe:)", l) is None and "GMT" not in l:
            continue
        ref = rango_fechas(t["periodo"], hoy)
        r = rango_fechas(l, ref[0] if ref else hoy)
        if not r:
            continue
        cab = next((ls[k] for k in range(i - 1, max(i - 5, -1), -1)
                    if re.search(r"period|application|registration", ls[k], re.I)), "Inscripción")
        salida.append(evento(
            f"inscripcion|{url}|{r[0]}", f"📝 Inscripción: {titulo}", r[0], r[1], url, url,
            notas=f"{cab}\n{l}", exacta=r[2]))
    return salida


# ---- ics ----------------------------------------------------------------------

def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _plegar(linea: str) -> str:
    b = linea.encode("utf-8")
    if len(b) <= 75:
        return linea
    trozos, actual = [], b""
    for ch in linea:
        c = ch.encode("utf-8")
        if len(actual) + len(c) > (75 if not trozos else 74):
            trozos.append(actual.decode("utf-8"))
            actual = b""
        actual += c
    trozos.append(actual.decode("utf-8"))
    return "\r\n ".join(trozos)


# Eventos de mas dias que esto se publican como dos marcas de un dia (empieza / termina).
# En la vista de mes, Google pone arriba las barras de varios dias, las mas largas primero:
# periodos de semanas (Pirates Party, Store Tournament...) tapaban a los Regionales de 2 dias,
# que acababan escondidos en el "+ mas". Asi los fines de semana importantes quedan arriba.
MAX_DIAS_BARRA = 4


def _vevent(uid: str, titulo: str, ini: date, fin_excl: date, e: dict, sello: str) -> list[str]:
    notas = e["notas"] + f"\n\n{e['url']}"
    ev = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{sello}",
          f"DTSTART;VALUE=DATE:{ini:%Y%m%d}", f"DTEND;VALUE=DATE:{fin_excl:%Y%m%d}",
          f"SUMMARY:{_esc(titulo)}", f"DESCRIPTION:{_esc(notas)}", f"URL:{e['url']}",
          "TRANSP:TRANSPARENT"]
    if e["lugar"]:
        ev.append(f"LOCATION:{_esc(e['lugar'])}")
    return ev + ["END:VEVENT"]


def generar_ics(eventos: list[dict]) -> str:
    sello = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//optcg-calendario//ES", "CALSCALE:GREGORIAN",
           "METHOD:PUBLISH", "X-WR-CALNAME:One Piece TCG · Europa",
           "X-WR-CALDESC:Lanzamientos y eventos europeos de ONE PIECE CARD GAME (web oficial)",
           "X-WR-TIMEZONE:Europe/Madrid", "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
           "X-PUBLISHED-TTL:PT12H"]
    un_dia = timedelta(days=1)
    for e in sorted(eventos, key=lambda e: (e["inicio"], e["titulo"])):
        ini, fin = date.fromisoformat(e["inicio"]), date.fromisoformat(e["fin"])
        if (fin - ini).days + 1 <= MAX_DIAS_BARRA:
            out += _vevent(e["uid"], e["titulo"], ini, fin + un_dia, e, sello)  # DTEND exclusivo
            continue
        periodo = f"Del {ini:%d/%m/%Y} al {fin:%d/%m/%Y}."
        marcado = dict(e, notas=f"{periodo}\n{e['notas']}")
        base = e["uid"].split("@", 1)[0]
        out += _vevent(f"{base}-ini@optcg-calendario", f"▶️ Empieza · {e['titulo']}",
                       ini, ini + un_dia, marcado, sello)
        out += _vevent(f"{base}-fin@optcg-calendario", f"⏹️ Termina · {e['titulo']}",
                       fin, fin + un_dia, marcado, sello)
    out.append("END:VCALENDAR")
    return "\r\n".join(_plegar(l) for l in out) + "\r\n"


# ---- principal ----------------------------------------------------------------

def main() -> int:
    hoy = date.today()
    try:
        previo = json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previo = {"eventos": {}}
    previos = previo.get("eventos", {})

    nuevos: dict[str, dict] = {}
    origenes_fallidos: set[str] = set()

    prods, ok_prods = productos(hoy)
    for e in prods:
        nuevos[e["uid"]] = e
    if not ok_prods:
        origenes_fallidos.add("productos")

    tarjetas = tarjetas_eventos(hoy)
    if tarjetas is None:
        origenes_fallidos.add("eventos")
        tarjetas = []
    paginas_ok = set()
    for t in tarjetas:
        evs = detalle_evento(t, hoy)
        if evs is None:
            origenes_fallidos.add(t["url"])
            continue
        paginas_ok.add(t["url"])
        for e in evs:
            nuevos[e["uid"]] = e

    if not nuevos:
        print("ERROR: no se ha obtenido ningun evento; no se toca el calendario", file=sys.stderr)
        return 1

    final = dict(nuevos)
    for uid, e in previos.items():
        if uid in final:
            continue
        pasado = date.fromisoformat(e["fin"]) < hoy
        fallo = ("productos" in origenes_fallidos and "/products/" in e["origen"]) \
            or ("eventos" in origenes_fallidos) or e["origen"] in origenes_fallidos
        # paginas que ya no salen en /events/ (eventos terminados) tambien se conservan
        retirada = "/events/" in e["origen"] and e["origen"] not in paginas_ok
        if pasado or fallo or retirada:
            final[uid] = e

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(generar_ics(list(final.values())), encoding="utf-8", newline="")
    ESTADO.write_text(json.dumps({"actualizado": datetime.now().isoformat(timespec="seconds"),
                                  "eventos": final}, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    altas = len(set(final) - set(previos))
    bajas = len(set(previos) - set(final))
    print(f"OK: {len(final)} eventos ({altas} nuevos, {bajas} retirados); "
          f"fallos: {sorted(origenes_fallidos) or 'ninguno'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
