import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import transaction

from apps.catalogue.cleaning import clean_etablissement_name, clean_filiere_title
from apps.candidats.models import Candidat
from apps.catalogue.models import (
    CategorieEtablissement,
    Etablissement,
    Filiere,
    FiliereSerieRecommandee,
    Matiere,
    MatiereClassement,
    SerieBac,
    Universite,
)


CATEGORIES = [
    ("I", "Université d'Abomey Calavi", "public_universite"),
    ("II", "Université de Parakou", "public_universite"),
    ("III", "Université Nationale des Sciences, Technologies, Ingénierie et Mathématiques", "public_universite"),
    ("IV", "Université Nationale d'Agriculture", "public_universite"),
    ("V", "Université Africaine de Développement Coopératif", "public_universite"),
    ("VI", "Institut Universitaire d'Enseignement Professionnel", "public_universite"),
    ("VII", "Établissements de Sèmè City", "semecity"),
    ("VIII", "Écoles Inter-États", "public_ecole_inter_etats"),
    ("IX", "Établissements Privés d'Enseignement Supérieur (EPES)", "prive_epes"),
]

SERIE_FAMILLES = {
    "A1": "litteraire",
    "A2": "litteraire",
    "B": "economique",
    "C": "scientifique",
    "D": "scientifique",
    "E": "scientifique",
    "F1": "technique",
    "F2": "technique",
    "F3": "technique",
    "F4": "technique",
    "EA": "technique",
    "DT": "technique",
    "DEAT": "agricole",
    "G1": "economique",
    "G2": "economique",
    "G3": "economique",
    "Toutes séries": "toutes",
}

OFFER_PATTERN = re.compile(r"(?P<bourse>\d+)\s+(?P<aide>\d+)\s+(?P<mode>Classement|Concours|Dossier)\s+(?P<rest>.*)$")
CAT_PATTERN = re.compile(r"^\s*(I{1,3}|IV|V|VI{0,3}|IX)\s+[—-]\s+(.+)$")
SERIE_TOKEN_PATTERN = re.compile(r"\b(?:A1|A2|B|C|D|E|F1|F2|F3|F4|EA|G1|G2|G3|DT(?:/[A-Za-zÉéèêûû/ -]+)?|DEAT(?:/[A-Za-zÉéèêûû/ -]+)?|Toutes séries)\b")
MATIERE_SPLIT = re.compile(r"\s*,\s*|\s+ou\s+")
EPES_OFFER_PATTERN = re.compile(
    r"^\s{20,}(?P<offre>.+?)\s{2,}(?P<diplome>Licence professionnelle|Licence|Classe préparatoire|Autre)\s{2,}(?P<regime>Agréé|En ouverture)\s*$",
    re.IGNORECASE,
)
EPES_NUMBER_PATTERN = re.compile(r"^\s*(?P<num>\d{1,3})\s+(?P<name>.+?)\s*$")


def clean(value):
    return re.sub(r"\s+", " ", value.replace("\f", " ")).strip(" -–—\t")


def category_for_line(line, current):
    match = CAT_PATTERN.match(line.replace("\f", ""))
    if not match:
        return current
    code = match.group(1)
    return code if code in {item[0] for item in CATEGORIES} else current


def get_or_create_serie(code):
    code = clean(code)
    if not code or code == "—":
        code = "Toutes séries"
    if code.startswith("DT/"):
        parent, _ = SerieBac.objects.get_or_create(code="DT", defaults={"libelle": "BAC DT", "famille": "technique"})
        return SerieBac.objects.get_or_create(code=code, defaults={"libelle": f"BAC {code}", "famille": "technique", "parent": parent})[0]
    if code.startswith("DEAT/"):
        parent, _ = SerieBac.objects.get_or_create(code="DEAT", defaults={"libelle": "BAC DEAT", "famille": "agricole"})
        return SerieBac.objects.get_or_create(code=code, defaults={"libelle": f"BAC {code}", "famille": "agricole", "parent": parent})[0]
    return SerieBac.objects.get_or_create(code=code, defaults={"libelle": f"BAC {code}", "famille": SERIE_FAMILLES.get(code, "toutes")})[0]


def get_or_create_matiere(name):
    name = clean(name)
    aliases = {
        "Anglais (LV1)": "Anglais",
        "LV1": "Anglais",
        "Hist-Géo": "Hist-Géo",
        "Hist Géo": "Hist-Géo",
        "Math": "Maths",
    }
    return Matiere.objects.get_or_create(nom=aliases.get(name, name))[0]


def extract_series(text):
    tokens = []
    for token in SERIE_TOKEN_PATTERN.findall(text):
        token = clean(token)
        if token not in tokens:
            tokens.append(token)
    return tokens or ["Toutes séries"]


def extract_matieres(text):
    if "—" in text and len(clean(text)) <= 2:
        return []
    if ":" in text:
        text = text.split(":", 1)[1]
    text = re.sub(r"\bLes trois \(03\) matières écrites\b", "Matières professionnelles", text, flags=re.I)
    text = re.sub(r"\bToutes options\b", "", text, flags=re.I)
    parts = []
    for part in MATIERE_SPLIT.split(text):
        part = clean(part)
        part = re.sub(r"\.$", "", part)
        if part and len(part) <= 70 and not part.lower().startswith(("de ", "des ", "la ", "le ")):
            parts.append(part)
    return parts[:4]


def infer_keywords(title, debouches):
    text = f"{title} {debouches}".lower()
    mapping = {
        "informatique": ["informatique", "logiciel", "réseau", "digital", "intelligence artificielle", "multimédia"],
        "sante": ["santé", "médecine", "pharmacie", "infirm", "obstétr", "biomédical"],
        "agriculture": ["agric", "rural", "végét", "animale", "foresterie", "horticulture"],
        "droit": ["droit", "juridique", "administration", "politique"],
        "gestion": ["gestion", "management", "entrepreneuriat", "marketing", "commerce"],
        "finance": ["finance", "comptab", "banque", "économie", "assurance"],
        "ingenierie": ["génie", "mécanique", "électrique", "civil", "hydraulique", "énergie"],
        "arts": ["arts", "culture", "patrimoine", "cinéma", "musique"],
        "langues": ["anglais", "allemand", "espagnol", "arabe", "lettres"],
        "environnement": ["environnement", "eau", "assainissement", "hydrologie", "climat"],
    }
    return ",".join(key for key, needles in mapping.items() if any(needle in text for needle in needles))


def diplome_from_title(title):
    lower = title.lower()
    if "classe préparatoire" in lower or "classes préparatoires" in lower:
        return "classe_preparatoire"
    if "bapes" in lower:
        return "bapes"
    if "licence professionnelle" in lower:
        return "licence_professionnelle"
    if "licence" in lower:
        return "licence"
    return "licence"


def parse_public_blocks(lines, line_categories):
    starts = []
    for index, line in enumerate(lines):
        match = OFFER_PATTERN.search(line)
        if match and index < 2145:
            starts.append((index, match))
    for pos, (start, match) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else min(len(lines), 2145)
        block = lines[start:end]
        yield start, line_categories[start], match, block


def looks_like_establishment_fragment(value):
    value = clean(value)
    if not value:
        return False
    lowered = value.lower()
    if any(token in lowered for token in ["guido", "quotas", "bourse", "fpp", "université d'", "université nationale", "epes", "page "]):
        return False
    if value in {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"}:
        return False
    return True


def normalize_etablissement_name(parts):
    cleaned = []
    for part in parts:
        part = re.sub(r"^\d{1,3}\s+", "", clean(part))
        if looks_like_establishment_fragment(part):
            cleaned.append(part)
    value = clean(" ".join(cleaned))
    value = re.sub(r"\s+\d{1,3}\s+", " ", value)
    return value[:255]


def load_public_offer(line_no, cat_code, match, block, categories, universites, current_etabs):
    category = categories.get(cat_code, categories["I"])

    first = block[0]
    filiere_parts = [first[40 : match.start()].strip()]
    etab_parts = []
    first_left = first[:40].strip()
    if looks_like_establishment_fragment(first_left):
        etab_parts.append(first_left)
    matiere_parts = [first[130:178].strip()]
    debouche_parts = [first[178:].strip()]
    bac_parts = [first[match.end("mode") : 130].strip()]

    for line in block[1:]:
        if "Guido · MESRS" in line or "Quotas" in line or "N°" in line:
            continue
        left = clean(line[:40])
        mid = clean(line[40:80])
        bac = clean(line[100:130])
        mat = clean(line[130:178])
        deb = clean(line[178:])
        if looks_like_establishment_fragment(left):
            etab_parts.append(left)
        if mid and not re.search(r"\d+\s+\d+\s+(Classement|Concours|Dossier)", mid):
            filiere_parts.append(mid)
        if bac:
            bac_parts.append(bac)
        if mat:
            matiere_parts.append(mat)
        if deb:
            debouche_parts.append(deb)

    etab_name = normalize_etablissement_name(etab_parts)
    if etab_name:
        current_etabs[cat_code] = etab_name
    else:
        etab_name = current_etabs.get(cat_code) or f"Établissement non précisé {category.code}"
    sigle_match = re.search(r"\(([^()]{2,25})\)", etab_name)
    sigle = sigle_match.group(1) if sigle_match else ""
    filiere_title = clean_filiere_title(clean(" ".join(filiere_parts)) or f"Offre ligne {line_no + 1}")
    mode = match.group("mode").lower()
    if mode == "dossier":
        mode = "dossier"
    elif mode == "concours":
        mode = "concours"
    else:
        mode = "classement"
    debouches = clean(" ".join(debouche_parts))
    bac_text = clean(" ".join(bac_parts))
    matiere_text = clean(" ".join(matiere_parts))
    series = extract_series(bac_text)
    matieres = extract_matieres(matiere_text) or ["Matière non précisée"]

    etab_name = clean_etablissement_name(etab_name)
    etablissement, _ = Etablissement.objects.update_or_create(
        categorie=category,
        nom=etab_name,
        defaults={
            "sigle": sigle,
            "universite": universites.get(category.code) if category.type == "public_universite" else None,
            "secteur": "public",
            "regime": "na",
        },
    )
    filiere, _ = Filiere.objects.update_or_create(
        etablissement=etablissement,
        intitule=filiere_title,
        defaults={
            "diplome": diplome_from_title(filiere_title),
            "mode_entree": mode,
            "quota_bourse": int(match.group("bourse")),
            "quota_aide_fpp": int(match.group("aide")),
            "debouches": debouches,
            "mots_cles": infer_keywords(filiere_title, debouches),
            "regime": "na",
        },
    )
    for serie_code in series:
        serie = get_or_create_serie(serie_code)
        fsr, _ = FiliereSerieRecommandee.objects.get_or_create(filiere=filiere, serie=serie)
        for order, matiere_name in enumerate(matieres, start=1):
            matiere = get_or_create_matiere(matiere_name)
            coef = 2 if matiere.nom in {"Maths", "Maths appliquées"} and "informatique" in filiere.mots_cles else 1
            MatiereClassement.objects.update_or_create(
                filiere_serie=fsr,
                matiere=matiere,
                defaults={"coefficient": coef, "ordre_affichage": order},
            )


def load_epes(lines, category):
    current_etab = None
    pending_offer = None
    for line in lines:
        if "Guido · MESRS" in line or "N°" in line or "IX — EPES" in line:
            continue
        number_match = EPES_NUMBER_PATTERN.match(line)
        offer_match = EPES_OFFER_PATTERN.match(line)
        if number_match and not offer_match:
            name = clean(number_match.group("name"))
            if name and not name.lower().startswith(("licence", "cycle", "apprentissage")):
                sigle_match = re.search(r"\(([^()]{2,25})\)", name)
                current_etab, _ = Etablissement.objects.update_or_create(
                    categorie=category,
                    nom=name,
                    defaults={"sigle": sigle_match.group(1) if sigle_match else "", "secteur": "prive", "regime": "agree"},
                )
                if pending_offer:
                    create_epes_filiere(current_etab, *pending_offer)
                    pending_offer = None
            continue
        if offer_match:
            offre = clean(offer_match.group("offre"))
            diplome_label = clean(offer_match.group("diplome")).lower()
            regime_label = clean(offer_match.group("regime")).lower()
            regime = "agree" if "agré" in regime_label else "en_ouverture"
            diplome = "licence_professionnelle" if "professionnelle" in diplome_label else ("classe_preparatoire" if "préparatoire" in diplome_label else ("licence" if "licence" in diplome_label else "autre"))
            if current_etab:
                create_epes_filiere(current_etab, offre, diplome, regime)
            else:
                pending_offer = (offre, diplome, regime)


def create_epes_filiere(etablissement, offre, diplome, regime):
    if not offre:
        return
    Filiere.objects.update_or_create(
        etablissement=etablissement,
        intitule=offre,
        defaults={
            "diplome": diplome,
            "mode_entree": "dossier",
            "quota_bourse": 0,
            "quota_aide_fpp": 0,
            "regime": regime,
            "debouches": "Formation privée répertoriée dans le Guide MESRS 2026-2027.",
            "mots_cles": infer_keywords(offre, ""),
        },
    )


class Command(BaseCommand):
    help = "Importe massivement le catalogue depuis Guide_orientation_2026_2027.txt."

    def add_arguments(self, parser):
        parser.add_argument("--file", default="Guide_orientation_2026_2027.txt")
        parser.add_argument("--clear", action="store_true", help="Efface le catalogue avant import.")

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"Fichier introuvable: {path}")
        if options["clear"]:
            Candidat.objects.all().delete()
            Filiere.objects.all().delete()
            Etablissement.objects.all().delete()
            Universite.objects.all().delete()
            CategorieEtablissement.objects.all().delete()
            SerieBac.objects.all().delete()
            Matiere.objects.all().delete()

        categories = {}
        universites = {}
        for code, nom, type_ in CATEGORIES:
            categorie, _ = CategorieEtablissement.objects.update_or_create(code=code, defaults={"nom": nom, "type": type_})
            categories[code] = categorie
            if type_ == "public_universite":
                universites[code], _ = Universite.objects.update_or_create(categorie=categorie, sigle=code, defaults={"nom": nom})

        lines = path.read_text(encoding="utf-8").splitlines()
        current_category = "I"
        line_categories = []
        for line in lines:
            current_category = category_for_line(line, current_category)
            line_categories.append(current_category)

        current_etabs = {}
        for start, cat_code, match, block in parse_public_blocks(lines, line_categories):
            load_public_offer(start, cat_code, match, block, categories, universites, current_etabs)

        epes_start = next((i for i, line in enumerate(lines) if "IX — EPES" in line), len(lines))
        load_epes(lines[epes_start:], categories["IX"])
        call_command("seed_bac_coefficients")
        call_command("normalize_matiere_aliases")
        call_command("clean_catalogue_labels")
        call_command("repair_filiere_titles_from_guide")
        call_command("clean_series_labels")

        self.stdout.write(
            self.style.SUCCESS(
                f"Import terminé: {CategorieEtablissement.objects.count()} catégories, "
                f"{Etablissement.objects.count()} établissements, {Filiere.objects.count()} filières, "
                f"{FiliereSerieRecommandee.objects.count()} couples filière/série."
            )
        )
