import json
import unicodedata

from django.shortcuts import get_object_or_404, redirect, render

from apps.catalogue.cleaning import BASE_SERIES
from apps.catalogue.models import MatiereClassement, SerieBac
from apps.catalogue.services import calculer_moyenne_generale
from apps.moteur.services import calculer_recommandations
from .forms import BAC_SERIES, DEAT_OPTIONS, DT_OPTIONS, OrientationForm
from .models import Candidat


DEAT_OPTION_PATTERNS = {
    "AER": ["aer", "amenagement", "eha", "eau", "assainissement", "pe"],
    "Foresterie": ["foresterie", "forest", "fores"],
    "PV": ["pv", "production vegetale", "agriculture speciale"],
    "Production Animale": ["pa", "production animale", "zootechnie"],
    "Pêche et aquaculture": ["peche", "aquaculture"],
    "Nutrition et Technologie Alimentaire": ["nutrition", "technologie alimentaire", "alimentaire"],
}

DT_OPTION_PATTERNS = {
    "Arts textile": ["art", "textile", "dessin", "histoire de l'art"],
    "BTP": ["btp", "genie civil", "beton", "assainissement"],
    "CEMS": ["cems"],
    "CoM": ["com", "commerce", "commerciale", "mercatique", "marketing"],
    "Communication graphique": ["communication graphique", "graphique", "art applique"],
    "DPB": ["dpb"],
    "DWM": ["dwm", "multimedia", "internet"],
    "EAp": ["eap", "electronique", "etude electronique"],
    "EFS": ["efs", "economie familiale", "sociale"],
    "EL": ["el", "electrotech", "electrotechnique"],
    "FC": ["fc", "froid", "climatisation"],
    "FM": ["fm", "fabrication mecanique", "construction mecanique"],
    "HR": ["hr", "hotellerie", "restauration"],
    "IMI": ["imi", "informatique", "maintenance industrielle"],
    "MA": ["ma", "mecanique automobile", "automobile"],
    "MAO": ["mao"],
    "Musique": ["musique", "musicologie"],
    "OG": ["og", "geometrique", "geomatique", "architecture", "urbanisme"],
    "PM": ["pm", "productique"],
    "Tourisme": ["tourisme"],
}


def normalize_text(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return value.casefold()


def option_matiere_ids(serie, option, diplome):
    matieres = list(
        MatiereClassement.objects.filter(filiere_serie__serie=serie)
        .select_related("matiere")
        .values_list("matiere_id", "matiere__nom")
        .distinct()
    )
    common_patterns = {"francais", "anglais", "maths", "pct", "culture generale"}
    option_patterns = []
    if diplome == "DEAT":
        common_patterns |= {"svt", "matieres professionnelles", "agriculture generale"}
        option_patterns = DEAT_OPTION_PATTERNS.get(option, [])
    elif diplome == "DT":
        option_patterns = DT_OPTION_PATTERNS.get(option, [])

    selected_ids = set()
    for matiere_id, matiere_nom in matieres:
        normalized_name = normalize_text(matiere_nom)
        matches_option = any(pattern in normalized_name for pattern in option_patterns)
        has_embedded_option = "dt/" in normalized_name or "deat/" in normalized_name
        common_variants = common_patterns | {"anglais (lv1)", "francais c", "maths appliquees"}
        matches_common = normalized_name in common_variants
        if matches_option or (matches_common and not has_embedded_option):
            selected_ids.add(matiere_id)
    if not selected_ids:
        selected_ids = {matiere_id for matiere_id, _ in matieres}
    return sorted(selected_ids)


def orientation_create(request):
    if request.method == "POST":
        form = OrientationForm(request.POST)
        if form.is_valid():
            candidat = form.save()
            return redirect("candidats:resultats", pk=candidat.pk)
    else:
        form = OrientationForm()
    series_payload = {}
    exam_payload = {"BAC": [], "DEAT": [], "DT": []}
    for serie in SerieBac.objects.filter(filieres_recommandees__isnull=False, code__in=BASE_SERIES).distinct().prefetch_related("coefficients_bac__matiere"):
        matiere_ids = set(serie.coefficients_bac.values_list("matiere_id", flat=True))
        if not matiere_ids:
            matiere_ids.update(MatiereClassement.objects.filter(filiere_serie__serie=serie).values_list("matiere_id", flat=True))
        series_payload[str(serie.id)] = {"code": serie.code, "matieres": sorted(matiere_ids)}
        if serie.code in BAC_SERIES:
            exam_payload["BAC"].append({"value": serie.code, "label": serie.code, "serie_id": serie.id, "matieres": sorted(matiere_ids)})
        elif serie.code == "DEAT":
            exam_payload["DEAT"] = [
                {"value": value, "label": label, "serie_id": serie.id, "matieres": option_matiere_ids(serie, value, "DEAT")}
                for value, label in DEAT_OPTIONS
            ]
        elif serie.code == "DT":
            exam_payload["DT"] = [
                {"value": value, "label": label, "serie_id": serie.id, "matieres": option_matiere_ids(serie, value, "DT")}
                for value, label in DT_OPTIONS
            ]
    return render(
        request,
        "candidats/orientation_form.html",
        {
            "form": form,
            "matieres": form.note_matieres,
            "note_fields": form.note_fields,
            "series_payload": json.dumps(series_payload),
            "exam_payload": json.dumps(exam_payload),
        },
    )


def resultats(request, pk):
    candidat = get_object_or_404(Candidat.objects.select_related("serie_bac").prefetch_related("notes__matiere"), pk=pk)
    recommandations = calculer_recommandations(candidat)
    moyenne_generale, details_generale = calculer_moyenne_generale(candidat)
    return render(
        request,
        "candidats/resultats.html",
        {"candidat": candidat, "recommandations": recommandations, "moyenne_generale": moyenne_generale, "details_generale": details_generale},
    )
