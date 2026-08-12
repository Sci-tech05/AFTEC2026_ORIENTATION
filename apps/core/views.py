from django.http import JsonResponse
from django.db.models import Count, Prefetch, Q
from django.shortcuts import render

from apps.catalogue.cleaning import normalize_search_text
from apps.catalogue.models import CategorieEtablissement, Etablissement, Filiere, Universite


def _match_score(tokens, field_values):
    score = 0
    for token in tokens:
        token_score = 0
        for value, weight in field_values:
            if not value:
                continue
            if token == value:
                token_score = max(token_score, 120 * weight)
                continue
            words = value.split()
            if any(word == token for word in words):
                token_score = max(token_score, 100 * weight)
                continue
            if any(word.startswith(token) for word in words):
                token_score = max(token_score, 80 * weight)
                continue
            if token in value:
                token_score = max(token_score, 35 * weight)
        if token_score == 0:
            return 0
        score += token_score
    return score


def home(request):
    stats = {
        "filieres": Filiere.objects.count(),
        "offres_orientation": Filiere.objects.filter(series_recommandees__isnull=False).distinct().count(),
        "universites": Universite.objects.count(),
        "etablissements": Etablissement.objects.count(),
        "categories": CategorieEtablissement.objects.count(),
    }
    return render(request, "core/home.html", {"stats": stats})


def models_catalog(request):
    return JsonResponse(
        {
            "object": "list",
            "data": [],
        }
    )


def etablissements(request):
    query = request.GET.get("q", "").strip()
    filieres_qs = Filiere.objects.select_related("etablissement").order_by("intitule")
    etablissements_prefetch = Etablissement.objects.select_related("categorie", "universite").prefetch_related(
        Prefetch("filieres", queryset=filieres_qs)
    )
    categories = (
        CategorieEtablissement.objects.annotate(
            etablissement_count=Count("etablissements", distinct=True),
            filiere_count=Count("etablissements__filieres", distinct=True),
        )
        .prefetch_related(Prefetch("etablissements", queryset=etablissements_prefetch))
        .all()
    )
    filtered_etablissements = Etablissement.objects.none()
    filtered_filieres = Filiere.objects.none()
    if query:
        tokens = normalize_search_text(query).split()
        filiere_matches = []
        for filiere in Filiere.objects.select_related("etablissement", "etablissement__categorie").all():
            search_score = _match_score(
                tokens,
                [
                    (normalize_search_text(filiere.intitule), 4),
                    (normalize_search_text(filiere.etablissement.nom), 3),
                    (normalize_search_text(filiere.etablissement.sigle), 3),
                    (normalize_search_text(filiere.etablissement.categorie.nom), 2),
                    (normalize_search_text(filiere.debouches), 1),
                ],
            )
            if search_score:
                filiere_matches.append((search_score, filiere))

        etablissement_matches = []
        for etablissement in Etablissement.objects.select_related("categorie", "universite").prefetch_related("filieres").all():
            search_score = _match_score(
                tokens,
                [
                    (normalize_search_text(etablissement.nom), 4),
                    (normalize_search_text(etablissement.sigle), 4),
                    (normalize_search_text(etablissement.categorie.nom), 2),
                    (normalize_search_text(etablissement.universite.nom if etablissement.universite else ""), 2),
                    (
                        normalize_search_text(" ".join(filiere.intitule for filiere in etablissement.filieres.all())),
                        1,
                    ),
                ],
            )
            if search_score:
                etablissement_matches.append((search_score, etablissement))

        filtered_etablissements = [item[1] for item in sorted(etablissement_matches, key=lambda item: (-item[0], item[1].categorie_id, item[1].nom))][:24]
        filtered_filieres = [item[1] for item in sorted(filiere_matches, key=lambda item: (-item[0], item[1].etablissement.nom, item[1].intitule))][:24]
    stats = {
        "categories": CategorieEtablissement.objects.count(),
        "etablissements": Etablissement.objects.count(),
        "filieres": Filiere.objects.count(),
        "offres_orientation": Filiere.objects.filter(series_recommandees__isnull=False).distinct().count(),
    }
    return render(
        request,
        "core/etablissements.html",
        {
            "categories": categories,
            "query": query,
            "filtered": filtered_etablissements if query else None,
            "filtered_filieres": filtered_filieres if query else None,
            "stats": stats,
        },
    )
