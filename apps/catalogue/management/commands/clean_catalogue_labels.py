from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalogue.cleaning import clean_etablissement_name, clean_filiere_title
from apps.catalogue.models import Etablissement, Filiere


class Command(BaseCommand):
    help = "Nettoie les libelles parasites produits par l'extraction PDF du guide."

    @transaction.atomic
    def handle(self, *args, **options):
        updated_etabs = 0
        updated_filieres = 0
        merged_etabs = 0

        for etablissement in Etablissement.objects.all():
            cleaned = clean_etablissement_name(etablissement.nom)
            if cleaned and cleaned != etablissement.nom:
                etablissement.nom = cleaned
                etablissement.save(update_fields=["nom"])
                updated_etabs += 1

        for etablissement in list(Etablissement.objects.order_by("categorie_id", "nom", "id")):
            duplicate = (
                Etablissement.objects.filter(categorie=etablissement.categorie, nom=etablissement.nom)
                .exclude(pk=etablissement.pk)
                .order_by("id")
                .first()
            )
            if not duplicate:
                continue
            keeper = duplicate if duplicate.id < etablissement.id else etablissement
            removed = etablissement if keeper == duplicate else duplicate
            Filiere.objects.filter(etablissement=removed).update(etablissement=keeper)
            if not keeper.sigle and removed.sigle:
                keeper.sigle = removed.sigle
                keeper.save(update_fields=["sigle"])
            removed.delete()
            merged_etabs += 1

        for filiere in Filiere.objects.all():
            cleaned = clean_filiere_title(filiere.intitule)
            if cleaned and cleaned != filiere.intitule:
                filiere.intitule = cleaned
                filiere.save(update_fields=["intitule"])
                updated_filieres += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Libelles nettoyes: {updated_etabs} etablissements, {updated_filieres} filieres, {merged_etabs} doublons fusionnes."
            )
        )
