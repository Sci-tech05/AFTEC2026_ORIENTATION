from django.contrib.admin import AdminSite

from apps.candidats.models import Candidat, NoteBac
from apps.catalogue.models import (
    CategorieEtablissement,
    Etablissement,
    Filiere,
    FiliereSerieRecommandee,
    Matiere,
    MatiereClassement,
    SerieBac,
    SerieMatiereCoefficient,
    Universite,
)


class AftecAdminSite(AdminSite):
    site_header = "AFTEC Admin"
    site_title = "AFTEC Administration"
    index_title = "Pilotage du contenu"
    login_template = "admin/login.html"
    index_template = "admin/index.html"

    def index(self, request, extra_context=None):
        recent_candidates = Candidat.objects.select_related("serie_bac").order_by("-created_at")[:5]
        recent_filieres = Filiere.objects.select_related("etablissement", "etablissement__categorie").order_by("-id")[:5]
        recent_etablissements = Etablissement.objects.select_related("categorie", "universite").order_by("-id")[:5]

        dashboard_cards = [
            {
                "label": "Candidats",
                "value": Candidat.objects.count(),
                "description": "Profils et préférences enregistrés",
            },
            {
                "label": "Filières",
                "value": Filiere.objects.count(),
                "description": "Offres et critères du catalogue",
            },
            {
                "label": "Établissements",
                "value": Etablissement.objects.count(),
                "description": "Universités, écoles et EPES",
            },
            {
                "label": "Séries BAC",
                "value": SerieBac.objects.count(),
                "description": "Référentiel des séries et coefficients",
            },
        ]

        extra_context = extra_context or {}
        extra_context.update(
            {
                "dashboard_cards": dashboard_cards,
                "recent_candidates": recent_candidates,
                "recent_filieres": recent_filieres,
                "recent_etablissements": recent_etablissements,
                "tracking_models": [
                    ("Candidats", Candidat.objects.count(), "apps.candidats.models.Candidat"),
                    ("Notes BAC", NoteBac.objects.count(), "apps.candidats.models.NoteBac"),
                    ("Catégories", CategorieEtablissement.objects.count(), "apps.catalogue.models.CategorieEtablissement"),
                    ("Universités", Universite.objects.count(), "apps.catalogue.models.Universite"),
                    ("Établissements", Etablissement.objects.count(), "apps.catalogue.models.Etablissement"),
                    ("Filières", Filiere.objects.count(), "apps.catalogue.models.Filiere"),
                    ("Séries BAC", SerieBac.objects.count(), "apps.catalogue.models.SerieBac"),
                    ("Matières BAC", SerieMatiereCoefficient.objects.count(), "apps.catalogue.models.SerieMatiereCoefficient"),
                    ("Filières recommandées", FiliereSerieRecommandee.objects.count(), "apps.catalogue.models.FiliereSerieRecommandee"),
                    ("Matières de classement", MatiereClassement.objects.count(), "apps.catalogue.models.MatiereClassement"),
                    ("Matières", Matiere.objects.count(), "apps.catalogue.models.Matiere"),
                ],
            }
        )
        return super().index(request, extra_context=extra_context)


aftec_admin_site = AftecAdminSite(name="admin")