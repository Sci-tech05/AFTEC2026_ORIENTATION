from dataclasses import dataclass
from decimal import Decimal

from apps.catalogue.models import FiliereSerieRecommandee


@dataclass
class Recommendation:
    filiere: object
    moyenne_classement: Decimal | None
    details: list[dict]
    missing_matieres: list[str]
    score_passions: int
    indicateur: str
    composite_score: Decimal = Decimal("0")

    @property
    def complete(self):
        return not self.missing_matieres and self.moyenne_classement is not None


def _indicateur_chance(filiere, moyenne):
    if moyenne is None:
        return "Informations incomplètes"
    if filiere.seuil_bourse_estime is None and filiere.seuil_aide_estime is None:
        if moyenne > Decimal("16.99"):
            return "Classement possible"
        return "Tente ta chance"
    if filiere.seuil_bourse_estime is not None and moyenne >= filiere.seuil_bourse_estime:
        return "Chances élevées d'être boursier"
    if filiere.seuil_aide_estime is not None and moyenne >= filiere.seuil_aide_estime:
        return "Chances moyennes pour l'aide/FPP"
    return "Chances faibles selon les seuils indicatifs"


def _score_passions(filiere, passions):
    haystack = f"{filiere.intitule} {filiere.debouches} {filiere.mots_cles}".lower()
    return sum(1 for passion in passions if passion.lower() in haystack)


def _matches_mode_entree(filiere, mode_entree):
    if not mode_entree:
        return True
    return filiere.mode_entree == mode_entree


def _matches_secteur(filiere, secteur):
    if not secteur:
        return True
    return filiere.etablissement.secteur == secteur


def calculer_recommandations(candidat, limit=None):
    notes = {note.matiere_id: note.note for note in candidat.notes.select_related("matiere")}
    passions = candidat.passions or []
    recommandations = []
    mode_entree = (candidat.preference_mode_entree or "").strip().lower()
    secteur = (candidat.preference_secteur or "").strip().lower()

    qs = (
        FiliereSerieRecommandee.objects.filter(serie=candidat.serie_bac)
        .select_related("filiere", "filiere__etablissement", "filiere__etablissement__categorie", "serie")
        .prefetch_related("matieres_classement__matiere")
    )
    for filiere_serie in qs:
        if not _matches_mode_entree(filiere_serie.filiere, mode_entree):
            continue
        if not _matches_secteur(filiere_serie.filiere, secteur):
            continue
        total = Decimal("0")
        total_coef = Decimal("0")
        details = []
        missing = []
        for item in filiere_serie.matieres_classement.all():
            note = notes.get(item.matiere_id)
            coef = Decimal(item.coefficient)
            contribution = None
            if note is None:
                missing.append(item.matiere.nom)
            else:
                contribution = note * coef
                total += contribution
                total_coef += coef
            details.append({"matiere": item.matiere.nom, "coefficient": item.coefficient, "note": note, "contribution": contribution})

        moyenne = (total / total_coef).quantize(Decimal("0.01")) if total_coef and not missing else None
        filiere = filiere_serie.filiere
        recommandations.append(
            Recommendation(
                filiere=filiere,
                moyenne_classement=moyenne,
                details=details,
                missing_matieres=missing,
                score_passions=_score_passions(filiere, passions),
                indicateur=_indicateur_chance(filiere, moyenne),
                composite_score=( (moyenne * Decimal("10")) if moyenne is not None else Decimal("0")) + Decimal(_score_passions(filiere, passions)),
            )
        )

    # Prioriser d'abord les filières pour lesquelles le candidat a exprimé des centres d'intérêt,
    # puis les filières avec une moyenne de classement calculée, puis trier par moyenne.
    # Trier par priorité: complétude des données, puis par score composite
    recommandations.sort(key=lambda item: (item.complete, item.composite_score), reverse=True)
    return recommandations[:limit] if limit else recommandations
