from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalogue.cleaning import clean_filiere_title, compact_spaces
from apps.catalogue.models import Filiere


SUSPECT_ENDINGS = (" et", " des", " de la", " du", " en", " Option", " Option:", " d’", " l’")
STOP_WORDS = (
    "Guide",
    "Page ",
    "N°",
    "Établissement",
    "Etablissement",
    "Offre de formation",
    "Diplôme",
    "Regime",
    "Régime",
    "Quotas",
    "Bourse",
    "Aide /",
)
NEW_OFFER_STARTS = (
    "Licence ",
    "Licence professionnelle ",
    "Licence Professionnelle ",
    "BAPES ",
    "Classe préparatoire ",
    "Classe Préparatoire ",
    "Formation ",
)


def is_suspect(title):
    return title.endswith(SUSPECT_ENDINGS)


def clean_segment(segment):
    value = compact_spaces(segment)
    if not value or any(word in value for word in STOP_WORDS):
        return ""
    if value.startswith(NEW_OFFER_STARTS):
        return ""
    if len(value) > 90:
        return ""
    return value.strip(" -—")


def continuation_from(lines, index, category_code):
    parts = []
    for line in lines[index + 1 : index + 5]:
        if not compact_spaces(line):
            continue
        if category_code == "IX":
            segment = clean_segment(line[70:150]) or clean_segment(line)
        else:
            segment = clean_segment(line[40:95])
        if not segment:
            break
        parts.append(segment)
        if not segment.endswith(SUSPECT_ENDINGS):
            break
    return " ".join(parts)


class Command(BaseCommand):
    help = "Complete les intitules de filieres coupes en fin de ligne a partir du texte du guide."

    def add_arguments(self, parser):
        parser.add_argument("--file", default="Guide_orientation_2026_2027.txt")

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"Fichier introuvable: {path}")

        lines = path.read_text(encoding="utf-8").splitlines()
        updated = 0
        unresolved = 0

        for filiere in Filiere.objects.select_related("etablissement__categorie").all():
            current = clean_filiere_title(filiere.intitule)
            if not is_suspect(current):
                if current != filiere.intitule:
                    filiere.intitule = current
                    filiere.save(update_fields=["intitule"])
                    updated += 1
                continue

            match_index = next((i for i, line in enumerate(lines) if current in line), None)
            if match_index is None:
                unresolved += 1
                continue

            suffix = continuation_from(lines, match_index, filiere.etablissement.categorie.code)
            if not suffix:
                unresolved += 1
                continue

            repaired = clean_filiere_title(compact_spaces(f"{current} {suffix}"))
            if repaired and repaired != filiere.intitule:
                filiere.intitule = repaired
                filiere.save(update_fields=["intitule"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Intitules de filieres repares: {updated}. Non resolus: {unresolved}."))
