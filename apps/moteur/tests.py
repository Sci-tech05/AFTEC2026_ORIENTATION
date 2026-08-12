from decimal import Decimal

from django.test import TestCase

from apps.candidats.models import Candidat, NoteBac
from apps.catalogue.models import Etablissement, Filiere, FiliereSerieRecommandee, Matiere, MatiereClassement, SerieBac, CategorieEtablissement
from apps.moteur.services import calculer_recommandations


class MoteurOrientationTests(TestCase):
    def setUp(self):
        categorie = CategorieEtablissement.objects.create(code="I", nom="Université d'Abomey Calavi", type="public_universite")
        etablissement = Etablissement.objects.create(categorie=categorie, nom="FAST", sigle="FAST")
        etablissement_concours = Etablissement.objects.create(categorie=categorie, nom="ENSET", sigle="ENSET", secteur=Etablissement.Secteur.PRIVE)
        self.serie = SerieBac.objects.create(code="C", libelle="BAC C", famille="scientifique")
        maths = Matiere.objects.create(nom="Maths")
        francais = Matiere.objects.create(nom="Français")
        pct = Matiere.objects.create(nom="PCT")
        filiere_classement = Filiere.objects.create(
            etablissement=etablissement,
            intitule="Mathématiques Informatique et Applications",
            quota_bourse=10,
            quota_aide_fpp=5,
            mode_entree=Filiere.ModeEntree.CLASSEMENT,
            seuil_bourse_estime=Decimal("14.00"),
            seuil_aide_estime=Decimal("12.00"),
            mots_cles="informatique,mathematiques",
        )
        filiere_concours = Filiere.objects.create(
            etablissement=etablissement_concours,
            intitule="Electrotechnique",
            quota_bourse=8,
            quota_aide_fpp=2,
            mode_entree=Filiere.ModeEntree.CONCOURS,
            seuil_bourse_estime=Decimal("15.50"),
            seuil_aide_estime=Decimal("13.50"),
        )
        fsr_classement = FiliereSerieRecommandee.objects.create(filiere=filiere_classement, serie=self.serie)
        fsr_concours = FiliereSerieRecommandee.objects.create(filiere=filiere_concours, serie=self.serie)
        for fsr in (fsr_classement, fsr_concours):
            MatiereClassement.objects.create(filiere_serie=fsr, matiere=maths, coefficient=2, ordre_affichage=1)
            MatiereClassement.objects.create(filiere_serie=fsr, matiere=francais, coefficient=1, ordre_affichage=2)
            MatiereClassement.objects.create(filiere_serie=fsr, matiere=pct, coefficient=1, ordre_affichage=3)
        self.matieres = {"maths": maths, "francais": francais, "pct": pct}
        self.filiere_classement = filiere_classement
        self.filiere_concours = filiere_concours

    def test_calcule_la_moyenne_de_classement_ponderee(self):
        candidat = Candidat.objects.create(nom="ADJOVI", prenom="Ariane", serie_bac=self.serie, passions=["informatique"])
        NoteBac.objects.create(candidat=candidat, matiere=self.matieres["maths"], note=Decimal("15"))
        NoteBac.objects.create(candidat=candidat, matiere=self.matieres["francais"], note=Decimal("12"))
        NoteBac.objects.create(candidat=candidat, matiere=self.matieres["pct"], note=Decimal("13"))

        result = calculer_recommandations(candidat)[0]

        self.assertEqual(result.moyenne_classement, Decimal("13.75"))
        self.assertEqual(result.indicateur, "Chances moyennes pour l'aide/FPP")

    def test_signale_les_matieres_manquantes(self):
        candidat = Candidat.objects.create(nom="HOUNTON", prenom="Marc", serie_bac=self.serie)
        NoteBac.objects.create(candidat=candidat, matiere=self.matieres["maths"], note=Decimal("15"))

        result = calculer_recommandations(candidat)[0]

        self.assertIsNone(result.moyenne_classement)
        self.assertEqual(result.missing_matieres, ["Français", "PCT"])

    def test_filtre_les_recommandations_selon_le_mode_d_entree_choisi(self):
        candidat = Candidat.objects.create(
            nom="ADJOVI",
            prenom="Ariane",
            serie_bac=self.serie,
            preference_mode_entree="classement",
            preference_secteur="public",
        )
        NoteBac.objects.create(candidat=candidat, matiere=self.matieres["maths"], note=Decimal("15"))
        NoteBac.objects.create(candidat=candidat, matiere=self.matieres["francais"], note=Decimal("12"))
        NoteBac.objects.create(candidat=candidat, matiere=self.matieres["pct"], note=Decimal("13"))

        resultats = calculer_recommandations(candidat)

        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats[0].filiere, self.filiere_classement)

    def test_exclut_les_filieres_qui_ne_correspondent_pas_au_secteur_choisi(self):
        candidat = Candidat.objects.create(
            nom="ADJOVI",
            prenom="Ariane",
            serie_bac=self.serie,
            preference_secteur="prive",
        )
        NoteBac.objects.create(candidat=candidat, matiere=self.matieres["maths"], note=Decimal("15"))
        NoteBac.objects.create(candidat=candidat, matiere=self.matieres["francais"], note=Decimal("12"))
        NoteBac.objects.create(candidat=candidat, matiere=self.matieres["pct"], note=Decimal("13"))

        resultats = calculer_recommandations(candidat)

        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats[0].filiere, self.filiere_concours)

# Create your tests here.
