import re
import unicodedata


TRAILING_NOISE_PATTERNS = [
    r"\s+des Sciences, Technologies, Ing[ée]nierie.*$",
    r"\s+'Agriculture d['’]all Bourse$",
    r"\s+VII\s+[—-].*$",
    r"\s+VIII\s+[—-].*$",
    r"\s+avi\s+d['’]?all\s+Bourse$",
    r"\s+avi\s+d['’]?a\s+Bours?e?$",
    r"\s+avi\s+d['’]?\s*Bour?s?e?$",
    r"\s+avi\s+d\s+Bou$",
    r"\s+avi\s+Bo$",
    r"\s+avi\s+B$",
    r"\s+d\s+Bou$",
    r"\s+lavi\s+B$",
    r"\s+nt\s+nt\s+Professionnel\s+d['’]all\s+Bourse$",
    r"\s+d['’]all\s+Bourse$",
    r"\s+d['’]al\s+Bourse$",
    r"\s+d['’]a\s+Bours?e?$",
    r"\s+d['’]\s+Bour?s?e?$",
    r"\s+Bo$",
]


EXACT_FILIERE_REPLACEMENTS = {
    "Eau Hygiène et Assainissement(EHA) )": "Eau Hygiène et Assainissement (EHA)",
    "Hydrologie quantitative et Gestion intégrée des Ressources": "Hydrologie quantitative et Gestion intégrée des Ressources en eau",
    "Métiers de l’Audiovisuel et du Multimédia": "Métiers de l’Audiovisuel et du Multimédia",
    "Production et Santé animales": "Production et Santé animales",
    "Sciences du Langage et de la Communication": "Sciences du Langage et de la Communication",
    "Sciences de la Vie et de la Terre": "Sciences de la Vie et de la Terre",
    "Socio-Anthropologie": "Socio-Anthropologie",
    "Récréologie": "Récréologie",
    "Soins obstétricaux": "Soins obstétricaux",
    "Génie Biologique et Bioprocédés (GBB)": "Génie Biologique et Bioprocédés (GBB)",
    "Comptabilité": "Comptabilité",
    "Mécanique Automobile": "Mécanique Automobile",
    "Physique Chimie": "Physique Chimie",
    "Maintenance des Systèmes (Maintenance Industrielle)": "Maintenance des Systèmes (Maintenance Industrielle)",
    "Sciences et Techniques de l’Ingénieur": "Sciences et Techniques de l’Ingénieur",
    "Genre et Développement": "Genre et Développement",
    "Toutes les filières": "Toutes les filières",
    "Systèmes embarqués et Internet des Objets (SEIoT)": "Systèmes embarqués et Internet des Objets (SEIoT)",
    "Statistiques Appliquées": "Statistiques Appliquées",
    "(ESTAG) Licence professionnelle en Marketing, Communication et": "Licence professionnelle en Marketing, Communication et Commerce",
    "Comptable (IIFMEC) Licence professionnelle en Marketing Communication et": "Licence professionnelle en Marketing Communication et Commerce",
    "Ecole Supérieure d’Entrepreneuriat et de la Prospérité Licence professionnelle en Entrepreneuriat Option:": "Licence professionnelle en Entrepreneuriat Option: Finances banques assurance",
    "Licence Professionnelle en Marketing Communication et 11 Ecole de Commerce de Lyon Campus Bénin": "Licence Professionnelle en Marketing Communication et Commerce",
}


ETABLISSEMENT_REPLACEMENTS = {
    "Biosciences et Biotechnologies Appliquées (ENSBBA)": "Ecole Nationale Supérieure des Biosciences et Biotechnologies Appliquées (ENSBBA)",
    "Ecole Nationale Supérieure des": "Ecole Nationale Supérieure des Biosciences et Biotechnologies Appliquées (ENSBBA)",
    "Démographie (ENSPD)": "Ecole Nationale de Statistique, de Planification et de Démographie (ENSPD)",
    "BAPES en Histoire et Géographie BAPES En ouverture": "Ecole Supérieure pour la Formation et le Recyclage d’Enseignants (ESFRE)",
    "(ENSTIC)": "Ecole Nationale des Sciences et Techniques de l'Information et de la Communication (ENSTIC)",
    "de l'Education Physique et Sportive-INJEPS)": "Institut National de la Jeunesse, de l'Education Physique et Sportive (INJEPS)",
    "Institut National de l'Eau (INE": "Institut National de l'Eau (INE)",
    "19 l'Aménagement du Territoire et de l'Environnement-IGATE)": "Institut de Géographie, de l'Aménagement du Territoire et de l'Environnement (IGATE)",
    "II — Université de Parakou": "Université de Parakou",
    "II - Université de Parakou": "Université de Parakou",
    "VI - Institut Universitaire d'Enseigneme Professionnel VI — Institut Universitaire d'Enseigneme": "Institut Universitaire d'Enseignement Professionnel",
    "Métiers de l'agriculture VII - Établissements de Sèmè City": "Métiers de l'agriculture",
    "Ecole de l’Innovation et de l’Expertise Informatique (EPITECH) VIII - Écoles Inter-États VIII — Écoles Inter-États": "Ecole de l’Innovation et de l’Expertise Informatique (EPITECH)",
}


def compact_spaces(value):
    return re.sub(r"\s+", " ", value or "").strip()


def clean_filiere_title(value):
    cleaned = compact_spaces(value)
    for pattern in TRAILING_NOISE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = compact_spaces(cleaned)
    cleaned = cleaned.replace("(EHA) )", "(EHA)")
    cleaned = re.sub(r"\s+\)$", ")", cleaned)
    return EXACT_FILIERE_REPLACEMENTS.get(cleaned, cleaned)


def clean_etablissement_name(value):
    cleaned = compact_spaces(value)
    cleaned = ETABLISSEMENT_REPLACEMENTS.get(cleaned, cleaned)
    cleaned = re.sub(r"\s+(?:I|II|III|IV|V|VI|VII|VIII|IX)\s+[—-].*$", "", cleaned)
    cleaned = re.sub(r"\s+Filières de Formations professionnelles\s+Autre\s+En ouverture$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+(?:Licence|BAPES|Formation|Classe [Pp]réparatoire)\s+.+\s+(?:Agréé|En ouverture)$", "", cleaned, flags=re.IGNORECASE)
    return compact_spaces(cleaned)


def normalize_search_text(value):
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


BASE_SERIES = {"A1", "A2", "B", "C", "D", "E", "EA", "F1", "F2", "F3", "F4", "G1", "G2", "G3", "DT", "DEAT", "Toutes séries"}


def clean_serie_code(code):
    cleaned = compact_spaces(code)
    if cleaned in BASE_SERIES:
        return cleaned
    if cleaned.startswith("DT/"):
        return "DT"
    if cleaned.startswith("DEAT/"):
        return "DEAT"
    return cleaned
