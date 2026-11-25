"""Genera los SVG animados del perfil de GitHub (tema claro y oscuro).

Uso:  python scripts/generar_svgs.py [carpeta_de_fuentes]
Las fuentes (Space Grotesk, JetBrains Mono y Caveat, de Google Fonts) se recortan
a los caracteres usados y se incrustan en cada SVG, así se ven igual en cualquier lado.
"""
import base64, io, math, os, sys
from xml.sax.saxutils import escape
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools import subset

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "..", "github-byleny", "fonts")
SALIDA = os.path.join(RAIZ, "assets")

FAMILIAS = {  # clave: (archivo, peso)
    "SG7": ("SpaceGrotesk.ttf", 700),
    "SG5": ("SpaceGrotesk.ttf", 500),
    "JB5": ("JetBrainsMono.ttf", 500),
    "JB7": ("JetBrainsMono.ttf", 700),
    "CV": ("Caveat.ttf", 700),
}
_cache = {}


def fuente(k):
    if k not in _cache:
        archivo, peso = FAMILIAS[k]
        f = TTFont(os.path.join(FUENTES, archivo))
        _cache[k] = instantiateVariableFont(f, {"wght": peso})
    return _cache[k]


def ancho(texto, k, size):
    f = fuente(k)
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    total = 0
    for ch in texto:
        g = cmap.get(ord(ch))
        if g is None:
            raise ValueError(f"'{ch}' no existe en {k}")
        total += hmtx[g][0]
    return total * size / upm


TEMAS = {
    "light": dict(bg="#FAFAF9", card="#FFFFFF", fg="#121212", muted="#5A5A5A", line="#121212",
                  shadow="#121212", dot="#121212", dotop=".10", accent="#4640DE", soft="#F1EFEA",
                  band="#121212", bandtx="#FAFAF9", map="#121212"),
    "dark": dict(bg="#0E0E10", card="#18181B", fg="#FAFAF9", muted="#A6A6B8", line="#FAFAF9",
                 shadow="#8C88F5", dot="#FAFAF9", dotop=".08", accent="#8C88F5", soft="#232329",
                 band="#D6F24C", bandtx="#121212", map="#0B0B0D"),
}
INK, PAPER, INDIGO, GOLD, LIME, GREEN, RED, AMBER = ("#121212", "#FAFAF9", "#4640DE", "#F2C230",
                                                     "#D6F24C", "#2FBF71", "#FF5A4E", "#F2A93B")

CSS_BASE = """
.a{transform-box:fill-box;transform-origin:center}
@keyframes pop{from{opacity:0;transform:scale(.6) rotate(-6deg)}}
@keyframes up{from{opacity:0;transform:translateY(18px)}}
@keyframes fade{from{opacity:0}}
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
@keyframes bob2{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(6px) rotate(1deg)}}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
@keyframes hl{from{transform:scaleX(0)}}
@keyframes pulse{0%{transform:scale(.6);opacity:.9}100%{transform:scale(2.6);opacity:0}}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
@keyframes grow{from{transform:scaleY(0)}}
@keyframes growx{from{transform:scaleX(0)}}
@keyframes wiggle{0%,100%{transform:rotate(-4deg)}50%{transform:rotate(4deg)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


class SVG:
    def __init__(self, w, h, t):
        self.w, self.h, self.t = w, h, t
        self.partes, self.usos, self.css = [], {}, [CSS_BASE]

    def add(self, s):
        self.partes.append(s)
        return self

    def text(self, x, y, s, k, size, fill, anchor="start", extra="", ls=0):
        self.usos.setdefault(k, set()).update(s)
        lsa = f' letter-spacing="{ls}"' if ls else ""
        self.partes.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{k}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}"{lsa} {extra}>{escape(s)}</text>')
        return ancho(s, k, size) + ls * len(s)

    def caja(self, x, y, w, h, fill, r=16, sw=2.5, sombra=6, sh=None, extra=""):
        sh = sh or self.t["shadow"]
        out = ""
        if sombra:
            out += f'<rect x="{x+sombra}" y="{y+sombra}" width="{w}" height="{h}" rx="{r}" fill="{sh}"/>'
        out += (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" '
                f'stroke="{self.t["line"]}" stroke-width="{sw}" {extra}/>')
        return out

    def pill(self, x, y, s, k, size, fill, color, pad=14, h=None, sombra=3, sw=2):
        w = ancho(s, k, size) + pad * 2
        h = h or size * 2.1
        self.add(self.caja(x, y, w, h, fill, r=h / 2, sw=sw, sombra=sombra))
        self.text(x + w / 2, y + h / 2 + size * 0.36, s, k, size, color, "middle")
        return w

    def render(self, nombre):
        caras = []
        for k, chars in self.usos.items():
            f = fuente(k)
            buf = io.BytesIO()
            f.save(buf)
            buf.seek(0)
            sub = TTFont(buf)
            opts = subset.Options()
            opts.flavor = "woff"
            opts.layout_features = ["kern", "liga", "calt"]
            opts.name_IDs = []
            opts.notdef_outline = True
            s = subset.Subsetter(opts)
            s.populate(text="".join(sorted(chars)) + " ")
            s.subset(sub)
            out = io.BytesIO()
            sub.flavor = "woff"
            sub.save(out)
            b64 = base64.b64encode(out.getvalue()).decode()
            caras.append(f"@font-face{{font-family:'{k}';src:url(data:font/woff;base64,{b64}) format('woff')}}")
        estilo = "".join(caras) + "".join(self.css)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
               f'width="{self.w}" height="{self.h}" role="img" aria-label="{escape(nombre)}">'
               f'<style>{estilo}</style>{"".join(self.partes)}</svg>')
        return svg


def anim(nombre, dur, delay=0, extra="backwards", ease="cubic-bezier(.2,.8,.2,1)"):
    return f'style="animation:{nombre} {dur}s {ease} {delay}s {extra}"'


def loop(nombre, dur, delay=0, ease="ease-in-out"):
    return f'style="animation:{nombre} {dur}s {ease} {delay}s infinite"'


def flecha(x, y, size, color, sw=3):
    """Flecha ↗ dibujada (las fuentes no traen el glifo)."""
    s = size
    return (f'<path d="M{x} {y+s} L{x+s} {y} M{x+s*0.3} {y} L{x+s} {y} L{x+s} {y+s*0.7}" '
            f'fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')


def estrella(cx, cy, r, color):
    p = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.32
        p.append(f"{cx + rr*math.cos(a):.1f},{cy + rr*math.sin(a):.1f}")
    return f'<polygon points="{" ".join(p)}" fill="{color}"/>'


# ───────────────────────────────────────────────────────────── HERO
def hero(t):
    W, H = 1200, 540
    s = SVG(W, H, t)
    s.add(f'<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
          f'<circle cx="2" cy="2" r="1.4" fill="{t["dot"]}" opacity="{t["dotop"]}"/></pattern>'
          f'<clipPath id="panel"><rect x="2" y="2" width="1186" height="526" rx="30"/></clipPath></defs>')
    s.add(f'<rect x="12" y="12" width="1186" height="526" rx="30" fill="{t["shadow"]}"/>')
    s.add(f'<rect x="2" y="2" width="1186" height="526" rx="30" fill="{t["bg"]}"/>')
    s.add('<g clip-path="url(#panel)"><rect width="1200" height="540" fill="url(#dots)"/>')

    # fila superior
    s.add(f'<g class="a" {anim("fade", .6)}>')
    s.pill(48, 38, "PORTAFOLIO · V2026", "JB7", 13, t["card"], t["fg"], sombra=0)
    s.add("</g>")
    txt = "DISPONIBLE PARA NUEVOS PROYECTOS"
    w = ancho(txt, "JB7", 13) + 58
    x0 = 1140 - w
    s.add(f'<g class="a" {anim("fade", .6, .1)}>')
    s.add(s.caja(x0, 38, w, 28, t["card"], r=14, sw=2, sombra=0))
    s.add(f'<circle cx="{x0+20}" cy="52" r="5" fill="{GREEN}"/>'
          f'<circle cx="{x0+20}" cy="52" r="5" fill="{GREEN}" class="a" {loop("pulse", 1.8, 0, "ease-out")}/>')
    s.text(x0 + 34, 56.5, txt, "JB7", 13, t["fg"])
    s.add("</g>")

    # saludo a mano + flecha
    s.add(f'<g class="a" {anim("pop", .7, .2)}><g transform="rotate(-4 60 128)">')
    s.text(52, 128, "¡Hola! Soy Bylen Naspiran", "CV", 44, t["accent"])
    s.add("</g></g>")
    s.add(f'<path d="M478 104 C 540 92, 590 120, 586 166" fill="none" stroke="{t["accent"]}" stroke-width="3.5" '
          f'stroke-linecap="round" pathLength="1" stroke-dasharray="1" {anim("draw", .8, .8)}/>'
          f'<path d="M572 152 L586 168 L598 150" fill="none" stroke="{t["accent"]}" stroke-width="3.5" '
          f'stroke-linecap="round" stroke-linejoin="round" class="a" {anim("fade", .2, 1.5)}/>')

    # titular con resaltador
    s.add(f'<g class="a" {anim("up", .8, .3)}>')
    s.text(48, 238, "Software real,", "SG7", 94, t["fg"], ls=-2.5)
    s.add("</g>")
    w2 = ancho("impacto real.", "SG7", 94) - 2.5 * 13
    s.add(f'<rect x="40" y="276" width="{w2+22:.0f}" height="58" rx="6" fill="{LIME}" '
          f'transform="rotate(-1.2 40 300)" class="a" style="transform-origin:left;animation:hl .7s cubic-bezier(.2,.8,.2,1) .3s backwards"/>')
    s.add(f'<g class="a" {anim("up", .8, .45)}>')
    s.text(48, 326, "impacto real.", "SG7", 94, INK if t is TEMAS["dark"] else t["fg"], ls=-2.5)
    s.add("</g>")
    # en oscuro el texto sobre el resaltador va en tinta, pero fuera del resaltador quedaría invisible:
    # el resaltador cubre toda la frase, así que se mantiene legible.

    s.add(f'<g class="a" {anim("fade", .8, .7)}>')
    s.text(50, 384, "Estudiante de Ingeniería de Sistemas y desarrollador", "SG5", 22, t["muted"])
    s.text(50, 414, "de software en Cali, Colombia. Salud · Finanzas · Web.", "SG5", 22, t["muted"])
    s.add("</g>")

    # sticker 1: AUC
    s.add(f'<g class="a" {anim("pop", .7, .9)}><g class="a" {loop("bob", 4.2)}><g transform="rotate(3 945 150)">')
    s.add(s.caja(800, 96, 310, 112, INDIGO, r=18, sombra=7))
    s.text(822, 128, "SENTINELAS · ALERTA DE BROTES", "JB7", 12.5, "#CFCDF8", ls=0.5)
    s.text(820, 186, "AUC 0,954", "SG7", 54, PAPER, ls=-1)
    s.add("</g></g></g>")

    # sticker 2: en producción
    sub2 = "slestudiojuridico.com"
    w3 = ancho(sub2, "SG7", 23) + 40
    s.add(f'<g class="a" {anim("pop", .7, 1.1)}><g class="a" {loop("bob2", 5, .6)}><g transform="rotate(-4 990 270)">')
    s.add(s.caja(1132 - w3, 232, w3, 82, GOLD, r=16, sombra=6))
    s.add(f'<circle cx="{1132-w3+24}" cy="257" r="5.5" fill="{INK}"/>'
          f'<circle cx="{1132-w3+24}" cy="257" r="5.5" fill="{INK}" class="a" {loop("blink", 1.2, 0, "steps(1)")}/>')
    s.text(1132 - w3 + 38, 262, "EN PRODUCCIÓN · ENE 2026", "JB7", 12.5, INK)
    s.text(1132 - w3 + 20, 296, sub2, "SG7", 23, INK)
    s.add("</g></g></g>")

    # sticker 3: terminal
    s.add(f'<g class="a" {anim("pop", .7, 1.3)}><g class="a" {loop("bob", 4.8, 1.2)}><g transform="rotate(-1.5 930 390)">')
    s.add(s.caja(770, 336, 330, 124, t["card"], r=16, sombra=6))
    s.add(f'<path d="M770 368 v-16 a16 16 0 0 1 16 -16 h298 a16 16 0 0 1 16 16 v16 z" fill="{INK}" '
          f'stroke="{t["line"]}" stroke-width="2.5"/>')
    for i, c in enumerate([RED, GOLD, GREEN]):
        s.add(f'<circle cx="{792+i*18}" cy="352" r="5" fill="{c}"/>')
    s.text(1086, 357, "bash", "JB5", 12, "#A6A6B8", "end")
    lines = [("$ git push origin main", t["fg"]), ("› build listo", t["muted"]), ("● en producción", GREEN)]
    for i, (ln, col) in enumerate(lines):
        s.css.append(f"@keyframes ln{i}{{0%,{8+i*22}%{{opacity:0}}{12+i*22}%,92%{{opacity:1}}100%{{opacity:0}}}}")
        s.add(f'<g style="animation:ln{i} 6s linear 1.6s infinite">')
        s.text(790, 396 + i * 24, ln, "JB7" if i == 2 else "JB5", 16, col)
        s.add("</g>")
    s.add(f'<rect x="{790 + ancho("$ git push origin main", "JB5", 16) + 4:.0f}" y="383" width="9" height="17" '
          f'fill="{t["accent"]}" {loop("blink", 1, 0, "steps(1)")}/>')
    s.add("</g></g></g>")

    # cinta inferior en movimiento
    s.add(f'<rect x="0" y="470" width="1200" height="70" fill="{t["band"]}"/>')
    s.add(f'<line x1="0" y1="470" x2="1200" y2="470" stroke="{t["line"]}" stroke-width="2.5"/>')
    items = ["DESARROLLADOR DE SOFTWARE", "INGENIERÍA DE SISTEMAS", "HACKATHONS Y RETOS",
             "SALUD · FINANZAS · WEB", "MINTIC · DATOS ABIERTOS", "SOFTWARE CON IMPACTO"]
    x, partes = 0, []
    gap = 64
    seg = SVG(1, 1, t)
    for it in items:
        partes.append((x, it))
        x += ancho(it, "JB7", 19) + gap
    total = x
    s.css.append(f"@keyframes mq{{to{{transform:translateX(-{total:.1f}px)}}}}")
    s.add(f'<g style="animation:mq 26s linear infinite">')
    for rep in range(2):
        for px, it in partes:
            s.text(40 + px + rep * total, 512, it, "JB7", 19, t["bandtx"], ls=0)
            s.add(estrella(40 + px + rep * total + ancho(it, "JB7", 19) + gap / 2, 505, 11, GOLD if t is TEMAS["light"] else INDIGO))
    s.add("</g>")
    s.add("</g>")
    s.add(f'<rect x="2" y="2" width="1186" height="526" rx="30" fill="none" stroke="{t["line"]}" stroke-width="2.5"/>')
    return s


# ───────────────────────────────────────────────────────────── CIFRAS
def cifras(t):
    W, H = 1200, 200
    s = SVG(W, H, t)
    datos = [("0,954", "AUC de SentinelaS,", "validado en 16 años", INDIGO, PAPER, "#CFCDF8"),
             ("3", "apps en vivo de", "Parches CicloVida", t["card"], t["fg"], t["muted"]),
             ("1", "cliente real en", "producción desde 2026", GOLD, INK, "#3A3A3A"),
             ("1", "paper en congreso", "internacional (AmITIC)", t["card"], t["fg"], t["muted"]),
             ("3", "hackathons y retos", "de datos y ciudad", LIME, INK, "#3A3A3A")]
    gap = 18
    bw = (W - 14 - gap * 4) / 5
    for i, (num, l1, l2, fill, col, mut) in enumerate(datos):
        x = 2 + i * (bw + gap)
        rot = [-1.5, 1, -0.8, 1.4, -1.2][i]
        s.add(f'<g class="a" {anim("pop", .6, .1 + i * .12)}><g transform="rotate({rot} {x+bw/2} 95)">')
        s.add(s.caja(x, 14, bw, 166, fill, r=18, sombra=7))
        s.text(x + 22, 92, num, "SG7", 60, col, ls=-1.5)
        s.text(x + 22, 132, l1, "SG5", 16.5, mut)
        s.text(x + 22, 155, l2, "SG5", 16.5, mut)
        s.add("</g></g>")
    return s


# ───────────────────────────────────────────────────────────── ENCABEZADOS
def encabezado(t, num, kicker, titulo, nota):
    W, H = 1200, 130
    s = SVG(W, H, t)
    s.add(f'<g class="a" {anim("fade", .5)}>')
    w = s.pill(4, 14, f"{num} / {kicker}", "JB7", 13, t["accent"], PAPER if t is TEMAS["light"] else INK, sombra=3)
    s.add("</g>")
    s.add(f'<g class="a" {anim("up", .7, .1)}>')
    tw = s.text(2, 104, titulo, "SG7", 52, t["fg"], ls=-1.5)
    s.add("</g>")
    s.add(f'<path d="M4 118 q {tw/4:.0f} -10 {tw/2:.0f} 0 t {tw/2:.0f} 0" fill="none" stroke="{GOLD}" stroke-width="5" '
          f'stroke-linecap="round" pathLength="1" stroke-dasharray="1" {anim("draw", .9, .5)}/>')
    nx = min(tw + 60, 1190 - ancho(nota, "CV", 32))
    s.add(f'<g class="a" {anim("pop", .6, .8)}><g transform="rotate(-5 {nx} 90)">')
    s.text(nx, 98, nota, "CV", 32, t["accent"])
    s.add("</g></g>")
    return s


# ───────────────────────────────────────────────────────────── TARJETAS
def tarjeta(t, kicker, kfill, kcolor, evento, titulo, lineas, metrica, mlabel, tags, ilustracion):
    W, H = 610, 370
    s = SVG(W, H, t)
    s.add(f'<g class="a" {anim("up", .7)}>')
    s.add(s.caja(2, 2, 592, 352, t["card"], r=24, sombra=10))
    s.pill(28, 28, kicker, "JB7", 12, kfill, kcolor, pad=12, sombra=0)
    # evento a mano
    ew = ancho(evento, "CV", 25)
    s.add(f'<g transform="rotate(-3 {566-ew} 50)">')
    s.text(522, 52, evento, "CV", 25, t["accent"], "end")
    s.add("</g>")
    s.add(f'<circle cx="554" cy="46" r="20" fill="{GOLD}" stroke="{t["line"]}" stroke-width="2.5"/>')
    s.add(flecha(547, 39, 14, INK, 3))
    s.text(28, 124, titulo, "SG7", 40, t["fg"], ls=-1)
    for i, ln in enumerate(lineas):
        s.text(28, 156 + i * 24, ln, "SG5", 17, t["muted"])
    s.text(26, 272, metrica, "SG7", 48, t["accent"], ls=-1)
    s.text(28, 294, mlabel, "JB5", 12.5, t["muted"])
    x = 28
    for tg in tags:
        x += s.pill(x, 310, tg, "JB5", 12.5, t["soft"], t["fg"], pad=10, h=28, sombra=0, sw=1.8) + 8
    if x > 400:
        raise ValueError(f"Etiquetas muy largas en {titulo}: {x}")
    s.add(ilustracion(s, t))
    s.add("</g>")
    return s


def ilus_sentinelas(s, t):
    x0, y0 = 400, 196
    out = [s.caja(x0, y0, 170, 140, t["map"], r=14, sw=2, sombra=0)]
    out.append(f'<path d="M{x0+40} {y0+20} C {x0+90} {y0+30}, {x0+60} {y0+80}, {x0+110} {y0+120}" fill="none" '
               f'stroke="#2B2B33" stroke-width="10" stroke-linecap="round"/>')
    pts = [(30, 30, GREEN), (62, 24, GREEN), (96, 40, AMBER), (130, 30, GREEN), (44, 64, GREEN),
           (80, 74, RED), (120, 66, GREEN), (36, 104, AMBER), (68, 112, GREEN), (104, 104, RED), (140, 110, GREEN),
           (150, 76, GREEN)]
    for i, (px, py, c) in enumerate(pts):
        r = 9 if c == RED else 5.5
        out.append(f'<circle cx="{x0+px}" cy="{y0+py}" r="{r}" fill="{c}"/>')
        if c == RED:
            out.append(f'<circle cx="{x0+px}" cy="{y0+py}" r="{r}" fill="none" stroke="{c}" stroke-width="3" '
                       f'class="a" {loop("pulse", 2, i * .3, "ease-out")}/>')
    return "".join(out)


def ilus_finsmart(s, t):
    x0, y0 = 404, 214
    out = [f'<line x1="{x0}" y1="{y0+116}" x2="{x0+168}" y2="{y0+116}" stroke="{t["line"]}" stroke-width="2.5"/>']
    alturas = [40, 56, 34, 62, 46, 108, 50]
    for i, h in enumerate(alturas):
        c = RED if h == 108 else (t["accent"] if i % 2 else t["fg"])
        out.append(f'<rect x="{x0+6+i*23}" y="{y0+116-h}" width="16" height="{h}" rx="3" fill="{c}" '
                   f'class="a" style="transform-origin:bottom;animation:grow .7s cubic-bezier(.2,.8,.2,1) {.3+i*.08:.2f}s backwards"/>')
    bx = x0 + 6 + 5 * 23 + 8
    out.append(f'<g class="a" {loop("bob", 2.4)}><g transform="rotate(-6 {bx} {y0-6})">')
    s.usos.setdefault("CV", set()).update("anomalía")
    out.append(f'<text x="{bx-78}" y="{y0-4}" font-family="CV" font-size="26" fill="{RED}">anomalía</text>')
    out.append("</g></g>")
    return "".join(out)


def ilus_estudio(s, t):
    x0, y0 = 396, 200
    out = [s.caja(x0, y0, 178, 132, t["bg"], r=12, sw=2, sombra=0)]
    out.append(f'<path d="M{x0} {y0+26} v-14 a12 12 0 0 1 12 -12 h154 a12 12 0 0 1 12 12 v14 z" fill="{t["soft"]}" stroke="{t["line"]}" stroke-width="2"/>')
    for i, c in enumerate([RED, GOLD, GREEN]):
        out.append(f'<circle cx="{x0+14+i*12}" cy="{y0+13}" r="3.6" fill="{c}"/>')
    s.usos.setdefault("JB7", set()).update("AURORA")
    s.usos.setdefault("JB5", set()).update("Área privada")
    out.append(f'<text x="{x0+89}" y="{y0+56}" font-family="JB7" font-size="15" fill="{t["fg"]}" text-anchor="middle" letter-spacing="3">AURORA</text>')
    out.append(f'<text x="{x0+89}" y="{y0+74}" font-family="JB5" font-size="11" fill="{t["muted"]}" text-anchor="middle">Área privada</text>')
    for i in range(2):
        out.append(f'<rect x="{x0+30}" y="{y0+84+i*18}" width="118" height="12" rx="6" fill="{t["soft"]}" stroke="{t["line"]}" stroke-width="1.5"/>')
    out.append(f'<g class="a" {anim("pop", .5, 1)}><circle cx="{x0+160}" cy="{y0+118}" r="17" fill="{GREEN}" stroke="{t["line"]}" stroke-width="2"/>'
               f'<path d="M{x0+152} {y0+118} l6 6 l10 -12" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></g>')
    return "".join(out)


def ilus_parches(s, t):
    x0, y0 = 400, 200
    ruta = f"M{x0+10} {y0+110} C {x0+50} {y0+20}, {x0+90} {y0+140}, {x0+130} {y0+50} S {x0+170} {y0+10}, {x0+168} {y0+20}"
    out = [f'<path d="{ruta}" fill="none" stroke="{t["line"]}" stroke-width="3" stroke-dasharray="7 7" stroke-linecap="round"/>']
    for (px, py) in [(10, 110), (84, 92), (168, 20)]:
        out.append(f'<circle cx="{x0+px}" cy="{y0+py}" r="9" fill="{GOLD}" stroke="{t["line"]}" stroke-width="2.5"/>')
    out.append(f'<g><circle r="8" fill="{GREEN}" stroke="{t["line"]}" stroke-width="2.5"/>'
               f'<animateMotion dur="5s" repeatCount="indefinite" path="{ruta}"/></g>')
    # parche: grupo de personas
    gx, gy = x0 + 30, y0 + 18
    for i, (dx, dy, c) in enumerate([(0, 0, t["accent"]), (20, -6, RED), (40, 2, GREEN), (14, 18, GOLD)]):
        out.append(f'<circle cx="{gx+dx}" cy="{gy+dy}" r="9" fill="{c}" stroke="{t["line"]}" stroke-width="2" '
                   f'class="a" {anim("pop", .5, .6 + i * .15)}/>')
    return "".join(out)


def ilus_petstock(s, t):
    x0, y0 = 402, 204
    out = []
    datos = [("Alimento", .9), ("Arena", .35), ("Juguetes", .6)]
    s.usos.setdefault("JB5", set()).update("".join(d[0] for d in datos) + "mín")
    for i, (n, v) in enumerate(datos):
        y = y0 + 12 + i * 30
        out.append(f'<text x="{x0}" y="{y}" font-family="JB5" font-size="11" fill="{t["muted"]}">{n}</text>')
        out.append(f'<rect x="{x0}" y="{y+5}" width="160" height="12" rx="6" fill="{t["soft"]}" stroke="{t["line"]}" stroke-width="1.5"/>')
        c = RED if v < .4 else GREEN
        out.append(f'<rect x="{x0}" y="{y+5}" width="{160*v:.0f}" height="12" rx="6" fill="{c}" stroke="{t["line"]}" stroke-width="1.5" '
                   f'class="a" style="transform-origin:left;animation:growx .8s cubic-bezier(.2,.8,.2,1) {.4+i*.15:.2f}s backwards"/>')
    out.append(f'<line x1="{x0+64}" y1="{y0+10}" x2="{x0+64}" y2="{y0+86}" stroke="{t["accent"]}" stroke-width="2" stroke-dasharray="4 4"/>')
    s.usos.setdefault("SG5", set()).update("¿Qué se agota?")
    bx, by = x0 + 8, y0 + 98
    out.append(f'<g class="a" {loop("bob", 3.4)}>' + s.caja(bx, by, 150, 32, INDIGO, r=16, sw=2, sombra=3) +
               f'<text x="{bx+75}" y="{by+21}" font-family="SG5" font-size="14" fill="{PAPER}" text-anchor="middle">¿Qué se agota?</text></g>')
    return "".join(out)


def ilus_pulsored(s, t):
    cx, cy = 486, 316
    out = [f'<circle cx="{cx}" cy="{cy}" r="9" fill="{t["fg"]}"/>']
    for i, r in enumerate([34, 62, 90]):
        out.append(f'<path d="M{cx-r*0.78:.1f} {cy-r*0.62:.1f} A {r} {r} 0 0 1 {cx+r*0.78:.1f} {cy-r*0.62:.1f}" fill="none" '
                   f'stroke="{t["accent"] if i < 2 else RED}" stroke-width="9" stroke-linecap="round" '
                   f'style="animation:wf{i} 2.4s steps(1) infinite"/>')
    s.css.append("@keyframes wf0{0%{opacity:.15}15%,100%{opacity:1}}@keyframes wf1{0%,30%{opacity:.15}45%,100%{opacity:1}}"
                 "@keyframes wf2{0%,60%{opacity:.15}75%,100%{opacity:1}}")
    s.usos.setdefault("JB7", set()).update("riesgo 82")
    out.append(f'<g class="a" {loop("bob", 3)}>' + s.caja(cx + 40, cy - 112, 92, 28, GOLD, r=14, sw=2, sombra=3) +
               f'<text x="{cx+86}" y="{cy-93}" font-family="JB7" font-size="12" fill="{INK}" text-anchor="middle">riesgo 82</text></g>')
    return "".join(out)


PROYECTOS = {
    "sentinelas": ("ALERTA TEMPRANA · SALUD", INDIGO, PAPER, "Datos al Ecosistema 2026", "SentinelaS",
                   ["Alerta brotes epidémicos por municipio en el", "Valle del Cauca, 4 semanas antes."],
                   "0,954", "AUC · VALIDADO EN 16 AÑOS", ["Python", "sklearn", "Gemini"], ilus_sentinelas),
    "finsmart": ("FINANZAS PERSONALES · ML", GOLD, INK, "Proyecto de grado", "FinSmart",
                 ["Recurrentes, gastos inusuales y facturas", "de GDO con pago directo por PSE."],
                 "2 modelos", "ISOLATION FOREST + DBSCAN", ["FastAPI", "Next.js", "Docker"], ilus_finsmart),
    "estudio": ("CLIENTE REAL · WEB", GREEN, INK, "En vivo desde ene 2026", "Estudio jurídico",
                ["Sitio, bitácora con suscripción y AURORA:", "el portal donde los clientes siguen su caso."],
                "En vivo", "SLESTUDIOJURIDICO.COM", ["Web", "Producción"], ilus_estudio),
    "parches": ("SMART CITY · CALI", LIME, INK, "Smart City Expo 2026", "Parches CicloVida",
                ["Te une con gente de tu hora, estación y", "ritmo para ir juntos a la CicloVida."],
                "3 apps", "EN VIVO EN RENDER", ["Flutter", "FastAPI", "k-means"], ilus_parches),
    "petstock": ("GESTIÓN + IA GENERATIVA", INDIGO, PAPER, "Proyecto personal", "PetStock",
                 ["Inventario y ventas con un asistente que", "conoce la tienda y crea su publicidad."],
                 "4 módulos", "DASHBOARD · INVENTARIO · VENTAS · IA", ["Next.js", "Express", "Prisma"], ilus_petstock),
    "pulsored": ("WIFI PÚBLICO · AGENTES", GOLD, INK, "Hackathon Colombia 5.0", "PulsoRed",
                 ["Score de riesgo por punto wifi, tiempo", "estimado a la falla y autopsia de cada caída."],
                 "3", "AGENTES DE IA · MINTIC 2025", ["Python", "Leaflet"], ilus_pulsored),
}


def mini(t, kicker, titulo, linea, metrica, mlabel, color):
    W, H = 610, 190
    s = SVG(W, H, t)
    s.add(f'<g class="a" {anim("up", .7)}>')
    s.add(s.caja(2, 2, 592, 172, t["card"], r=22, sombra=10))
    s.pill(26, 24, kicker, "JB7", 12, t["soft"], t["fg"], pad=12, sombra=0, sw=1.8)
    s.text(26, 104, titulo, "SG7", 34, t["fg"], ls=-1)
    s.text(26, 140, linea, "SG5", 16.5, t["muted"])
    s.text(566, 100, metrica, "SG7", 52, color, "end", ls=-1)
    s.text(566, 124, mlabel, "JB5", 12, t["muted"], "end")
    s.add(f'')
    s.add("</g>")
    return s


# ───────────────────────────────────────────────────────────── TRAYECTORIA
def trayectoria(t):
    W, H = 1200, 360
    s = SVG(W, H, t)
    y = 178
    s.add(f'<line x1="40" y1="{y}" x2="1160" y2="{y}" stroke="{t["line"]}" stroke-width="4" stroke-linecap="round" '
          f'pathLength="1" stroke-dasharray="1" {anim("draw", 1.6, .1, "backwards", "ease-in-out")}/>')
    hitos = [("2025", "Hackathon Colombia 5.0", "MinTIC · PulsoRed", GOLD),
             ("SEP 2025", "Paper en AmITIC", "A* vs. suma mínima · Neiva", INDIGO),
             ("ENE 2026", "Sitio en producción", "Estudio jurídico · AURORA", GREEN),
             ("2026", "Datos al Ecosistema", "SentinelaS · salud pública", INDIGO),
             ("2026", "Smart City Expo Cali", "Parches CicloVida · Dedsec", LIME),
             ("2027", "Ingeniero de Sistemas", "Universidad de San Buenaventura", GOLD)]
    n = len(hitos)
    for i, (fecha, tit, sub, c) in enumerate(hitos):
        x = 150 + i * (900 / (n - 1))
        d = .3 + i * .22
        arriba = i % 2 == 0
        final = i == n - 1
        s.add(f'<g class="a" {anim("pop", .5, d)}>')
        s.add(f'<circle cx="{x}" cy="{y}" r="15" fill="{c if not final else t["card"]}" stroke="{t["line"]}" stroke-width="3" '
              f'{"stroke-dasharray=\"5 4\"" if final else ""}/>')
        s.add("</g>")
        ty = y - 96 if arriba else y + 58
        s.add(f'<g class="a" {anim("up", .6, d + .1)}>')
        s.add(f'<line x1="{x}" y1="{y + (-15 if arriba else 15)}" x2="{x}" y2="{ty + (52 if arriba else -22)}" stroke="{t["line"]}" stroke-width="2"/>')
        s.pill(x - (ancho(fecha, "JB7", 12) + 20) / 2, ty - 26 if arriba else ty - 22, fecha, "JB7", 12,
               t["accent"], PAPER if t is TEMAS["light"] else INK, pad=10, h=24, sombra=0, sw=2)
        s.text(x, ty + 20 if arriba else ty + 24, tit, "SG7", 19, t["fg"], "middle")
        s.text(x, ty + 42 if arriba else ty + 46, sub, "SG5", 14, t["muted"], "middle")
        s.add("</g>")
    # "aquí voy"
    xa = 985
    s.add(f'<circle cx="{xa}" cy="{y}" r="7" fill="{RED}"/><circle cx="{xa}" cy="{y}" r="7" fill="{RED}" class="a" {loop("pulse", 1.6, 0, "ease-out")}/>')
    s.add(f'<g class="a" {anim("pop", .6, 1.9)}><g transform="rotate(-6 {xa+30} 50)">')
    s.text(xa + 22, 58, "aquí voy", "CV", 34, RED)
    s.add("</g></g>")
    s.add(f'<path d="M{xa+40} 72 C {xa+46} 110, {xa+20} 140, {xa+5} 160" fill="none" stroke="{RED}" stroke-width="3" stroke-linecap="round" '
          f'pathLength="1" stroke-dasharray="1" {anim("draw", .6, 2.1)}/>'
          f'<path d="M{xa+1} 145 L{xa+3} 162 L{xa+19} 155" fill="none" stroke="{RED}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" class="a" {anim("fade", .2, 2.6)}/>')
    return s


# ───────────────────────────────────────────────────────────── STACK
def stack(t):
    W, H = 1200, 370
    s = SVG(W, H, t)
    cols = [("BACKEND Y DATOS", INDIGO, ["Python", "FastAPI", "pandas", "Node.js", "Express", "SQLite"]),
            ("FRONTEND", GOLD, ["TypeScript", "React", "Next.js", "Flutter", "Leaflet", "Chart.js"]),
            ("ML Y VISIÓN", GREEN, ["scikit-learn", "Prophet", "PyTorch", "TensorFlow", "YOLO", "ResNet-50"]),
            ("IA GENERATIVA", LIME, ["Claude", "Gemini", "OpenAI API", "Hugging Face", "Copilot", "Cursor"]),
            ("HERRAMIENTAS", t["accent"], ["Git", "GitHub", "GitLab", "Docker", "Compose", "Jupyter"])]
    cw = 1200 / 5
    k = 0
    for ci, (head, c, items) in enumerate(cols):
        x = ci * cw + 6
        s.add(f'<g class="a" {anim("fade", .5, ci * .1)}>')
        s.add(f'<rect x="{x}" y="10" width="14" height="14" rx="4" fill="{c}" stroke="{t["line"]}" stroke-width="2"/>')
        s.text(x + 22, 22.5, head, "JB7", 13, t["fg"], ls=0.5)
        s.add("</g>")
        for i, it in enumerate(items):
            rot = [-2, 1.5, -1, 2, -1.5, 1][(i + ci) % 6]
            y = 46 + i * 52
            s.add(f'<g class="a" {anim("pop", .45, .25 + k * .035)}><g transform="rotate({rot} {x+60} {y+18})">')
            fill = c if i == 0 else t["card"]
            col = (PAPER if c in (INDIGO, "#4640DE") else INK) if i == 0 else t["fg"]
            if i == 0 and c == "#8C88F5":
                col = INK
            s.pill(x, y, it, "SG5", 17, fill, col, pad=16, h=38, sombra=4)
            s.add("</g></g>")
            k += 1
    return s


# ───────────────────────────────────────────────────────────── CIERRE
def cierre(t):
    W, H = 1200, 340
    s = SVG(W, H, t)
    s.add(s.caja(2, 2, 1186, 326, INDIGO, r=30, sombra=10))
    s.add(f'<defs><pattern id="d2" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.4" fill="#FAFAF9" opacity=".12"/></pattern></defs>'
          f'<rect x="2" y="2" width="1186" height="326" rx="30" fill="url(#d2)"/>')
    s.text(56, 84, "¿TIENES UN PROYECTO EN MENTE?", "JB7", 16, "#CFCDF8", ls=1)
    s.add(f'<g class="a" {anim("up", .7, .2)}>')
    w = s.text(52, 186, "Hablemos.", "SG7", 112, PAPER, ls=-4)
    s.add("</g>")
    s.add(f'<path d="M58 210 q {w/4:.0f} -14 {w/2:.0f} 0 t {w/2-10:.0f} 0" fill="none" stroke="{GOLD}" stroke-width="7" stroke-linecap="round" '
          f'pathLength="1" stroke-dasharray="1" {anim("draw", .8, .8)}/>')
    s.text(58, 270, "Abierto a proyectos y colaboraciones en software, sistemas y datos.", "SG5", 20, "#E4E3FB")
    # sobre con carta
    ex, ey = 840, 92
    s.add(f'<g class="a" {loop("bob", 4)}><g transform="rotate(5 {ex+130} {ey+90})">')
    s.add(f'<g style="animation:carta 4s ease-in-out infinite">')
    s.css.append("@keyframes carta{0%,100%{transform:translateY(0)}50%{transform:translateY(-34px)}}")
    s.add(s.caja(ex + 22, ey - 10, 216, 150, PAPER, r=8, sw=2.5, sombra=0, sh=INK))
    s.text(ex + 40, ey + 24, "Hola Bylen,", "CV", 26, INK)
    s.text(ex + 40, ey + 52, "tengo una idea y", "CV", 24, "#3A3A3A")
    s.text(ex + 40, ey + 78, "quiero construirla.", "CV", 24, "#3A3A3A")
    s.add("</g>")
    s.add(f'<path d="M{ex} {ey+60} h260 v130 h-260 z" fill="{GOLD}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
          f'<path d="M{ex} {ey+60} l130 78 l130 -78" fill="{GOLD}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
          f'<path d="M{ex} {ey+190} l100 -66 M{ex+260} {ey+190} l-100 -66" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>')
    s.add(f'<circle cx="{ex+130}" cy="{ey+138}" r="16" fill="{RED}" stroke="{INK}" stroke-width="3"/>')
    s.add("</g></g>")
    s.add(f'<g class="a" {loop("wiggle", 2.4)}>' + estrella(1108, 64, 22, LIME) + "</g>")
    s.add(f'<g class="a" {loop("wiggle", 3, .5)}>' + estrella(790, 270, 15, GOLD) + "</g>")
    return s


# ───────────────────────────────────────────────────────────── PORTAFOLIO
def portafolio(t):
    W, H = 1200, 590
    s = SVG(W, H, t)
    s.add(f'<defs><pattern id="d3" width="22" height="22" patternUnits="userSpaceOnUse">'
          f'<circle cx="2" cy="2" r="1.4" fill="{t["dot"]}" opacity="{t["dotop"]}"/></pattern>'
          f'<clipPath id="pantalla"><rect x="50" y="118" width="640" height="400" rx="4"/></clipPath></defs>')
    s.add(s.caja(2, 2, 1186, 576, t["bg"], r=30, sombra=10))
    s.add(f'<rect x="2" y="2" width="1186" height="576" rx="30" fill="url(#d3)"/>')

    # navegador con recorrido por el sitio
    carpeta = os.path.join(RAIZ, "scripts", "capturas")
    fotos = sorted(f for f in os.listdir(carpeta) if f.endswith(".jpg"))
    secciones = [f.split("-", 1)[1][:-4] for f in fotos]
    n = len(fotos)
    s.add(f'<g class="a" {anim("up", .8)}><g transform="rotate(-1.2 370 320)">')
    s.add(s.caja(36, 64, 668, 470, t["card"], r=18, sombra=9))
    s.add(f'<line x1="36" y1="108" x2="704" y2="108" stroke="{t["line"]}" stroke-width="2.5"/>')
    for i, c in enumerate([RED, GOLD, GREEN]):
        s.add(f'<circle cx="{62+i*20}" cy="86" r="6.5" fill="{c}" stroke="{t["line"]}" stroke-width="1.5"/>')
    s.add(s.caja(140, 73, 480, 26, t["soft"], r=13, sw=1.8, sombra=0))
    s.text(158, 91, "devbyleny.vercel.app", "JB7", 13.5, t["fg"])
    base_w = ancho("devbyleny.vercel.app", "JB7", 13.5)
    hold, mov = 2.6, .7
    paso = hold + mov
    total = paso * n
    # barra de direcciones sincronizada con cada sección
    for i, sec in enumerate(secciones):
        ini, fin = i * paso / total * 100, (i * paso + hold + mov * .5) / total * 100
        if i == 0:
            kf = f"0%,{fin:.2f}%{{opacity:1}}{fin+.01:.2f}%,{100 - mov*.5/total*100:.2f}%{{opacity:0}}100%{{opacity:1}}"
        else:
            kf = (f"0%,{ini - mov*.5/total*100:.2f}%{{opacity:0}}{ini - mov*.5/total*100 + .01:.2f}%,{fin:.2f}%{{opacity:1}}"
                  f"{fin+.01:.2f}%,100%{{opacity:0}}")
        s.css.append(f"@keyframes url{i}{{{kf}}}")
        etiqueta = "" if sec == "top" else f"/#{sec}"
        if etiqueta:
            s.add(f'<g style="animation:url{i} {total:.1f}s linear infinite;opacity:{1 if i == 0 else 0}">')
            s.text(158 + base_w, 91, etiqueta, "JB5", 13.5, t["accent"])
            s.add("</g>")
    s.add(f'<g clip-path="url(#pantalla)">')
    pasos = []
    for i in range(n):
        a, b = i * paso / total * 100, (i * paso + hold) / total * 100
        pasos.append(f"{a:.2f}%,{b:.2f}%{{transform:translateY({-400*i}px)}}")
    pasos.append(f"100%{{transform:translateY({-400*n}px)}}")
    s.css.append("@keyframes recorrido{" + "".join(pasos) + "}")
    s.add(f'<g style="animation:recorrido {total:.1f}s cubic-bezier(.7,0,.3,1) infinite">')
    for i, f in enumerate(fotos + fotos[:1]):
        with open(os.path.join(carpeta, f), "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        s.add(f'<image x="50" y="{118 + i*400}" width="640" height="400" href="data:image/jpeg;base64,{b64}"/>')
    s.add("</g></g>")
    s.add(f'<rect x="50" y="118" width="640" height="400" rx="4" fill="none" stroke="{t["line"]}" stroke-width="1.5"/>')
    s.add("</g></g>")

    # invitación
    x = 760
    s.add(f'<g class="a" {anim("fade", .5, .2)}>')
    s.pill(x, 62, "04 / PORTAFOLIO", "JB7", 13, t["accent"], PAPER if t is TEMAS["light"] else INK, sombra=3)
    s.add("</g>")
    s.add(f'<g class="a" {anim("up", .7, .3)}>')
    s.text(x - 2, 160, "¿Quieres", "SG7", 50, t["fg"], ls=-1.5)
    s.text(x - 2, 214, "conocerme más?", "SG7", 50, t["fg"], ls=-1.5)
    s.add("</g>")
    s.add(f'<g class="a" {anim("pop", .6, .7)}><g transform="rotate(-6 1060 110)">')
    s.text(1010, 114, "¡entra aquí!", "CV", 30, t["accent"])
    s.add("</g></g>")
    items = [("Cada proyecto a fondo, con video", INDIGO), ("Mi CV en español e inglés", GOLD),
             ("Dónde he trabajado y qué estudio", GREEN), ("Quién soy fuera del código", LIME)]
    for i, (it, c) in enumerate(items):
        y = 262 + i * 46
        s.add(f'<g class="a" {anim("up", .5, .6 + i * .12)}>')
        s.add(s.caja(x, y - 21, 28, 28, c, r=8, sw=2, sombra=3))
        col = PAPER if c == INDIGO else INK
        s.add(f'<path d="M{x+7} {y-7} l5 5 l9 -10" fill="none" stroke="{col}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
        s.text(x + 44, y, it, "SG5", 19, t["fg"])
        s.add("</g>")
    # botón con cursor que lo pulsa
    label = "Entrar al portafolio"
    bw = ancho(label, "SG7", 23) + 96
    by = 448
    s.css.append("@keyframes clic{0%,62%,100%{transform:translate(0,0)}70%{transform:translate(5px,5px)}78%{transform:translate(0,0)}}"
                 "@keyframes cursor{0%{transform:translate(150px,90px);opacity:0}15%{opacity:1}55%,80%{transform:translate(0,0);opacity:1}"
                 "66%{transform:translate(0,0) scale(.85)}100%{transform:translate(0,0);opacity:0}}"
                 "@keyframes onda{0%,64%{transform:scale(0);opacity:0}66%{transform:scale(.2);opacity:.9}90%,100%{transform:scale(1.6);opacity:0}}")
    s.add(f'<rect x="{x+5}" y="{by+5}" width="{bw}" height="66" rx="33" fill="{t["shadow"]}" class="a" {anim("fade", .6, 1.1)}/>')
    s.add(f'<g class="a" {anim("pop", .6, 1.1)}><g style="animation:clic 3.6s ease-in-out 1.6s infinite">')
    s.add(s.caja(x, by, bw, 66, GOLD, r=33, sombra=0))
    s.text(x + 28, by + 41, label, "SG7", 23, INK)
    s.add(f'<circle cx="{x+bw-33}" cy="{by+33}" r="21" fill="{INK}"/>')
    s.add(flecha(x + bw - 40, by + 26, 14, GOLD, 3))
    s.add("</g></g>")
    cx, cy = x + bw - 64, by + 46
    s.add(f'<circle cx="{cx}" cy="{cy-8}" r="26" fill="none" stroke="{t["accent"]}" stroke-width="3" class="a" '
          f'style="animation:onda 3.6s ease-out 1.6s infinite;opacity:0"/>')
    s.add(f'<g style="animation:cursor 3.6s ease-in-out 1.6s infinite;opacity:0"><g transform="translate({cx-8} {cy-14})">'
          f'<path d="M0 0 L0 30 L8 23 L14 36 L20 33 L14 21 L25 21 Z" fill="{PAPER}" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/></g></g>')
    s.text(x + 4, 556, "devbyleny.vercel.app", "JB5", 14, t["muted"])
    return s


# ───────────────────────────────────────────────────────────── BOTONES
def boton(t, label, fill, col):
    w = ancho(label, "SG7", 22) + 96
    s = SVG(int(w + 14), 86, t)
    s.add(s.caja(2, 4, w, 70, fill, r=35, sombra=7))
    s.text(30, 47, label, "SG7", 22, col, ls=0.5)
    s.add(f'<circle cx="{w-30}" cy="39" r="21" fill="{INK if fill != INK else PAPER}"/>')
    s.add(flecha(w - 37, 32, 14, fill if fill != INK else INK, 3))
    return s


def main():
    os.makedirs(SALIDA, exist_ok=True)
    piezas = {
        "hero": hero, "cifras": cifras, "portafolio": portafolio, "trayectoria": trayectoria, "stack": stack, "cierre": cierre,
        "h-proyectos": lambda t: encabezado(t, "01", "PROYECTOS", "Lo que he construido", "de la idea a producción"),
        "h-trayectoria": lambda t: encabezado(t, "02", "TRAYECTORIA", "De dónde vengo", "¡y lo que viene!"),
        "h-stack": lambda t: encabezado(t, "03", "STACK", "Con qué lo construyo", "Python y JS, casi siempre"),
        "mini-panini": lambda t: mini(t, "NODE.JS · API REST", "Panini API · Mundial 2026",
                                      "48 selecciones, tu colección e intercambios.", "960", "LÁMINAS", GOLD if t is TEMAS["dark"] else INDIGO),
        "mini-knn": lambda t: mini(t, "MACHINE LEARNING", "¿Es explícita esta canción?",
                                   "KNN vs. Naive Bayes sobre Spotify 2024.", "0,68", "ACCURACY · KNN", GREEN),
        "btn-portafolio": lambda t: boton(t, "PORTAFOLIO", INDIGO, PAPER),
        "btn-linkedin": lambda t: boton(t, "LINKEDIN", GOLD, INK),
        "btn-correo": lambda t: boton(t, "CORREO", LIME, INK),
    }
    for k, args in PROYECTOS.items():
        piezas[f"p-{k}"] = (lambda a: (lambda t: tarjeta(t, *a)))(args)
    total = 0
    for nombre, fn in piezas.items():
        for tema, t in TEMAS.items():
            svg = fn(t).render(nombre)
            ruta = os.path.join(SALIDA, f"{nombre}-{tema}.svg")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(svg)
            total += len(svg)
            print(f"{nombre}-{tema}.svg  {len(svg)/1024:.0f} KB")
    print(f"TOTAL {total/1024:.0f} KB")


if __name__ == "__main__":
    main()
