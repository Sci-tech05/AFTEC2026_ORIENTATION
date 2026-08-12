from django.core.management.base import BaseCommand
from django.db import transaction

from apps.candidats.models import NoteBac
from apps.catalogue.models import Matiere, MatiereClassement, SerieMatiereCoefficient


ALIASES = {
    "Anglais (LV1)": "Anglais",
    "LV1": "Anglais",
}


class Command(BaseCommand):
    help = "Fusionne les alias de matieres vers les libelles utilises par les notes saisies."

    @transaction.atomic
    def handle(self, *args, **options):
        moved = 0
        deleted = 0

        for alias_name, target_name in ALIASES.items():
            alias = Matiere.objects.filter(nom=alias_name).first()
            if not alias:
                continue

            target, _ = Matiere.objects.get_or_create(nom=target_name)

            for coefficient in list(SerieMatiereCoefficient.objects.filter(matiere=alias)):
                existing = SerieMatiereCoefficient.objects.filter(serie=coefficient.serie, matiere=target).first()
                if existing:
                    coefficient.delete()
                else:
                    coefficient.matiere = target
                    coefficient.save(update_fields=["matiere"])
                    moved += 1

            for classement in list(MatiereClassement.objects.filter(matiere=alias)):
                existing = MatiereClassement.objects.filter(filiere_serie=classement.filiere_serie, matiere=target).first()
                if existing:
                    classement.delete()
                else:
                    classement.matiere = target
                    classement.save(update_fields=["matiere"])
                    moved += 1

            NoteBac.objects.filter(matiere=alias).update(matiere=target)

            if (
                not alias.matiereclassement_set.exists()
                and not alias.coefficients_series.exists()
                and not NoteBac.objects.filter(matiere=alias).exists()
            ):
                alias.delete()
                deleted += 1

        self.stdout.write(self.style.SUCCESS(f"Alias de matieres normalises: {moved} liens deplaces, {deleted} alias supprimes."))
