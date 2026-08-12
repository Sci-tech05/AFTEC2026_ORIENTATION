from django.core.management.base import BaseCommand

from apps.catalogue.models import Matiere, SerieBac, SerieMatiereCoefficient


COEFFICIENTS = {
    "A1": [
        ("Français", 5),
        ("Philo", 4),
        ("Hist-Géo", 3),
        ("Anglais", 3),
        ("Langue vivante 2", 2),
        ("Maths", 2),
        ("SVT", 2),
        ("EPS", 1),
    ],
    "A2": [
        ("Français", 4),
        ("Philo", 3),
        ("Hist-Géo", 5),
        ("Anglais", 3),
        ("Langue vivante 2", 2),
        ("Maths", 2),
        ("SVT", 2),
        ("EPS", 1),
    ],
    "B": [
        ("Français", 4),
        ("Philo", 3),
        ("Hist-Géo", 4),
        ("Anglais", 2),
        ("Economie", 4),
        ("Maths", 2),
        ("SVT", 2),
        ("EPS", 1),
    ],
    "C": [
        ("Maths", 6),
        ("PCT", 5),
        ("Français", 2),
        ("Anglais", 2),
        ("SVT", 2),
        ("Hist-Géo", 2),
        ("Philo", 2),
        ("EPS", 1),
    ],
    "D": [
        ("Maths", 4),
        ("PCT", 4),
        ("Français", 2),
        ("Anglais", 2),
        ("SVT", 5),
        ("Hist-Géo", 2),
        ("Philo", 2),
        ("EPS", 1),
    ],
    "E": [
        ("Français", 2),
        ("Maths", 5),
        ("PCT", 4),
        ("Construction Mécanique", 3),
        ("Manipulation", 3),
        ("Etude de Fabrication ou Technologie", 2),
        ("EPS", 1),
    ],
    "G1": [
        ("Techniques de base de secrétariat", 3),
        ("Français", 3),
        ("Etude de Cas", 4),
        ("Economie", 3),
        ("Anglais", 2),
        ("Compte-Rendu PV + Rapport", 3),
        ("Droit Administratif et Droit du Travail", 2),
        ("EPS", 1),
    ],
    "G2": [
        ("Français", 3),
        ("Etude de Cas", 6),
        ("Economie", 3),
        ("Anglais", 2),
        ("Maths appliquées", 3),
        ("Droit (TBAD-Finances Publiques)", 2),
        ("EPS", 1),
    ],
    "G3": [
        ("Français", 3),
        ("Etude de Cas", 6),
        ("Economie", 3),
        ("Anglais", 2),
        ("Maths appliquées", 3),
        ("Droit (TBAD-Finances Publiques)", 2),
        ("EPS", 1),
    ],
    "F1": [
        ("Travaux Pratiques", 3),
        ("Français", 2),
        ("Maths", 3),
        ("PCT", 2),
        ("Construction Mécanique", 3),
        ("Mécanique", 2),
        ("Automatique", 2),
        ("Etude d'Outillage", 2),
        ("Analyse de Fabrication", 3),
        ("EPS", 1),
    ],
    "F2": [
        ("Informatique (T.P.)", 2),
        ("Réalisation de Maquette (T.P.)", 4),
        ("Mesures et Essais de Laboratoire (T.P.)", 3),
        ("Français", 2),
        ("Maths", 3),
        ("PCT", 2),
        ("Construction Mécanique", 2),
        ("Etude d'un Système Technique", 4),
        ("EPS", 1),
    ],
    "F3": [
        ("Construction (T.P.)", 4),
        ("Mesure et Essai de Laboratoire (T.P.)", 3),
        ("Français", 2),
        ("Maths", 3),
        ("PCT", 2),
        ("Electrotechnique", 3),
        ("Etude de Système Technique", 5),
        ("EPS", 1),
    ],
    "F4": [
        ("Projet d'Exploitation (T.P.)", 3),
        ("Dessin Technique (T.P.)", 3),
        ("Français", 2),
        ("Maths", 3),
        ("PCT", 2),
        ("Résistance des Matériaux", 3),
        ("Béton Armé", 2),
        ("Métré et Etude de Prix", 2),
        ("Procédé de Construction", 2),
        ("EPS", 1),
    ],
    "EA": [
        ("Traitement de l'eau (T.P.)", 4),
        ("Réseaux hydrauliques (T.P.)", 3),
        ("Français", 2),
        ("Assainissement", 2),
        ("Maths", 3),
        ("Anglais", 1),
        ("PCT", 2),
        ("Mobilisation des ressources en eau", 4),
        ("Projet d'exploitation", 4),
        ("EPS", 1),
    ],
}


class Command(BaseCommand):
    help = "Charge les coefficients des epreuves obligatoires du BAC par serie."

    def handle(self, *args, **options):
        created = 0
        for serie_code, matieres in COEFFICIENTS.items():
            serie, _ = SerieBac.objects.get_or_create(code=serie_code, defaults={"libelle": f"BAC {serie_code}", "famille": "technique"})
            for order, (matiere_name, coefficient) in enumerate(matieres, start=1):
                matiere, _ = Matiere.objects.get_or_create(nom=matiere_name)
                _, was_created = SerieMatiereCoefficient.objects.update_or_create(
                    serie=serie,
                    matiere=matiere,
                    defaults={"coefficient": coefficient, "ordre_affichage": order},
                )
                created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Coefficients BAC charges ({created} nouveaux liens)."))
