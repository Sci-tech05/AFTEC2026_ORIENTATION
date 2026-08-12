import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.catalogue.models import CategorieEtablissement, Etablissement, Filiere, FiliereSerieRecommandee, Matiere, MatiereClassement, SerieBac


class Command(BaseCommand):
    help = "Importe un fichier JSON structuré issu du Guide MESRS."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Chemin du fichier JSON à importer.")

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"Fichier introuvable: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data:
            categorie, _ = CategorieEtablissement.objects.get_or_create(
                code=row["categorie_code"],
                defaults={"nom": row["categorie_nom"], "type": row.get("categorie_type", "public_universite")},
            )
            etablissement, _ = Etablissement.objects.get_or_create(
                categorie=categorie,
                nom=row["etablissement"],
                defaults={"sigle": row.get("sigle", ""), "secteur": row.get("secteur", "public"), "regime": row.get("regime", "na")},
            )
            filiere, _ = Filiere.objects.update_or_create(
                etablissement=etablissement,
                intitule=row["filiere"],
                defaults={
                    "quota_bourse": row.get("bourse", 0) or 0,
                    "quota_aide_fpp": row.get("aide_fpp", 0) or 0,
                    "mode_entree": row.get("mode_entree", "classement"),
                    "debouches": row.get("debouches", ""),
                    "mots_cles": row.get("mots_cles", ""),
                },
            )
            for bloc in row.get("series", []):
                serie, _ = SerieBac.objects.get_or_create(code=bloc["code"], defaults={"libelle": bloc["code"], "famille": bloc.get("famille", "toutes")})
                fsr, _ = FiliereSerieRecommandee.objects.get_or_create(filiere=filiere, serie=serie)
                for index, item in enumerate(bloc.get("matieres", []), start=1):
                    matiere, _ = Matiere.objects.get_or_create(nom=item["nom"] if isinstance(item, dict) else item)
                    coefficient = item.get("coefficient", 1) if isinstance(item, dict) else 1
                    MatiereClassement.objects.update_or_create(
                        filiere_serie=fsr,
                        matiere=matiere,
                        defaults={"coefficient": coefficient, "ordre_affichage": index},
                    )
        self.stdout.write(self.style.SUCCESS(f"Import terminé: {len(data)} lignes traitées."))
