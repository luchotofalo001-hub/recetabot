"""Extracción local de ingredientes y tiempo. Sin IA."""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

def fold(text: str) -> str:
    text = text or ""
    text = text.lower().replace("ñ", "\x00n")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("\x00n", "n")


# Frases largas primero. Nombre canónico en español.
INGREDIENTS: list[tuple[str, str]] = [
    ("dulce de leche", "dulce de leche"),
    ("leche condensada", "leche condensada"),
    ("leche de coco", "leche de coco"),
    ("leche de almendras", "leche de almendras"),
    ("crema de leche", "crema de leche"),
    ("crema chantilly", "crema de leche"),
    ("queso crema", "queso crema"),
    ("queso untable", "queso crema"),
    ("cream cheese", "queso crema"),
    ("queso azul", "queso azul"),
    ("queso rallado", "queso rallado"),
    ("queso parmesano", "queso parmesano"),
    ("parmesano", "queso parmesano"),
    ("mozzarella", "mozzarella"),
    ("muzarella", "mozzarella"),
    ("muzzarella", "mozzarella"),
    ("provolone", "provolone"),
    ("roquefort", "roquefort"),
    ("ricota", "ricota"),
    ("ricotta", "ricota"),
    ("mascarpone", "mascarpone"),
    ("yogur", "yogur"),
    ("yogurt", "yogur"),
    ("manteca", "manteca"),
    ("mantequilla", "manteca"),
    ("aceite de oliva", "aceite de oliva"),
    ("aceite de coco", "aceite de coco"),
    ("aceite neutro", "aceite"),
    ("aceite vegetal", "aceite"),
    ("aceite de canola", "aceite"),
    ("aceite", "aceite"),
    ("oliva", "aceituna"),
    ("aceitunas", "aceituna"),
    ("aceituna", "aceituna"),
    ("huevo", "huevo"),
    ("huevos", "huevo"),
    ("yema", "huevo"),
    ("yemas", "huevo"),
    ("clara", "huevo"),
    ("claras", "huevo"),
    ("harina de almendras", "harina de almendras"),
    ("harina de avena", "harina de avena"),
    ("harina integral", "harina integral"),
    ("harina leudante", "harina"),
    ("harina 0000", "harina"),
    ("harina 000", "harina"),
    ("harina", "harina"),
    ("fecula de maiz", "fécula de maíz"),
    ("fécula de maíz", "fécula de maíz"),
    ("maicena", "fécula de maíz"),
    ("almidon", "almidón"),
    ("azucar impalpable", "azúcar impalpable"),
    ("azúcar impalpable", "azúcar impalpable"),
    ("azucar negra", "azúcar negra"),
    ("azucar mascabo", "azúcar mascabo"),
    ("azucar", "azúcar"),
    ("azúcar", "azúcar"),
    ("sal gruesa", "sal"),
    ("sal", "sal"),
    ("pimienta", "pimienta"),
    ("nuez moscada", "nuez moscada"),
    ("comino", "comino"),
    ("pimenton", "pimentón"),
    ("pimentón", "pimentón"),
    ("paprika", "pimentón"),
    ("aji molido", "ají molido"),
    ("ají molido", "ají molido"),
    ("oregano", "orégano"),
    ("orégano", "orégano"),
    ("tomillo", "tomillo"),
    ("romero", "romero"),
    ("laurel", "laurel"),
    ("perejil", "perejil"),
    ("cilantro", "cilantro"),
    ("albahaca", "albahaca"),
    ("menta", "menta"),
    ("ciboulette", "ciboulette"),
    ("curry", "curry"),
    ("curcuma", "cúrcuma"),
    ("canela", "canela"),
    ("clavo de olor", "clavo de olor"),
    ("vainilla", "vainilla"),
    ("esencia de vainilla", "vainilla"),
    ("extracto de vainilla", "vainilla"),
    ("cacao amargo", "cacao"),
    ("cacao", "cacao"),
    ("chocolate blanco", "chocolate blanco"),
    ("chocolate semi amargo", "chocolate"),
    ("chocolate amargo", "chocolate"),
    ("chocolate con leche", "chocolate con leche"),
    ("chocolate", "chocolate"),
    ("dulce de membrillo", "dulce de membrillo"),
    ("membrillo", "membrillo"),
    ("mermelada", "mermelada"),
    ("jalea", "mermelada"),
    ("miel", "miel"),
    ("glucosa", "glucosa"),
    ("levadura", "levadura"),
    ("polvo de hornear", "polvo de hornear"),
    ("royal", "polvo de hornear"),
    ("bicarbonato", "bicarbonato"),
    ("gelatina", "gelatina"),
    ("agar", "agar"),
    ("leche", "leche"),
    ("agua", "agua"),
    ("vino blanco", "vino blanco"),
    ("vino tinto", "vino tinto"),
    ("vino", "vino"),
    ("cerveza", "cerveza"),
    ("sidra", "sidra"),
    ("caldo de verduras", "caldo de verduras"),
    ("caldo de gallina", "caldo"),
    ("caldo de pollo", "caldo"),
    ("caldo", "caldo"),
    ("salsa de soja", "salsa de soja"),
    ("salsa de ostion", "salsa de ostras"),
    ("salsa de ostras", "salsa de ostras"),
    ("salsa de pescado", "salsa de pescado"),
    ("salsa de tomate", "salsa de tomate"),
    ("pure de tomate", "puré de tomate"),
    ("puré de tomate", "puré de tomate"),
    ("tomate triturado", "tomate"),
    ("tomate cherry", "tomate"),
    ("tomate perita", "tomate"),
    ("tomate seco", "tomate seco"),
    ("tomates secos", "tomate seco"),
    ("tomate", "tomate"),
    ("cebolla de verdeo", "cebolla de verdeo"),
    ("verdeo", "cebolla de verdeo"),
    ("cebollita de verdeo", "cebolla de verdeo"),
    ("cebolla morada", "cebolla"),
    ("cebolla", "cebolla"),
    ("ajo", "ajo"),
    ("echalote", "echalote"),
    ("morron", "morrón"),
    ("morrón", "morrón"),
    ("pimiento", "morrón"),
    ("aji picante", "ají"),
    ("ají", "ají"),
    ("chile", "ají"),
    ("zanahoria", "zanahoria"),
    ("papa", "papa"),
    ("papas", "papa"),
    ("patata", "papa"),
    ("batata", "batata"),
    ("boniato", "batata"),
    ("zapallo", "zapallo"),
    ("calabaza", "zapallo"),
    ("zucchini", "zucchini"),
    ("zucchinis", "zucchini"),
    ("zapallito", "zapallito"),
    ("berenjena", "berenjena"),
    ("choclo", "choclo"),
    ("maiz", "choclo"),
    ("maíz", "choclo"),
    ("arveja", "arveja"),
    ("arvejas", "arveja"),
    ("chaucha", "chaucha"),
    ("chauchas", "chaucha"),
    ("poroto", "poroto"),
    ("porotos", "poroto"),
    ("lenteja", "lenteja"),
    ("lentejas", "lenteja"),
    ("garbanzo", "garbanzo"),
    ("garbanzos", "garbanzo"),
    ("espinaca", "espinaca"),
    ("acelga", "acelga"),
    ("lechuga", "lechuga"),
    ("rucula", "rúcula"),
    ("rúcula", "rúcula"),
    ("repollo", "repollo"),
    ("brocoli", "brócoli"),
    ("brócoli", "brócoli"),
    ("coliflor", "coliflor"),
    ("puerro", "puerro"),
    ("apio", "apio"),
    ("hongo", "hongo"),
    ("hongos", "hongo"),
    ("champignon", "champignon"),
    ("champignones", "champignon"),
    ("portobello", "hongo"),
    ("palta", "palta"),
    ("aguacate", "palta"),
    ("pepino", "pepino"),
    ("rabano", "rabanito"),
    ("limón", "limón"),
    ("limon", "limón"),
    ("lima", "lima"),
    ("naranja", "naranja"),
    ("mandarina", "mandarina"),
    ("manzana", "manzana"),
    ("pera", "pera"),
    ("banana", "banana"),
    ("platano", "banana"),
    ("frutilla", "frutilla"),
    ("frutillas", "frutilla"),
    ("fresa", "frutilla"),
    ("frambuesa", "frambuesa"),
    ("frambuesas", "frambuesa"),
    ("arandano", "arándano"),
    ("arándano", "arándano"),
    ("arandanos", "arándano"),
    ("mora", "mora"),
    ("cereza", "cereza"),
    ("durazno", "durazno"),
    ("duraznos", "durazno"),
    ("ciruela", "ciruela"),
    ("higo", "higo"),
    ("higos", "higo"),
    ("kiwi", "kiwi"),
    ("anana", "ananá"),
    ("ananá", "ananá"),
    ("piña", "ananá"),
    ("mango", "mango"),
    ("maracuya", "maracuyá"),
    ("maracuyá", "maracuyá"),
    ("uva", "uva"),
    ("pasas de uva", "pasas"),
    ("pasas", "pasas"),
    ("coco rallado", "coco"),
    ("coco", "coco"),
    ("nuez", "nuez"),
    ("nueces", "nuez"),
    ("almendra", "almendra"),
    ("almendras", "almendra"),
    ("mani", "maní"),
    ("maní", "maní"),
    ("pistacho", "pistacho"),
    ("pistachos", "pistacho"),
    ("avena", "avena"),
    ("semillas de girasol", "semillas de girasol"),
    ("girasol", "semillas de girasol"),
    ("chia", "chía"),
    ("chía", "chía"),
    ("lino", "lino"),
    ("sesamo", "sésamo"),
    ("sésamo", "sésamo"),
    ("pan rallado", "pan rallado"),
    ("pan lactal", "pan"),
    ("pan", "pan"),
    ("vainillas", "vainillas"),
    ("bizcochuelo", "bizcochuelo"),
    ("galletitas", "galletitas"),
    ("corn flakes", "cereal"),
    ("fideos", "fideos"),
    ("pasta", "fideos"),
    ("noquis", "ñoquis"),
    ("ñoquis", "ñoquis"),
    ("ravioles", "ravioles"),
    ("arroz", "arroz"),
    ("polenta", "polenta"),
    ("pollo", "pollo"),
    ("pechuga", "pollo"),
    ("pechugas", "pollo"),
    ("suprema", "pollo"),
    ("muslo", "pollo"),
    ("alitas", "pollo"),
    ("pata muslo", "pollo"),
    ("gallina", "pollo"),
    ("pavo", "pavo"),
    ("cerdo", "cerdo"),
    ("bondiola", "cerdo"),
    ("matambre de cerdo", "cerdo"),
    ("matambrito", "cerdo"),
    ("carré", "cerdo"),
    ("carre", "cerdo"),
    ("costillar", "cerdo"),
    ("ribs", "cerdo"),
    ("chuleta", "cerdo"),
    ("chuleton", "cerdo"),
    ("jamon cocido", "jamón cocido"),
    ("jamón cocido", "jamón cocido"),
    ("jamon crudo", "jamón crudo"),
    ("jamón crudo", "jamón crudo"),
    ("jamon", "jamón"),
    ("jamón", "jamón"),
    ("panceta", "panceta"),
    ("tocino", "panceta"),
    ("bacon", "panceta"),
    ("chorizo colorado", "chorizo colorado"),
    ("chorizo", "chorizo"),
    ("longaniza", "longaniza"),
    ("morcilla", "morcilla"),
    ("salchicha", "salchicha"),
    ("salame", "salame"),
    ("carne picada", "carne picada"),
    ("picada", "carne picada"),
    ("carne vacuna", "carne"),
    ("carne", "carne"),
    ("nalga", "carne"),
    ("cuadril", "carne"),
    ("colita de cuadril", "carne"),
    ("bife", "carne"),
    ("bifes", "carne"),
    ("asado", "carne"),
    ("vacío", "carne"),
    ("vacio", "carne"),
    ("entraña", "carne"),
    ("entrana", "carne"),
    ("osobuco", "carne"),
    ("paleta", "carne"),
    ("matambre", "carne"),
    ("lomo", "carne"),
    ("roast beef", "carne"),
    ("cordero", "cordero"),
    ("lechon", "cerdo"),
    ("lechón", "cerdo"),
    ("pescado", "pescado"),
    ("merluza", "pescado"),
    ("salmon", "salmón"),
    ("salmón", "salmón"),
    ("atun", "atún"),
    ("atún", "atún"),
    ("caballa", "pescado"),
    ("lenguado", "pescado"),
    ("brochet", "pescado"),
    ("camaron", "camarón"),
    ("camarón", "camarón"),
    ("langostino", "langostino"),
    ("mejillon", "mejillón"),
    ("mejillón", "mejillón"),
    ("calamar", "calamar"),
    ("pulpo", "pulpo"),
    ("sardina", "sardina"),
    ("jurel", "pescado"),
    ("anchoa", "anchoa"),
    ("mostaza", "mostaza"),
    ("mayonesa", "mayonesa"),
    ("ketchup", "ketchup"),
    ("vinagre", "vinagre"),
    ("aceto", "vinagre"),
    ("limoncello", "licor"),
    ("rhum", "ron"),
    ("ron", "ron"),
    ("cognac", "licor"),
    ("aguardiente", "licor"),
    ("cafe", "café"),
    ("café", "café"),
    ("te ", "té"),
    ("yerba", "yerba"),
    ("anís", "anís"),
    ("anis estrellado", "anís"),
    ("jengibre", "jengibre"),
    ("ginger", "jengibre"),
    ("ralladura", "ralladura de cítrico"),
]

# Términos que el título suele aportar y el procedimiento omite.
TITLE_HINTS: list[tuple[str, str]] = [
    ("frutilla", "frutilla"),
    ("frambuesa", "frambuesa"),
    ("chocolate", "chocolate"),
    ("limon", "limón"),
    ("limón", "limón"),
    ("banana", "banana"),
    ("manzana", "manzana"),
    ("dulce de leche", "dulce de leche"),
    ("ricota", "ricota"),
    ("espinaca", "espinaca"),
    ("calabaza", "zapallo"),
    ("zapallo", "zapallo"),
    ("pollo", "pollo"),
    ("cerdo", "cerdo"),
    ("cordero", "cordero"),
    ("pescado", "pescado"),
    ("atun", "atún"),
    ("salmon", "salmón"),
    ("verdura", "verdura"),
    ("queso", "queso"),
    ("higo", "higo"),
    ("maracuya", "maracuyá"),
    ("mani", "maní"),
    ("nuez", "nuez"),
    ("almendra", "almendra"),
    ("zanahoria", "zanahoria"),
    ("papa", "papa"),
    ("batata", "batata"),
    ("hongos", "hongo"),
    ("champi", "champignon"),
    ("lenteja", "lenteja"),
    ("garbanzo", "garbanzo"),
    ("arroz", "arroz"),
    ("fideo", "fideos"),
    ("noqui", "ñoquis"),
    ("ñoqui", "ñoquis"),
    ("pizza", "masa de pizza"),
    ("empanada", "masa de empanada"),
    ("medialuna", "masa de medialuna"),
    ("pan ", "harina"),
    ("torta", "harina"),
    ("tarta", "harina"),
    ("budin", "harina"),
    ("budín", "harina"),
    ("galleta", "harina"),
    ("bizcoch", "harina"),
]

MEAT = {
    "pollo", "pavo", "cerdo", "jamón cocido", "jamón crudo", "jamón", "panceta",
    "chorizo colorado", "chorizo", "longaniza", "morcilla", "salchicha", "salame",
    "carne picada", "carne", "cordero", "pescado", "salmón", "atún", "camarón",
    "langostino", "mejillón", "calamar", "pulpo", "sardina", "anchoa",
}
DAIRY_EGG = {"huevo", "leche", "crema de leche", "queso crema", "queso azul", "queso rallado",
            "queso parmesano", "mozzarella", "provolone", "roquefort", "ricota", "mascarpone",
            "yogur", "manteca", "queso", "dulce de leche"}

# Si el título nombra estas proteínas y el texto no las repite, igual se agregan.
PROTEIN_TITLE = [
    ("pollo", "pollo"), ("cerdo", "cerdo"), ("cordero", "cordero"), ("vacío", "carne"),
    ("vacio", "carne"), ("asado", "carne"), ("matambre", "carne"), ("nalga", "carne"),
    ("cuadril", "carne"), ("bife", "carne"), ("osobuco", "carne"), ("bondiola", "cerdo"),
    ("pescado", "pescado"), ("merluza", "pescado"), ("salmon", "salmón"), ("atun", "atún"),
    ("langostino", "langostino"), ("camar", "camarón"), ("chorizo", "chorizo"),
    ("morcilla", "morcilla"), ("panceta", "panceta"), ("jamon", "jamón"), ("jamón", "jamón"),
]


DISH_DEFAULTS: list[tuple[str, list[str]]] = [
    ("paella", ["arroz", "azafrán", "caldo"]),
    ("risotto", ["arroz", "caldo", "cebolla"]),
    ("hummus", ["garbanzo", "limón", "aceite"]),
    ("falafel", ["garbanzo", "perejil"]),
    ("saltimbocca", ["carne", "jamón crudo", "salvia"]),
    ("rosca de reyes", ["harina", "huevo", "manteca", "fruta abrillantada"]),
    ("pan dulce", ["harina", "huevo", "frutas secas"]),
    ("croissant", ["harina", "manteca", "levadura"]),
    ("medialuna", ["harina", "manteca", "levadura"]),
    ("empanada", ["harina", "cebolla"]),
    ("pizza", ["harina", "levadura", "salsa de tomate"]),
    ("ñoqui", ["papa", "harina"]),
    ("noqui", ["papa", "harina"]),
    ("ravioles", ["harina", "huevo"]),
    ("fideos", ["fideos"]),
    ("asado", ["carne", "sal"]),
    ("parrilla", ["carne", "sal"]),
    ("milanesa", ["carne", "pan rallado", "huevo"]),
    ("guiso", ["carne", "papa", "cebolla", "zanahoria"]),
    ("locro", ["maíz blanco", "poroto", "zapallo", "chorizo"]),
    ("carbonada", ["carne", "zapallo", "choclo", "durazno"]),
    ("tortilla de papa", ["papa", "huevo", "cebolla"]),
    ("tortilla", ["huevo"]),
    ("omelette", ["huevo"]),
    ("flan", ["huevo", "leche", "azúcar"]),
    ("budin de pan", ["pan", "leche", "huevo"]),
    ("arroz con leche", ["arroz", "leche", "azúcar"]),
    ("sambayon", ["huevo", "azúcar", "vino"]),
    ("sambayón", ["huevo", "azúcar", "vino"]),
    ("clafoutis", ["huevo", "leche", "harina"]),
    ("brownie", ["chocolate", "huevo", "harina", "manteca"]),
    ("cookie", ["harina", "manteca", "azúcar"]),
    ("galleta", ["harina", "azúcar"]),
    ("alfajor", ["harina", "dulce de leche"]),
    ("cheesecake", ["queso crema", "huevo", "azúcar"]),
    ("pavlova", ["huevo", "azúcar"]),
    ("merengue", ["huevo", "azúcar"]),
    ("panqueque", ["harina", "huevo", "leche"]),
    ("crepe", ["harina", "huevo", "leche"]),
    ("waffle", ["harina", "huevo", "leche"]),
    ("chipa", ["fécula de maíz", "queso", "huevo"]),
    ("chipá", ["fécula de maíz", "queso", "huevo"]),
    ("sorrentino", ["harina", "huevo", "ricota"]),
    ("canelon", ["pasta", "salsa de tomate"]),
    ("lasagna", ["pasta", "salsa de tomate"]),
    ("lasaña", ["pasta", "salsa de tomate"]),
    ("tarta", ["harina", "manteca"]),
    ("quiche", ["huevo", "crema de leche"]),
    ("ensalada", ["aceite", "sal"]),
    ("sopa", ["caldo"]),
    ("wrap", ["pan"]),
    ("sandwich", ["pan"]),
    ("sándwich", ["pan"]),
    ("hamburguesa", ["carne picada", "pan"]),
    ("albondiga", ["carne picada", "huevo", "pan rallado"]),
    ("albóndiga", ["carne picada", "huevo", "pan rallado"]),
    ("estofado", ["carne", "cebolla", "zanahoria"]),
    ("cazuela", ["carne", "papa"]),
    ("ceviche", ["pescado", "limón", "cebolla"]),
    ("sushi", ["arroz", "pescado"]),
    ("taco", ["tortilla", "carne"]),
    ("burrito", ["tortilla", "poroto"]),
    ("chili", ["carne picada", "poroto", "tomate"]),
    ("curry", ["curry", "cebolla"]),
    ("wok", ["aceite", "verdura"]),
    ("tempura", ["harina", "huevo"]),
    ("empanada gallega", ["harina", "atún", "cebolla"]),
    ("vitel tone", ["carne", "atún", "mayonesa"]),
    ("vittel tone", ["carne", "atún", "mayonesa"]),
    ("matambre", ["carne"]),
    ("bondiola", ["cerdo"]),
    ("ribs", ["cerdo"]),
    ("cordero", ["cordero"]),
    ("pollo", ["pollo"]),
    ("berenjena", ["berenjena"]),
    ("calabaza", ["zapallo"]),
    ("hongo", ["hongo"]),
    ("humita", ["choclo", "cebolla"]),
    ("tamal", ["choclo"]),
    ("pastel de papa", ["papa", "carne picada"]),
    ("papa", ["papa"]),
    ("batata", ["batata"]),
    ("lentaja", ["lenteja"]),
    ("lenteja", ["lenteja"]),
    ("garbanzo", ["garbanzo"]),
    ("poroto", ["poroto"]),
    ("salchicha", ["salchicha"]),
    ("chorizo", ["chorizo"]),
    ("morcilla", ["morcilla"]),
    ("provoleta", ["provolone"]),
    ("fugazza", ["harina", "cebolla", "mozzarella"]),
    ("fugazzeta", ["harina", "cebolla", "mozzarella"]),
    ("napolitana", ["salsa de tomate", "jamón", "mozzarella"]),
]


def enrich_from_title(title: str, ingredients: list[str]) -> list[str]:
    found = list(ingredients)
    seen = set(found)
    title_f = fold(title)
    for key, extras in DISH_DEFAULTS:
        if fold(key) in title_f:
            for item in extras:
                if item not in seen:
                    seen.add(item)
                    found.append(item)
    if "paella" in title_f and "mixta" in title_f:
        for item in ("pollo", "camarón", "mejillón"):
            if item not in seen:
                seen.add(item)
                found.append(item)
    return found
    blob = fold(f"{title}\n{procedure}")
    found: list[str] = []
    seen = set()
    for raw, canon in INGREDIENTS:
        key = fold(raw)
        if re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", blob):
            if canon not in seen:
                seen.add(canon)
                found.append(canon)
    title_f = fold(title)
    for raw, canon in TITLE_HINTS + PROTEIN_TITLE:
        if fold(raw) in title_f and canon not in seen:
            seen.add(canon)
            found.append(canon)
    # Queso genérico si hay un queso nombrado
    if any(x.startswith("queso") or x in {"mozzarella", "provolone", "roquefort", "ricota"} for x in found):
        if "queso" not in seen:
            found.append("queso")
    found = enrich_from_title(title, found)
    return found


def extract_ingredients(title: str, procedure: str) -> list[str]:
    blob = fold(f"{title}\n{procedure}")
    found: list[str] = []
    seen = set()
    for raw, canon in INGREDIENTS:
        key = fold(raw)
        if re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", blob):
            if canon not in seen:
                seen.add(canon)
                found.append(canon)
    title_f = fold(title)
    for raw, canon in TITLE_HINTS + PROTEIN_TITLE:
        if fold(raw) in title_f and canon not in seen:
            seen.add(canon)
            found.append(canon)
    if any(x.startswith("queso") or x in {"mozzarella", "provolone", "roquefort", "ricota"} for x in found):
        if "queso" not in seen:
            found.append("queso")
    return enrich_from_title(title, found)


def is_vegetarian(ingredients: Iterable[str], title: str, category: str) -> bool:
    cat = fold(category)
    if cat in {"vegetariano", "vegano", "ensaladas"}:
        # igual chequeamos carne explícita
        pass
    ings = set(ingredients)
    if ings & MEAT:
        return False
    title_f = fold(title)
    for raw in ("higado", "molleja", "milanesa", "chorizo", "morcilla", "panceta", "bondiola", "asado", "vacio", "entrana", "pollo", "cerdo", "pescado"):
        if raw in title_f:
            return False
    for raw, canon in PROTEIN_TITLE:
        if canon in MEAT and fold(raw) in title_f:
            return False
    return True


def is_vegan(ingredients: Iterable[str], title: str, category: str) -> bool:
    if not is_vegetarian(ingredients, title, category):
        return False
    if set(ingredients) & DAIRY_EGG:
        return False
    if fold(category) == "vegano":
        return True
    blob = fold(title)
    if any(w in blob for w in ("huevo", "leche", "queso", "manteca", "crema", "yogur")):
        return False
    return True


_MIN = re.compile(r"(\d+)\s*(?:minutos?|mins?|min\b)", re.I)
_HOUR = re.compile(r"(\d+)\s*(?:horas?|hs\b)", re.I)
_RANGE = re.compile(r"(\d+)\s*(?:a|-)\s*(\d+)\s*(?:minutos?|mins?|min\b)", re.I)


def estimate_minutes(procedure: str, title: str = "") -> int:
    text = procedure or ""
    minutes = 0
    for a, b in _RANGE.findall(text):
        minutes += int(b)
    # evitar doble conteo simple: sumar menciones sueltas no cubiertas es difícil;
    # usamos la suma de números explícitos de minutos + horas, con tope razonable.
    explicit = [int(x) for x in _MIN.findall(text)]
    hours = [int(x) for x in _HOUR.findall(text)]
    if explicit:
        # reposos largos (heladera toda la noche) no cuentan como tiempo activo
        active = [m for m in explicit if m <= 180]
        minutes = sum(active) if active else max(explicit)
    minutes += sum(h * 60 for h in hours if h <= 4)
    blob = fold(text + " " + title)
    prep = 10
    if any(w in blob for w in ("amasar", "leudar", "levar", "merengue", "hojaldr")):
        prep += 20
    if "horno" in blob or "hornear" in blob:
        prep += 5
    if not explicit and not hours:
        if any(w in blob for w in ("sarten", "sartén", "saltear", "plancha")):
            minutes = 25
        elif "horno" in blob:
            minutes = 40
        else:
            minutes = 30
    total = minutes + prep
    if "toda la noche" in blob or "24 horas" in blob or "de un dia para otro" in fold(text):
        total = max(total, 90)
    return int(min(max(total, 10), 360))


def meal_tags(title: str, category: str) -> list[str]:
    cat = fold(category)
    title_f = fold(title)
    tags = []
    if cat in {"postres", "pasteleria", "helados", "mermeladas"} or any(
        w in title_f for w in ("torta", "postre", "budin", "flan", "helado", "cookie", "galleta")
    ):
        tags.append("postre")
    if cat in {"bebidas"}:
        tags.append("bebida")
    if cat in {"panes"}:
        tags.append("pan")
    if cat in {"ensaladas", "snacks"}:
        tags.append("entrada")
    if not tags:
        tags.append("plato")
    if cat in {"guisos-y-sopas"} or any(w in title_f for w in ("guiso", "sopa", "estofado")):
        tags.append("cena")
        tags.append("almuerzo")
    return tags
