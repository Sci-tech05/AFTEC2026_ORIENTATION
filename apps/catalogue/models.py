from django.db import models


class CategorieEtablissement(models.Model):
    class TypeCategorie(models.TextChoices):
        PUBLIC_UNIVERSITE = "public_universite", "Université publique"
        PUBLIC_ECOLE_INTER_ETATS = "public_ecole_inter_etats", "École inter-États"
        PRIVE_EPES = "prive_epes", "EPES privé"
        SEMECITY = "semecity", "Sèmè City"

    code = models.CharField(max_length=8, unique=True)
    nom = models.CharField(max_length=220)
    type = models.CharField(max_length=40, choices=TypeCategorie.choices)
    logo = models.ImageField(upload_to="logos/categories/", blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "catégorie d'établissement"
        verbose_name_plural = "catégories d'établissements"

    def __str__(self):
        return f"{self.code} - {self.nom}"


class Universite(models.Model):
    categorie = models.ForeignKey(CategorieEtablissement, on_delete=models.PROTECT, related_name="universites")
    nom = models.CharField(max_length=220)
    sigle = models.CharField(max_length=40, blank=True)
    ville = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.sigle or self.nom


class Etablissement(models.Model):
    class Secteur(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVE = "prive", "Privé"

    class Regime(models.TextChoices):
        AGREE = "agree", "Agréé"
        EN_OUVERTURE = "en_ouverture", "En ouverture"
        NON_APPLICABLE = "na", "Non applicable"

    universite = models.ForeignKey(Universite, on_delete=models.SET_NULL, null=True, blank=True, related_name="etablissements")
    categorie = models.ForeignKey(CategorieEtablissement, on_delete=models.PROTECT, related_name="etablissements")
    nom = models.CharField(max_length=260)
    sigle = models.CharField(max_length=80, blank=True)
    ville = models.CharField(max_length=120, blank=True)
    secteur = models.CharField(max_length=12, choices=Secteur.choices, default=Secteur.PUBLIC)
    regime = models.CharField(max_length=20, choices=Regime.choices, default=Regime.NON_APPLICABLE)

    class Meta:
        ordering = ["categorie__id", "nom"]

    def __str__(self):
        return self.sigle or self.nom


class SerieBac(models.Model):
    class Famille(models.TextChoices):
        LITTERAIRE = "litteraire", "Littéraire"
        SCIENTIFIQUE = "scientifique", "Scientifique"
        TECHNIQUE = "technique", "Technique"
        AGRICOLE = "agricole", "Agricole"
        ECONOMIQUE = "economique", "Économique"
        TOUTES = "toutes", "Toutes"

    code = models.CharField(max_length=30, unique=True)
    libelle = models.CharField(max_length=160)
    famille = models.CharField(max_length=20, choices=Famille.choices)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="sous_options")

    class Meta:
        ordering = ["famille", "code"]
        verbose_name = "série de BAC"
        verbose_name_plural = "séries de BAC"

    def __str__(self):
        return self.code


class Matiere(models.Model):
    nom = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class SerieMatiereCoefficient(models.Model):
    serie = models.ForeignKey(SerieBac, on_delete=models.CASCADE, related_name="coefficients_bac")
    matiere = models.ForeignKey(Matiere, on_delete=models.PROTECT, related_name="coefficients_series")
    coefficient = models.PositiveSmallIntegerField(default=1)
    ordre_affichage = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["serie__code", "ordre_affichage", "matiere__nom"]
        unique_together = ("serie", "matiere")
        verbose_name = "coefficient BAC par série"
        verbose_name_plural = "coefficients BAC par série"

    def __str__(self):
        return f"{self.serie} - {self.matiere} (coef. {self.coefficient})"


class Filiere(models.Model):
    class Diplome(models.TextChoices):
        LICENCE = "licence", "Licence"
        LICENCE_PRO = "licence_professionnelle", "Licence professionnelle"
        BAPES = "bapes", "BAPES"
        PREPA = "classe_preparatoire", "Classe préparatoire"
        AUTRE = "autre", "Autre"

    class ModeEntree(models.TextChoices):
        CLASSEMENT = "classement", "Classement"
        CONCOURS = "concours", "Concours"
        DOSSIER = "dossier", "Dossier"

    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, related_name="filieres")
    intitule = models.CharField(max_length=260)
    diplome = models.CharField(max_length=40, choices=Diplome.choices, default=Diplome.LICENCE)
    mode_entree = models.CharField(max_length=20, choices=ModeEntree.choices, default=ModeEntree.CLASSEMENT)
    quota_bourse = models.PositiveIntegerField(default=0)
    quota_aide_fpp = models.PositiveIntegerField(default=0)
    debouches = models.TextField(blank=True)
    regime = models.CharField(max_length=20, choices=Etablissement.Regime.choices, default=Etablissement.Regime.NON_APPLICABLE)
    seuil_bourse_estime = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    seuil_aide_estime = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    mots_cles = models.CharField(max_length=300, blank=True, help_text="Mots-clés séparés par des virgules pour les passions.")

    class Meta:
        ordering = ["etablissement__nom", "intitule"]

    def __str__(self):
        return self.intitule


class FiliereSerieRecommandee(models.Model):
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE, related_name="series_recommandees")
    serie = models.ForeignKey(SerieBac, on_delete=models.PROTECT, related_name="filieres_recommandees")

    class Meta:
        unique_together = ("filiere", "serie")
        verbose_name = "série recommandée"
        verbose_name_plural = "séries recommandées"

    def __str__(self):
        return f"{self.filiere} / {self.serie}"


class MatiereClassement(models.Model):
    filiere_serie = models.ForeignKey(FiliereSerieRecommandee, on_delete=models.CASCADE, related_name="matieres_classement")
    matiere = models.ForeignKey(Matiere, on_delete=models.PROTECT)
    coefficient = models.PositiveSmallIntegerField(default=1)
    ordre_affichage = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["ordre_affichage", "matiere__nom"]
        unique_together = ("filiere_serie", "matiere")
        verbose_name = "matière de classement"
        verbose_name_plural = "matières de classement"

    def __str__(self):
        return f"{self.matiere} (coef. {self.coefficient})"
