import re

from django.core.management.base import BaseCommand, CommandError

from apps.catalogue.models import FiliereSerieRecommandee


class Command(BaseCommand):
    help = "Verifie que chaque filiere/serie dispose de matieres de classement coherentes."

    def handle(self, *args, **options):
        series_codes = {"A1", "A2", "B", "C", "D", "E", "EA", "F1", "F2", "F3", "F4", "G1", "G2", "G3", "DT", "DEAT", "Toutes series"}
        glued_serie_pattern = re.compile(
            r"(?:Maths|PCT|SVT|Francais|Français|Anglais|Economie|Cas|EST|RDM|Electrotechnique)"
            r"(?:A1|A2|B|C|D|E|EA|F[1-4]|G[1-3]|DT|DEAT)\b"
        )

        missing = []
        incoherent = []
        qs = FiliereSerieRecommandee.objects.select_related("filiere", "serie").prefetch_related("matieres_classement__matiere")
        for item in qs:
            matieres = [matiere_classement.matiere.nom for matiere_classement in item.matieres_classement.all()]
            if not matieres:
                missing.append(item)
                continue

            bad_matieres = [matiere for matiere in matieres if matiere in series_codes or glued_serie_pattern.search(matiere)]
            if bad_matieres:
                incoherent.append((item, bad_matieres))

        if missing:
            lines = [f"- {item.filiere} / {item.serie}" for item in missing]
            raise CommandError("Matieres de classement manquantes:\n" + "\n".join(lines))

        if incoherent:
            lines = [f"- {item.filiere} / {item.serie}: {', '.join(bad_matieres)}" for item, bad_matieres in incoherent]
            raise CommandError("Matieres de classement incoherentes:\n" + "\n".join(lines))

        self.stdout.write(self.style.SUCCESS("Donnees valides : toutes les filieres/series ont des matieres coherentes."))
