from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin_mixins import ExportCsvActionMixin, PremiumChangeFormMixin
from apps.core.admin_site import aftec_admin_site
from .models import Candidat, NoteBac


class NoteBacInline(admin.TabularInline):
    model = NoteBac
    extra = 0
    autocomplete_fields = ("matiere",)


@admin.register(Candidat, site=aftec_admin_site)
class CandidatAdmin(PremiumChangeFormMixin, ExportCsvActionMixin, admin.ModelAdmin):
    list_display = ("prenom", "nom", "diplome_examen_badge", "serie_bac", "moyenne_generale", "created_at")
    list_filter = ("diplome_examen", "sexe", "type_candidat", "annee_bac", "serie_bac", "preference_mode_entree", "preference_secteur")
    search_fields = ("nom", "prenom", "telephone", "email")
    inlines = [NoteBacInline]
    autocomplete_fields = ("serie_bac",)
    fieldsets = (
        ("Identité", {"fields": ("nom", "prenom", "sexe", "date_naissance", "telephone", "email")}),
        ("Scolarité", {"fields": ("departement", "commune", "annee_bac", "type_candidat", "serie_bac")}),
        ("Orientation", {"fields": ("diplome_examen", "option_diplome", "passions"), "classes": ("collapse",)}),
        ("Préférences", {"fields": (("preference_mode_entree", "preference_secteur"),), "classes": ("collapse",)}),
        ("Synthèse", {"fields": ("moyenne_generale",), "classes": ("collapse",)}),
    )
    list_select_related = ("serie_bac",)
    save_on_top = True
    list_per_page = 30
    ordering = ("-created_at",)
    readonly_fields = ("moyenne_generale",)
    date_hierarchy = "created_at"
    actions = ("export_selected_as_csv",)
    export_csv_fields = ("nom", "prenom", "sexe", "date_naissance", "telephone", "email", "departement", "commune", "annee_bac", "type_candidat", "diplome_examen", "option_diplome", "serie_bac", "moyenne_generale", "preference_secteur", "preference_mode_entree", "created_at")

    @admin.display(description="Diplôme", ordering="diplome_examen")
    def diplome_examen_badge(self, obj):
        palette = {
            obj.DiplomeExamen.BAC: ("#12304D", "#EEF4F8"),
            obj.DiplomeExamen.DEAT: ("#9A6A13", "#FFF8DF"),
            obj.DiplomeExamen.DT: ("#1F6F5B", "#E9FBF5"),
        }
        fg, bg = palette.get(obj.diplome_examen, ("#334155", "#E2E8F0"))
        return format_html(
            '<span style="display:inline-flex;align-items:center;padding:4px 10px;border-radius:999px;background:{};color:{};font-weight:700;">{}</span>',
            bg,
            fg,
            obj.get_diplome_examen_display(),
        )

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Saisis le profil candidat, ses choix et ses notes pour produire des recommandations fiables." 

    def get_premium_summary_cards(self, request, obj=None):
        if not obj:
            return []
        return [
            {"label": "Série", "value": obj.serie_bac.code},
            {"label": "Diplôme", "value": obj.get_diplome_examen_display()},
            {"label": "Moyenne", "value": f"{obj.moyenne_generale}/20" if obj.moyenne_generale is not None else "Non calculée"},
            {"label": "Préférence", "value": obj.preference_mode_entree or "Indifférent"},
        ]


@admin.register(NoteBac, site=aftec_admin_site)
class NoteBacAdmin(PremiumChangeFormMixin, ExportCsvActionMixin, admin.ModelAdmin):
    list_display = ("candidat", "matiere", "note")
    list_filter = ("matiere", "candidat__serie_bac", "candidat__diplome_examen")
    search_fields = ("candidat__nom", "candidat__prenom", "matiere__nom")
    autocomplete_fields = ("candidat", "matiere")
    fieldsets = (
        ("Note", {"fields": ("candidat", "matiere", "note")}),
    )
    list_select_related = ("candidat", "matiere")
    save_on_top = True
    actions = ("export_selected_as_csv",)
    export_csv_fields = ("candidat", "matiere", "note")

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Saisis une note BAC précise et rattache-la immédiatement au candidat et à la matière." 

    def get_premium_summary_cards(self, request, obj=None):
        if not obj:
            return []
        return [
            {"label": "Candidat", "value": f"{obj.candidat.prenom} {obj.candidat.nom}"},
            {"label": "Matière", "value": obj.matiere.nom},
            {"label": "Note", "value": f"{obj.note}/20"},
        ]

# Register your models here.
