import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalogue.cleaning import clean_serie_code
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


NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = f"{{{NS['w']}}}"

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

CATEGORY_BY_TABLE = [
    (0, "I"),
    (15, "II"),
    (21, "III"),
    (27, "IV"),
    (32, "V"),
    (33, "VI"),
    (34, "VII"),
    (35, "VIII"),
    (36, "IX"),
]

SERIE_FAMILLES = {
    "A1": "litteraire",
    "A2": "litteraire",
    "B": "economique",
    "C": "scientifique",
    "D": "scientifique",
    "E": "scientifique",
    "EA": "technique",
    "F1": "technique",
    "F2": "technique",
    "F3": "technique",
    "F4": "technique",
    "G1": "economique",
    "G2": "economique",
    "G3": "economique",
    "DT": "technique",
    "DEAT": "agricole",
    "Toutes séries": "toutes",
}

SERIE_PATTERN = re.compile(r"\b(A1|A2|B|C|D|E|EA|F1|F2|F3|F4|G1|G2|G3|DT|DEAT|Toutes séries)\b", re.I)
SERIE_SPEC_PATTERN = re.compile(
    r"(?P<series>(?:A1|A2|B|C|D|E|EA|F1|F2|F3|F4|G1|G2|G3|DT(?:/[^:,]+)?|DEAT(?:/[^:,]+)?|Toutes séries)"
    r"(?:\s*,\s*(?:A1|A2|B|C|D|E|EA|F1|F2|F3|F4|G1|G2|G3|DT(?:/[^:,]+)?|DEAT(?:/[^:,]+)?|Toutes séries))*)\s*:",
    re.I,
)
MATIERE_PREFIX_PATTERN = re.compile(
    r"(?:^|\s)(?:A1|A2|B|C|D|E|EA|F1|F2|F3|F4|G1|G2|G3|DT(?:/[^:]+)?|DEAT(?:/[^:]+)?|Toutes séries)\s*:\s*",
    re.I,
)


def compact(value):
    return re.sub(r"\s+", " ", value or "").strip(" -–—\t")


def cell_text(cell):
    parts = []
    for node in cell.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag in {W + "tab", W + "br"}:
            parts.append(" ")
    return compact("".join(parts))


def docx_tables(path):
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    tables = root.findall(".//w:tbl", NS)
    for table in tables:
        rows = []
        for row in table.findall("w:tr", NS):
            rows.append([cell_text(cell) for cell in row.findall("w:tc", NS)])
        yield rows


def category_for_table(index):
    current = "I"
    for start, code in CATEGORY_BY_TABLE:
        if index >= start:
            current = code
    return current


def get_or_create_serie(code):
    code = clean_serie_code(compact(code))
    if not code or code == "—":
        code = "Toutes séries"
    return SerieBac.objects.get_or_create(
        code=code,
        defaults={"libelle": f"BAC {code}" if code != "Toutes séries" else code, "famille": SERIE_FAMILLES.get(code, "toutes")},
    )[0]


def get_or_create_matiere(name):
    name = compact(name)
    aliases = {
        "Math": "Maths",
        "Mathematiques": "Maths",
        "Mathématiques": "Maths",
        "Hist Géo": "Hist-Géo",
        "Hist-Géo": "Hist-Géo",
        "Anglais (LV1)": "Anglais",
        "LV1": "Anglais",
    }
    return Matiere.objects.get_or_create(nom=aliases.get(name, name))[0]


def extract_series(value):
    if "Toutes séries" in value:
        return ["Toutes séries"]
    found = []
    for match in SERIE_PATTERN.findall(value or ""):
        code = match.upper() if match.lower() != "toutes séries" else "Toutes séries"
        if code not in found:
            found.append(code)
    return found or ["Toutes séries"]


def extract_matieres(value):
    value = compact(value)
    if not value or value == "—":
        return []
    value = MATIERE_PREFIX_PATTERN.sub(" ", value)
    value = re.sub(r"Les trois \(03\) matières écrites", "Matières professionnelles", value, flags=re.I)
    parts = []
    for part in re.split(r"\s*,\s*|\s+ ou \s+", value):
        part = compact(part).rstrip(".")
        if part and part != "—" and len(part) <= 80 and part not in parts:
            parts.append(part)
    return parts[:5]


def clean_matiere_name(name):
    name = compact(name).rstrip(".")
    aliases = {
        "Les trois (03) matières écrites": "Matières professionnelles",
        "Math": "Maths",
        "Mathematiques": "Maths",
        "Mathématiques": "Maths",
        "Anglais (LV1)": "Anglais",
        "LV1": "Anglais",
        "Electrotech": "Electrotechnique",
        "EST": "Etude de Système Technique",
    }
    return aliases.get(name, name)


def split_matiere_list(value):
    value = compact(value)
    value = re.sub(r"Les trois \(03\) matières écrites", "Matières professionnelles", value, flags=re.I)
    parts = []
    for part in re.split(r"\s*,\s*|\s+ ou \s+", value):
        part = clean_matiere_name(part)
        if part and part != "—" and len(part) <= 80 and part not in parts:
            parts.append(part)
    return parts[:3]


def expand_serie_spec(value):
    series = []
    for token in re.split(r"\s*,\s*", compact(value)):
        token = clean_serie_code(token)
        if token and token not in series:
            series.append(token)
    return series


def normalize_serie_spec_boundaries(value):
    value = compact(value)
    if not value:
        return value

    # Les cellules Word collent parfois la dernière matière au groupe de
    # séries suivant: "PCTF3 :", "RDMF3 :", "MathsDT/EAp :".
    value = re.sub(r"\b(PCT|RDM|EST|Maths|appliquées|Electrotech|Froid)(?=(?:F[1-4]|DT/|DEAT/)\b)", r"\1 ", value)
    value = re.sub(r"\b(PCT)(?=E\s*:)", r"\1 ", value)
    value = re.sub(r"\b(PCT)(?=E\s*,)", r"\1 ", value)
    return value


def extract_matieres_by_serie(value, series_codes):
    value = normalize_serie_spec_boundaries(value)
    if not value or value == "—":
        return {}

    matches = list(SERIE_SPEC_PATTERN.finditer(value))
    if not matches:
        matieres = extract_matieres(value)[:3]
        return {serie_code: matieres for serie_code in series_codes}

    mapped = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(value)
        matieres = split_matiere_list(value[start:end])
        for serie_code in expand_serie_spec(match.group("series")):
            if matieres:
                mapped[serie_code] = matieres

    return {serie_code: mapped.get(serie_code, []) for serie_code in series_codes}


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


def diplome_from_label(title, label=""):
    text = f"{title} {label}".lower()
    if "classe préparatoire" in text:
        return "classe_preparatoire"
    if "bapes" in text:
        return "bapes"
    if "licence professionnelle" in text:
        return "licence_professionnelle"
    if "licence" in text:
        return "licence"
    return "autre" if label.lower() == "autre" else "licence"


def sigle_from_name(name):
    match = re.search(r"\(([^()]{2,25})\)", name)
    return match.group(1) if match else ""


def public_offer_data(row):
    if len(row) >= 9 and row[2] and row[3].isdigit() and row[4].isdigit() and row[5] in {"Classement", "Concours", "Dossier"}:
        return {
            "etablissement": row[1],
            "intitule": row[2],
            "bourse": row[3],
            "aide": row[4],
            "mode": row[5],
            "series": row[6],
            "matieres": row[7],
            "debouches": row[8],
        }
    if len(row) >= 8 and not row[0] and row[1] and row[2].isdigit() and row[3].isdigit() and row[4] in {"Classement", "Concours", "Dossier"}:
        return {
            "etablissement": "",
            "intitule": row[1],
            "bourse": row[2],
            "aide": row[3],
            "mode": row[4],
            "series": row[5],
            "matieres": row[6],
            "debouches": row[7],
        }
    return None


def epes_offer_data(row):
    if len(row) >= 5 and row[2] and row[3] and row[4] in {"Agréé", "En ouverture"}:
        return {
            "etablissement": row[1],
            "intitule": row[2],
            "diplome": row[3],
            "regime": row[4],
        }
    if len(row) >= 4 and not row[0] and row[1] and row[2] and row[3] in {"Agréé", "En ouverture"}:
        return {
            "etablissement": "",
            "intitule": row[1],
            "diplome": row[2],
            "regime": row[3],
        }
    return None


class Command(BaseCommand):
    help = "Importe le catalogue directement depuis les tableaux du Guide_orientation_2026_2027.docx."

    def add_arguments(self, parser):
        parser.add_argument("--file", default="Guide_orientation_2026_2027.docx")
        parser.add_argument("--clear", action="store_true", help="Remplace les établissements et filières du catalogue.")

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"Fichier introuvable: {path}")

        if options["clear"]:
            Filiere.objects.all().delete()
            Etablissement.objects.all().delete()
            Universite.objects.all().delete()
            CategorieEtablissement.objects.all().delete()

        categories = {}
        universites = {}
        for code, nom, type_ in CATEGORIES:
            categorie, _ = CategorieEtablissement.objects.update_or_create(code=code, defaults={"nom": nom, "type": type_})
            categories[code] = categorie
            if type_ == "public_universite":
                universites[code], _ = Universite.objects.update_or_create(categorie=categorie, sigle=code, defaults={"nom": nom})

        current_etab_by_category = {}
        imported = 0

        for table_index, rows in enumerate(docx_tables(path)):
            category_code = category_for_table(table_index)
            category = categories[category_code]
            current_etab = current_etab_by_category.get(category_code)

            for row in rows:
                if category_code == "IX":
                    offer = epes_offer_data(row)
                    if not offer:
                        continue
                    etab_name = compact(offer["etablissement"]) or current_etab
                    if not etab_name:
                        continue
                    current_etab = etab_name
                    current_etab_by_category[category_code] = current_etab
                    regime = "agree" if offer["regime"] == "Agréé" else "en_ouverture"
                    etablissement, _ = Etablissement.objects.update_or_create(
                        categorie=category,
                        nom=etab_name,
                        defaults={"sigle": sigle_from_name(etab_name), "secteur": "prive", "regime": regime},
                    )
                    Filiere.objects.update_or_create(
                        etablissement=etablissement,
                        intitule=compact(offer["intitule"]),
                        defaults={
                            "diplome": diplome_from_label(offer["intitule"], offer["diplome"]),
                            "mode_entree": "dossier",
                            "quota_bourse": 0,
                            "quota_aide_fpp": 0,
                            "regime": regime,
                            "debouches": "Formation privée répertoriée dans le Guide MESRS 2026-2027.",
                            "mots_cles": infer_keywords(offer["intitule"], ""),
                        },
                    )
                    imported += 1
                    continue

                offer = public_offer_data(row)
                if not offer:
                    continue

                etab_name = compact(offer["etablissement"]) or current_etab
                if not etab_name:
                    continue
                current_etab = etab_name
                current_etab_by_category[category_code] = current_etab
                etablissement, _ = Etablissement.objects.update_or_create(
                    categorie=category,
                    nom=etab_name,
                    defaults={
                        "sigle": sigle_from_name(etab_name),
                        "universite": universites.get(category_code) if category.type == "public_universite" else None,
                        "secteur": "public",
                        "regime": "na",
                    },
                )
                title = compact(offer["intitule"])
                debouches = compact(offer["debouches"])
                filiere, _ = Filiere.objects.update_or_create(
                    etablissement=etablissement,
                    intitule=title,
                    defaults={
                        "diplome": diplome_from_label(title),
                        "mode_entree": offer["mode"].lower(),
                        "quota_bourse": int(offer["bourse"]),
                        "quota_aide_fpp": int(offer["aide"]),
                        "debouches": debouches,
                        "mots_cles": infer_keywords(title, debouches),
                        "regime": "na",
                    },
                )
                series = extract_series(offer["series"])
                matieres_by_serie = extract_matieres_by_serie(offer["matieres"], series)
                for serie_code in series:
                    serie = get_or_create_serie(serie_code)
                    fsr, _ = FiliereSerieRecommandee.objects.get_or_create(filiere=filiere, serie=serie)
                    matieres = matieres_by_serie.get(serie_code) or ["Matière non précisée"]
                    fsr.matieres_classement.all().delete()
                    for order, matiere_name in enumerate(matieres, start=1):
                        matiere = get_or_create_matiere(matiere_name)
                        MatiereClassement.objects.update_or_create(
                            filiere_serie=fsr,
                            matiere=matiere,
                            defaults={"coefficient": 1, "ordre_affichage": order},
                        )
                imported += 1

        call_command("seed_bac_coefficients")
        call_command("normalize_matiere_aliases")

        self.stdout.write(
            self.style.SUCCESS(
                f"Import DOCX terminé: {imported} filières, "
                f"{Etablissement.objects.count()} établissements, {FiliereSerieRecommandee.objects.count()} couples filière/série."
            )
        )
