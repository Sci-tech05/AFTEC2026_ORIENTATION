from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalogue.cleaning import BASE_SERIES, clean_serie_code
from apps.catalogue.models import FiliereSerieRecommandee, MatiereClassement, SerieBac


class Command(BaseCommand):
    help = "Fusionne les series BAC polluees par l'extraction PDF vers leurs series parentes."

    @transaction.atomic
    def handle(self, *args, **options):
        moved = 0
        deleted = 0
        renamed = 0

        for serie in list(SerieBac.objects.order_by("id")):
            cleaned_code = clean_serie_code(serie.code)
            if cleaned_code == serie.code and serie.libelle == f"BAC {serie.code}":
                continue

            if cleaned_code in {"DT", "DEAT"} and serie.code != cleaned_code:
                parent, _ = SerieBac.objects.get_or_create(
                    code=cleaned_code,
                    defaults={"libelle": f"BAC {cleaned_code}", "famille": "technique" if cleaned_code == "DT" else "agricole"},
                )
                for fsr in list(serie.filieres_recommandees.all()):
                    existing = FiliereSerieRecommandee.objects.filter(filiere=fsr.filiere, serie=parent).first()
                    if existing:
                        for matiere in fsr.matieres_classement.all():
                            MatiereClassement.objects.update_or_create(
                                filiere_serie=existing,
                                matiere=matiere.matiere,
                                defaults={"coefficient": matiere.coefficient, "ordre_affichage": matiere.ordre_affichage},
                            )
                        fsr.delete()
                    else:
                        fsr.serie = parent
                        fsr.save(update_fields=["serie"])
                    moved += 1
                serie.delete()
                deleted += 1
                continue

            if serie.code in BASE_SERIES and serie.libelle != f"BAC {serie.code}":
                serie.libelle = f"BAC {serie.code}"
                serie.save(update_fields=["libelle"])
                renamed += 1

        self.stdout.write(self.style.SUCCESS(f"Series nettoyees: {moved} liens deplaces, {deleted} series supprimees, {renamed} libelles renommes."))
