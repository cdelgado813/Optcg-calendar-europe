// Sirve los calendarios .ics de calendar.poordevelopers.com.
//
// Cada ruta apunta al fichero que genera la GitHub Action de su repo. El Worker solo hace de
// fachada: da una URL estable y amigable, y devuelve el tipo MIME correcto (text/calendar),
// que raw.githubusercontent.com no pone (sirve text/plain).
//
// La respuesta se cachea 1 hora en el borde de Cloudflare: los calendarios cambian como mucho
// una vez al dia y Google los relee cada pocas horas, asi que casi ninguna peticion llega a
// GitHub ni consume tiempo de CPU apreciable.

const CALENDARIOS = {
  "/optcg-eu.ics": {
    origen: "https://raw.githubusercontent.com/cdelgado813/Optcg-calendar-europe/main/docs/optcg-europa.ics",
    fichero: "optcg-eu.ics",
  },
};

const CACHE_SEGUNDOS = 3600;

export default {
  async fetch(request) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Método no permitido", { status: 405, headers: { Allow: "GET, HEAD" } });
    }

    const { pathname } = new URL(request.url);

    if (pathname === "/") {
      const lista = Object.keys(CALENDARIOS)
        .map((ruta) => `<li><a href="${ruta}">${ruta}</a></li>`)
        .join("");
      return new Response(
        `<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">` +
          `<title>Calendarios · Poor Developers</title><h1>Calendarios</h1><ul>${lista}</ul>` +
          `<p>Google Calendar → Otros calendarios → + → Desde URL.</p>`,
        { headers: { "Content-Type": "text/html; charset=utf-8" } },
      );
    }

    const cal = CALENDARIOS[pathname];
    if (!cal) {
      return new Response("No encontrado", { status: 404 });
    }

    const resp = await fetch(cal.origen, {
      cf: { cacheEverything: true, cacheTtl: CACHE_SEGUNDOS },
    });
    if (!resp.ok) {
      // Mejor un error claro que servir algo que no es un calendario: Google conserva la
      // ultima version buena y lo reintenta mas tarde.
      return new Response("El calendario no está disponible ahora mismo", { status: 502 });
    }

    return new Response(request.method === "HEAD" ? null : resp.body, {
      headers: {
        "Content-Type": "text/calendar; charset=utf-8",
        "Content-Disposition": `inline; filename="${cal.fichero}"`,
        "Cache-Control": `public, max-age=${CACHE_SEGUNDOS}`,
        "Access-Control-Allow-Origin": "*",
      },
    });
  },
};
