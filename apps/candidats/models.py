from django.db import models

from apps.catalogue.models import Matiere, SerieBac


class Candidat(models.Model):
    class DiplomeExamen(models.TextChoices):
        BAC = "BAC", "BAC"
        DEAT = "DEAT", "DEAT"
        DT = "DT", "DT"

    class Sexe(models.TextChoices):
        FEMININ = "F", "Féminin"
        MASCULIN = "M", "Masculin"
        AUTRE = "A", "Autre"

    class TypeCandidat(models.TextChoices):
        NOUVEAU = "nouveau_bachelier", "Nouveau bachelier"
        ANCIEN = "ancien_bachelier", "Ancien bachelier"
        PARENT = "parent_tuteur", "Parent ou tuteur"

    nom = models.CharField(max_length=120)
    prenom = models.CharField(max_length=160)
    sexe = models.CharField(max_length=1, choices=Sexe.choices, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    telephone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    departement = models.CharField(max_length=120, blank=True)
    commune = models.CharField(max_length=120, blank=True)
    annee_bac = models.PositiveSmallIntegerField(default=2026)
    type_candidat = models.CharField(max_length=30, choices=TypeCandidat.choices, default=TypeCandidat.NOUVEAU)
    diplome_examen = models.CharField(max_length=10, choices=DiplomeExamen.choices, default=DiplomeExamen.BAC)
    option_diplome = models.CharField(max_length=80, blank=True)
    serie_bac = models.ForeignKey(SerieBac, on_delete=models.PROTECT)
    moyenne_generale = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    passions = models.JSONField(default=list, blank=True)
    preference_secteur = models.CharField(max_length=20, blank=True)
    preference_mode_entree = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.prenom} {self.nom}"


class NoteBac(models.Model):
    candidat = models.ForeignKey(Candidat, on_delete=models.CASCADE, related_name="notes")
    matiere = models.ForeignKey(Matiere, on_delete=models.PROTECT)
    note = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        unique_together = ("candidat", "matiere")
        ordering = ["matiere__nom"]

    def __str__(self):
        return f"{self.candidat} - {self.matiere}: {self.note}/20"
