from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin_mixins import ExportCsvActionMixin, PremiumChangeFormMixin
from apps.core.admin_site import aftec_admin_site

from .models import (
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


class MatiereClassementInline(admin.TabularInline):
    model = MatiereClassement
    extra = 1
    autocomplete_fields = ("matiere",)


@admin.register(FiliereSerieRecommandee, site=aftec_admin_site)
class FiliereSerieRecommandeeAdmin(PremiumChangeFormMixin, ExportCsvActionMixin, admin.ModelAdmin):
    list_display = ("filiere", "serie")
    list_filter = ("serie", "serie__famille", "filiere__mode_entree", "filiere__etablissement__categorie")
    search_fields = ("filiere__intitule", "serie__code")
    inlines = [MatiereClassementInline]
    autocomplete_fields = ("filiere", "serie")
    fieldsets = (
        ("Association", {"fields": ("filiere", "serie")}),
    )
    list_select_related = ("filiere", "serie")
    save_on_top = True
    actions = ("export_selected_as_csv",)
    export_csv_fields = ("filiere", "serie")

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Relie une filière à une série BAC et maintiens les matières de classement associées."

    def get_premium_summary_cards(self, request, obj=None):
        if not obj:
            return []
        return [
            {"label": "Filière", "value": obj.filiere.intitule},
            {"label": "Série", "value": obj.serie.code},
            {"label": "Matières", "value": obj.matieres_classement.count()},
        ]


class FiliereSerieInline(admin.TabularInline):
    model = FiliereSerieRecommandee
    extra = 1
    autocomplete_fields = ("serie",)


@admin.register(Filiere, site=aftec_admin_site)
class FiliereAdmin(PremiumChangeFormMixin, ExportCsvActionMixin, admin.ModelAdmin):
    list_display = ("intitule", "etablissement", "mode_entree_badge", "quota_bourse", "quota_aide_fpp", "seuil_bourse_estime", "seuil_aide_estime")
    list_filter = ("mode_entree", "diplome", "etablissement__categorie", "etablissement__secteur", "etablissement__regime", "etablissement")
    search_fields = ("intitule", "etablissement__nom", "debouches", "mots_cles")
    inlines = [FiliereSerieInline]
    autocomplete_fields = ("etablissement",)
    fieldsets = (
        ("Présentation", {"fields": ("intitule", "etablissement", "diplome")}),
        ("Admission", {"fields": ("mode_entree", ("quota_bourse", "quota_aide_fpp")), "classes": ("collapse",)}),
        ("Indicateurs", {"fields": (("seuil_bourse_estime", "seuil_aide_estime"), "regime"), "classes": ("collapse",)}),
        ("Contenu", {"fields": ("debouches", "mots_cles"), "classes": ("collapse",)}),
    )
    list_select_related = ("etablissement", "etablissement__categorie")
    save_on_top = True
    list_per_page = 30
    actions = ("export_selected_as_csv", "set_mode_classement", "set_mode_concours", "set_mode_dossier")
    export_csv_fields = ("intitule", "etablissement", "mode_entree", "diplome", "quota_bourse", "quota_aide_fpp", "seuil_bourse_estime", "seuil_aide_estime")

    @admin.action(description="Définir le mode sur Classement")
    def set_mode_classement(self, request, queryset):
        updated = queryset.update(mode_entree=Filiere.ModeEntree.CLASSEMENT)
        self.message_user(request, f"{updated} filière(s) définie(s) sur Classement.")

    @admin.action(description="Définir le mode sur Concours")
    def set_mode_concours(self, request, queryset):
        updated = queryset.update(mode_entree=Filiere.ModeEntree.CONCOURS)
        self.message_user(request, f"{updated} filière(s) définie(s) sur Concours.")

    @admin.action(description="Définir le mode sur Dossier")
    def set_mode_dossier(self, request, queryset):
        updated = queryset.update(mode_entree=Filiere.ModeEntree.DOSSIER)
        self.message_user(request, f"{updated} filière(s) définie(s) sur Dossier.")

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Structure les critères d'admission, les quotas et les associations aux séries BAC."

    def get_premium_summary_cards(self, request, obj=None):
        if not obj:
            return []
        return [
            {"label": "Établissement", "value": obj.etablissement.nom},
            {"label": "Mode", "value": obj.get_mode_entree_display()},
            {"label": "Bourse", "value": obj.quota_bourse},
            {"label": "Aide/FPP", "value": obj.quota_aide_fpp},
        ]

    @admin.display(description="Mode", ordering="mode_entree")
    def mode_entree_badge(self, obj):
        palette = {
            obj.ModeEntree.CLASSEMENT: ("#12304D", "#F4F1E8"),
            obj.ModeEntree.CONCOURS: ("#9A6A13", "#FFF8DF"),
            obj.ModeEntree.DOSSIER: ("#1F6F5B", "#E9FBF5"),
        }
        fg, bg = palette.get(obj.mode_entree, ("#334155", "#E2E8F0"))
        return format_html(
            '<span style="display:inline-flex;align-items:center;padding:4px 10px;border-radius:999px;background:{};color:{};font-weight:700;">{}</span>',
            bg,
            fg,
            obj.get_mode_entree_display(),
        )


@admin.register(Etablissement, site=aftec_admin_site)
class EtablissementAdmin(PremiumChangeFormMixin, ExportCsvActionMixin, admin.ModelAdmin):
    list_display = ("nom", "sigle", "categorie", "secteur_badge", "regime_badge", "ville")
    list_filter = ("categorie", "categorie__type", "universite", "secteur", "regime")
    search_fields = ("nom", "sigle", "ville")
    autocomplete_fields = ("categorie", "universite")
    fieldsets = (
        ("Identité", {"fields": ("nom", "sigle", "categorie")}),
        ("Localisation", {"fields": ("universite", "ville")}),
        ("Statut", {"fields": (("secteur", "regime"),), "classes": ("collapse",)}),
    )
    list_select_related = ("categorie", "universite")
    save_on_top = True
    list_per_page = 40
    actions = ("export_selected_as_csv", "set_sector_public", "set_sector_private", "set_regime_agree", "set_regime_open", "set_regime_na")
    export_csv_fields = ("nom", "sigle", "categorie", "universite", "secteur", "regime", "ville")

    @admin.action(description="Définir le secteur sur Public")
    def set_sector_public(self, request, queryset):
        updated = queryset.update(secteur=Etablissement.Secteur.PUBLIC)
        self.message_user(request, f"{updated} établissement(s) défini(s) sur Public.")

    @admin.action(description="Définir le secteur sur Privé")
    def set_sector_private(self, request, queryset):
        updated = queryset.update(secteur=Etablissement.Secteur.PRIVE)
        self.message_user(request, f"{updated} établissement(s) défini(s) sur Privé.")

    @admin.action(description="Définir le régime sur Agréé")
    def set_regime_agree(self, request, queryset):
        updated = queryset.update(regime=Etablissement.Regime.AGREE)
        self.message_user(request, f"{updated} établissement(s) défini(s) sur Agréé.")

    @admin.action(description="Définir le régime sur En ouverture")
    def set_regime_open(self, request, queryset):
        updated = queryset.update(regime=Etablissement.Regime.EN_OUVERTURE)
        self.message_user(request, f"{updated} établissement(s) défini(s) sur En ouverture.")

    @admin.action(description="Définir le régime sur Non applicable")
    def set_regime_na(self, request, queryset):
        updated = queryset.update(regime=Etablissement.Regime.NON_APPLICABLE)
        self.message_user(request, f"{updated} établissement(s) défini(s) sur Non applicable.")

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Centralise les informations d'une structure et ses relations avec l'université, le secteur et le régime."

    def get_premium_summary_cards(self, request, obj=None):
        if not obj:
            return []
        return [
            {"label": "Catégorie", "value": obj.categorie.nom},
            {"label": "Secteur", "value": obj.get_secteur_display()},
            {"label": "Régime", "value": obj.get_regime_display()},
            {"label": "Ville", "value": obj.ville or "Non renseignée"},
        ]

    @admin.display(description="Secteur", ordering="secteur")
    def secteur_badge(self, obj):
        palette = {
            obj.Secteur.PUBLIC: ("#12304D", "#EEF4F8"),
            obj.Secteur.PRIVE: ("#9A6A13", "#FFF8DF"),
        }
        fg, bg = palette.get(obj.secteur, ("#334155", "#E2E8F0"))
        return format_html(
            '<span style="display:inline-flex;align-items:center;padding:4px 10px;border-radius:999px;background:{};color:{};font-weight:700;">{}</span>',
            bg,
            fg,
            obj.get_secteur_display(),
        )

    @admin.display(description="Régime", ordering="regime")
    def regime_badge(self, obj):
        palette = {
            obj.Regime.AGREE: ("#1F6F5B", "#E9FBF5"),
            obj.Regime.EN_OUVERTURE: ("#9A6A13", "#FFF8DF"),
            obj.Regime.NON_APPLICABLE: ("#475569", "#E2E8F0"),
        }
        fg, bg = palette.get(obj.regime, ("#334155", "#E2E8F0"))
        return format_html(
            '<span style="display:inline-flex;align-items:center;padding:4px 10px;border-radius:999px;background:{};color:{};font-weight:700;">{}</span>',
            bg,
            fg,
            obj.get_regime_display(),
        )


@admin.register(CategorieEtablissement, site=aftec_admin_site)
class CategorieEtablissementAdmin(PremiumChangeFormMixin, ExportCsvActionMixin, admin.ModelAdmin):
    list_display = ("code", "nom", "type")
    list_filter = ("type",)
    search_fields = ("code", "nom")
    fieldsets = (
        ("Identité", {"fields": ("code", "nom", "type")}),
        ("Habillage", {"fields": ("logo", "description"), "classes": ("collapse",)}),
    )
    list_select_related = ()
    save_on_top = True
    actions = ("export_selected_as_csv",)
    export_csv_fields = ("code", "nom", "type", "description")

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Regroupe les grands ensembles du guide et pilote l'arborescence des établissements."

    def get_premium_summary_cards(self, request, obj=None):
        if not obj:
            return []
        return [
            {"label": "Code", "value": obj.code},
            {"label": "Type", "value": obj.get_type_display()},
            {"label": "Libellé", "value": obj.nom},
        ]


@admin.register(Universite, site=aftec_admin_site)
class UniversiteAdmin(PremiumChangeFormMixin, ExportCsvActionMixin, admin.ModelAdmin):
    list_display = ("nom", "sigle", "categorie", "ville")
    list_filter = ("categorie", "ville")
    search_fields = ("nom", "sigle", "ville")
    autocomplete_fields = ("categorie",)
    fieldsets = (
        ("Identité", {"fields": ("nom", "sigle", "categorie")}),
        ("Localisation", {"fields": ("ville",), "classes": ("collapse",)}),
    )
    list_select_related = ("categorie",)
    save_on_top = True
    list_per_page = 40
    actions = ("export_selected_as_csv",)
    export_csv_fields = ("nom", "sigle", "categorie", "ville")

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Ordonne les universités et leurs établissements rattachés avec une édition rapide." 

    def get_premium_summary_cards(self, request, obj=None):
        if not obj:
            return []
        return [
            {"label": "Catégorie", "value": obj.categorie.nom},
            {"label": "Sigle", "value": obj.sigle or "—"},
            {"label": "Ville", "value": obj.ville or "Non renseignée"},
        ]


@admin.register(Matiere, site=aftec_admin_site)
class MatiereAdmin(PremiumChangeFormMixin, ExportCsvActionMixin, admin.ModelAdmin):
    list_display = ("nom",)
    search_fields = ("nom",)
    save_on_top = True
    actions = ("export_selected_as_csv",)
    export_csv_fields = ("nom",)

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Catalogue des matières réutilisées dans les coefficients BAC et les classements." 

    def get_premium_summary_cards(self, request, obj=None):
        if not obj:
            return []
        return [{"label": "Matière", "value": obj.nom}]


class SerieMatiereCoefficientInline(admin.TabularInline):
    model = SerieMatiereCoefficient
    extra = 1
    autocomplete_fields = ("matiere",)


@admin.register(SerieBac, site=aftec_admin_site)
class SerieBacAdmin(PremiumChangeFormMixin, ExportCsvActionMixin, admin.ModelAdmin):
    list_display = ("code", "libelle", "famille", "parent")
    list_filter = ("famille", "parent")
    search_fields = ("code", "libelle")
    inlines = [SerieMatiereCoefficientInline]
    autocomplete_fields = ("parent",)
    fieldsets = (
        ("Identité", {"fields": ("code", "libelle", "famille", "parent")}),
    )
    save_on_top = True
    list_per_page = 40
    actions = ("export_selected_as_csv",)
    export_csv_fields = ("code", "libelle", "famille", "parent")

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Décrit les séries du BAC et leurs coefficients de base, avec leurs éventuelles variantes." 

    def get_premium_summary_cards(self, request, obj=None):
        if not obj:
            return []
        return [
            {"label": "Famille", "value": obj.get_famille_display()},
            {"label": "Parent", "value": obj.parent.code if obj.parent else "Aucun"},
            {"label": "Code", "value": obj.code},
        ]


@admin.register(SerieMatiereCoefficient, site=aftec_admin_site)
class SerieMatiereCoefficientAdmin(PremiumChangeFormMixin, ExportCsvActionMixin, admin.ModelAdmin):
    list_display = ("serie", "matiere", "coefficient", "ordre_affichage")
    list_filter = ("serie", "serie__famille", "coefficient")
    search_fields = ("serie__code", "matiere__nom")
    autocomplete_fields = ("serie", "matiere")
    fieldsets = (
        ("Affectation", {"fields": ("serie", "matiere")}),
        ("Pondération", {"fields": (("coefficient", "ordre_affichage"),), "classes": ("collapse",)}),
    )
    list_select_related = ("serie", "matiere")
    save_on_top = True
    actions = ("export_selected_as_csv",)
    export_csv_fields = ("serie", "matiere", "coefficient", "ordre_affichage")

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Ajuste finement les coefficients BAC de chaque matière par série." 

    def get_premium_summary_cards(self, request, obj=None):
        if not obj:
            return []
        return [
            {"label": "Série", "value": obj.serie.code},
            {"label": "Matière", "value": obj.matiere.nom},
            {"label": "Coefficient", "value": obj.coefficient},
        ]


@admin.register(MatiereClassement, site=aftec_admin_site)
class MatiereClassementAdmin(PremiumChangeFormMixin, ExportCsvActionMixin, admin.ModelAdmin):
    list_display = ("filiere_serie", "matiere", "coefficient", "ordre_affichage")
    list_filter = ("filiere_serie__serie", "filiere_serie__filiere__etablissement", "coefficient")
    search_fields = ("filiere_serie__filiere__intitule", "matiere__nom")
    autocomplete_fields = ("filiere_serie", "matiere")
    fieldsets = (
        ("Affectation", {"fields": ("filiere_serie", "matiere")}),
        ("Pondération", {"fields": (("coefficient", "ordre_affichage"),), "classes": ("collapse",)}),
    )
    list_select_related = ("filiere_serie", "matiere")
    save_on_top = True
    actions = ("export_selected_as_csv",)
    export_csv_fields = ("filiere_serie", "matiere", "coefficient", "ordre_affichage")

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Définit les matières prises en compte pour le classement d'une filière et leur poids." 

    def get_premium_summary_cards(self, request, obj=None):
        if not obj:
            return []
        return [
            {"label": "Filière", "value": obj.filiere_serie.filiere.intitule},
            {"label": "Série", "value": obj.filiere_serie.serie.code},
            {"label": "Matière", "value": obj.matiere.nom},
        ]

# Register your models here.
