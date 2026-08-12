import csv
from decimal import Decimal

from django.http import HttpResponse


class ExportCsvActionMixin:
    export_csv_fields = ()

    @staticmethod
    def _stringify(value):
        if value is None:
            return ""
        if isinstance(value, Decimal):
            return format(value, "f")
        return str(value)

    def get_export_csv_fields(self):
        return self.export_csv_fields

    @property
    def actions(self):
        base_actions = list(getattr(super(), "actions", []))
        if "export_selected_as_csv" not in base_actions:
            base_actions.append("export_selected_as_csv")
        return base_actions

    @staticmethod
    def export_selected_as_csv(modeladmin, request, queryset):
        fields = modeladmin.get_export_csv_fields()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{modeladmin.model._meta.model_name}_export.csv"'
        writer = csv.writer(response)
        writer.writerow([field.replace("__", " ").title() for field in fields])
        for obj in queryset:
            row = []
            for field in fields:
                value = obj
                for attribute in field.split("__"):
                    value = getattr(value, attribute, None)
                    if callable(value):
                        value = value()
                row.append(modeladmin._stringify(value))
            writer.writerow(row)
        return response

    export_selected_as_csv.short_description = "Exporter la sélection en CSV"


class PremiumChangeFormMixin:
    change_form_template = "admin/aftec_change_form.html"

    def get_premium_hero_title(self, request, obj=None):
        model_name = self.model._meta.verbose_name
        return f"{('Modifier' if obj else 'Créer')} {model_name}"

    def get_premium_hero_subtitle(self, request, obj=None):
        return "Un formulaire structuré pour une édition plus rapide et plus lisible."

    def get_premium_summary_cards(self, request, obj=None):
        return []

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        obj = self.get_object(request, object_id) if object_id else None
        extra_context = extra_context or {}
        extra_context.update(
            {
                "premium_hero_title": self.get_premium_hero_title(request, obj),
                "premium_hero_subtitle": self.get_premium_hero_subtitle(request, obj),
                "premium_summary_cards": self.get_premium_summary_cards(request, obj),
            }
        )
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)