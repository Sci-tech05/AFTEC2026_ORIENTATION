from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.catalogue.models import (
    CategorieEtablissement,
    Etablissement,
    Filiere,
    FiliereSerieRecommandee,
    Matiere,
    MatiereClassement,
    SerieBac,
    Universite,
)


CATEGORIES = [
    ("I", "Université d'Abomey Calavi", "public_universite"),
    ("II", "Université de Parakou", "public_universite"),
    ("III", "Université Nationale des Sciences, Technologies, Ingénierie et Mathématiques", "public_universite"),
    ("IV", "Université Nationale d'Agriculture", "public_universite"),
    ("V", "Université Africaine de Développement Coopératif", "public_universite"),
    ("VI", "Institut Universitaire d'Enseignement Professionnel", "public_universite"),
    ("VII", "Établissements de Sèmè City", "semecity"),
    ("VIII", "Écoles Inter-États", "public_ecole_inter_etats"),
    ("IX", "Établissements Privés d'Enseignement Supérieur (EPES)", "prive_epes"),
]

SERIES = [
    ("A1", "BAC A1", "litteraire"),
    ("A2", "BAC A2", "litteraire"),
    ("B", "BAC B", "economique"),
    ("C", "BAC C", "scientifique"),
    ("D", "BAC D", "scientifique"),
    ("G1", "BAC G1", "economique"),
    ("G2", "BAC G2", "economique"),
    ("G3", "BAC G3", "economique"),
    ("DT/IMI", "BAC DT option IMI", "technique"),
    ("DT/CoM", "BAC DT option Commerce", "technique"),
    ("EA", "BAC Eau et Assainissement", "technique"),
]

MATIERES = [
    "Anglais",
    "Anglais (LV1)",
    "Français",
    "Maths",
    "PCT",
    "SVT",
    "Hist-Géo",
    "Philo",
    "Economie",
    "Etude de Cas",
    "Maths appliquées",
    "Technologie des systèmes informatiques",
    "Assainissement",
    "Mobilisation des ressources en eau",
    "Mercatique du tourisme",
    "Législation du tourisme",
]

FILIERES = [
    ("I", "Centre de Formation et de Recherche en matière de Population", "CEFORP", "Dynamique de Population et Planification Régionale", 5, 100, ["C", "D"], ["Anglais", "Hist-Géo", "Maths"], "développement local,population,cartographie", "Spécialiste en développement local, technicien SIG, gestionnaire de base de données.", Decimal("14.00"), Decimal("12.00")),
    ("I", "Centre Inter Facultaire de Formation et de Recherche en Environnement", "CIFRED", "Environnement, Hygiène et Santé publique", 31, 5, ["A1", "A2", "B", "C", "D", "EA"], ["Hist-Géo", "PCT", "SVT"], "sante,environnement,eau", "Formation sanitaire, ONG, police sanitaire environnementale, laboratoire de recherche.", Decimal("13.50"), Decimal("11.50")),
    ("I", "École du Patrimoine Africain", "EPA", "Gestion du patrimoine culturel", 37, 15, ["A1", "A2", "B", "C", "D", "G1", "G2", "G3", "DT/CoM"], ["Anglais", "Français", "Hist-Géo"], "arts,culture,tourisme", "Droit du patrimoine, gestion de musées, communication culturelle.", Decimal("12.50"), Decimal("10.50")),
    ("I", "École Nationale d'Économie Appliquée et de Management", "ENEAM", "Analyse Informatique et Programmation", 69, 5, ["C", "D", "DT/IMI"], ["Anglais", "Français", "Maths"], "informatique,developpement,reseaux", "Développeur d'applications web, mobile et desktop, technicien informatique.", Decimal("15.00"), Decimal("13.00")),
    ("I", "École Nationale d'Administration", "ENA", "Administration Générale", 10, 25, ["A1", "A2", "B", "C", "D", "G1", "G2", "G3"], ["Français", "Hist-Géo", "Philo"], "droit,administration,gestion", "Attaché des services administratifs, inspecteur du travail.", Decimal("13.00"), Decimal("11.00")),
    ("II", "Faculté d'Agronomie de Parakou", "FA-UP", "Sciences Agronomiques", 20, 20, ["C", "D"], ["Maths", "PCT", "SVT"], "agriculture,agronomie,environnement", "Technicien agricole, conseiller en production végétale et animale.", Decimal("13.00"), Decimal("11.00")),
    ("III", "Institut de Formation et de Recherche en Informatique", "IFRI", "Mathématiques Informatique et Applications", 35, 10, ["C"], ["Français", "Maths", "PCT"], "informatique,mathematiques,ingenierie", "Ingénieur logiciel, data analyst, développeur.", Decimal("15.50"), Decimal("13.50")),
    ("IV", "École d'Horticulture et d'Aménagement des Espaces Verts", "EHAEV", "Production Végétale", 25, 15, ["D"], ["Maths", "PCT", "SVT"], "agriculture,environnement", "Entrepreneur agricole, responsable exploitation horticole.", Decimal("12.50"), Decimal("10.50")),
    ("V", "Université Africaine de Développement Coopératif", "UADC", "Gestion des Coopératives", 10, 30, ["A1", "A2", "B", "G2"], ["Français", "Economie", "Hist-Géo"], "gestion,finance,developpement", "Gestionnaire de coopérative, chargé de projet.", Decimal("12.00"), Decimal("10.00")),
    ("VI", "Institut Universitaire d'Enseignement Professionnel", "IUEP", "Maintenance Industrielle", 15, 15, ["C", "D", "DT/IMI"], ["Maths", "PCT", "Technologie des systèmes informatiques"], "ingenierie,industrie,maintenance", "Technicien supérieur en maintenance industrielle.", Decimal("13.00"), Decimal("11.00")),
    ("VII", "Sèmè City", "SEME", "Entrepreneuriat et Innovation Numérique", 0, 20, ["C", "D", "G2", "DT/IMI"], ["Français", "Maths", "Anglais"], "informatique,entrepreneuriat,gestion", "Fondateur de startup, chargé d'innovation, chef de projet digital.", None, None),
    ("VIII", "École Inter-États des Sciences et Médecine Vétérinaires", "EISMV", "Médecine Vétérinaire", 5, 5, ["C", "D"], ["Maths", "PCT", "SVT"], "sante,agriculture,veterinaire", "Vétérinaire, inspecteur sanitaire, chercheur.", Decimal("16.00"), Decimal("14.00")),
    ("IX", "ESGIS Bénin", "ESGIS", "Licence professionnelle en Systèmes Informatiques et Logiciels", 0, 0, ["C", "D", "DT/IMI"], ["Français", "Maths", "Anglais"], "informatique,logiciel,reseaux", "Développeur logiciel, administrateur systèmes, technicien réseau.", None, None),
]


class Command(BaseCommand):
    help = "Charge un jeu de données représentatif du Guide MESRS 2026-2027."

    def handle(self, *args, **options):
        categories = {}
        for code, nom, type_ in CATEGORIES:
            categories[code], _ = CategorieEtablissement.objects.update_or_create(code=code, defaults={"nom": nom, "type": type_})

        series = {}
        for code, libelle, famille in SERIES:
            series[code], _ = SerieBac.objects.update_or_create(code=code, defaults={"libelle": libelle, "famille": famille})

        matieres = {nom: Matiere.objects.get_or_create(nom=nom)[0] for nom in MATIERES}

        universites = {}
        for code, categorie in categories.items():
            universites[code], _ = Universite.objects.update_or_create(categorie=categorie, sigle=code, defaults={"nom": categorie.nom, "ville": ""})

        for code, etab_nom, sigle, intitule, bourse, aide, serie_codes, matiere_names, mots_cles, debouches, seuil_bourse, seuil_aide in FILIERES:
            categorie = categories[code]
            etablissement, _ = Etablissement.objects.update_or_create(
                categorie=categorie,
                sigle=sigle,
                defaults={
                    "nom": etab_nom,
                    "universite": universites[code] if code not in {"VIII", "IX"} else None,
                    "secteur": "prive" if code == "IX" else "public",
                    "regime": "agree" if code == "IX" else "na",
                },
            )
            filiere, _ = Filiere.objects.update_or_create(
                etablissement=etablissement,
                intitule=intitule,
                defaults={
                    "quota_bourse": bourse,
                    "quota_aide_fpp": aide,
                    "debouches": debouches,
                    "mots_cles": mots_cles,
                    "seuil_bourse_estime": seuil_bourse,
                    "seuil_aide_estime": seuil_aide,
                    "regime": etablissement.regime,
                },
            )
            for serie_code in serie_codes:
                fsr, _ = FiliereSerieRecommandee.objects.get_or_create(filiere=filiere, serie=series[serie_code])
                for index, matiere_name in enumerate(matiere_names, start=1):
                    coef = 2 if matiere_name == "Maths" and "informatique" in mots_cles else 1
                    MatiereClassement.objects.update_or_create(
                        filiere_serie=fsr,
                        matiere=matieres[matiere_name],
                        defaults={"coefficient": coef, "ordre_affichage": index},
                    )
        self.stdout.write(self.style.SUCCESS("Jeu de données AFTEC chargé."))
