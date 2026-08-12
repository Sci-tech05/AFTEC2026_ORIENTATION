from decimal import Decimal

from django import forms
from django.db.models import Count

from apps.catalogue.cleaning import BASE_SERIES
from apps.catalogue.models import Matiere, SerieBac
from apps.catalogue.services import calculer_moyenne_generale
from .models import Candidat, NoteBac


PASSIONS = [
    ("informatique", "Informatique"),
    ("ingenierie", "Ingénierie"),
    ("sante", "Santé"),
    ("agriculture", "Agriculture"),
    ("droit", "Droit"),
    ("arts", "Arts et culture"),
    ("langues", "Langues"),
    ("gestion", "Gestion"),
    ("finance", "Finance"),
    ("environnement", "Environnement"),
]

BAC_SERIES = sorted(BASE_SERIES - {"DT", "DEAT", "Toutes séries"})

DEAT_OPTIONS = [
    ("AER", "AER"),
    ("Foresterie", "Foresterie"),
    ("PV", "PV"),
    ("Production Animale", "Production Animale"),
    ("Pêche et aquaculture", "Pêche et aquaculture"),
    ("Nutrition et Technologie Alimentaire", "Nutrition et Technologie Alimentaire"),
]

DT_OPTIONS = [
    ("Arts textile", "Arts textile"),
    ("BTP", "BTP"),
    ("CEMS", "CEMS"),
    ("CoM", "CoM"),
    ("Communication graphique", "Communication graphique"),
    ("DPB", "DPB"),
    ("DWM", "DWM"),
    ("EAp", "EAp"),
    ("EFS", "EFS"),
    ("EL", "EL"),
    ("FC", "FC"),
    ("FM", "FM"),
    ("HR", "HR"),
    ("IMI", "IMI"),
    ("MA", "MA"),
    ("MAO", "MAO"),
    ("Musique", "Musique"),
    ("OG", "OG"),
    ("PM", "PM"),
    ("Tourisme", "Tourisme"),
]


class OrientationForm(forms.ModelForm):
    option_diplome = forms.ChoiceField(choices=[("", "Choisir une option")], required=True)
    passions = forms.MultipleChoiceField(choices=PASSIONS, widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = Candidat
        fields = [
            "nom",
            "prenom",
            "sexe",
            "date_naissance",
            "telephone",
            "departement",
            "annee_bac",
            "type_candidat",
            "diplome_examen",
            "option_diplome",
            "serie_bac",
            "passions",
            "preference_secteur",
            "preference_mode_entree",
        ]
        widgets = {
            "date_naissance": forms.DateInput(attrs={"type": "date"}),
            "annee_bac": forms.NumberInput(attrs={"min": "2000", "max": "2030"}),
            "serie_bac": forms.HiddenInput(),
            "preference_mode_entree": forms.Select(
                choices=[("", "Indifférent"), ("classement", "Classement"), ("concours", "Concours"), ("dossier", "Dossier")]
            ),
            "preference_secteur": forms.Select(choices=[("", "Indifférent"), ("public", "Public"), ("prive", "Privé")]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["serie_bac"].queryset = (
            SerieBac.objects.annotate(n=Count("filieres_recommandees"))
            .filter(n__gt=0, code__in=BASE_SERIES)
            .order_by("code")
        )
        self.fields["serie_bac"].empty_label = "Choisir ma série"
        self.fields["serie_bac"].required = False
        bac_choices = [(serie.code, serie.code) for serie in self.fields["serie_bac"].queryset.filter(code__in=BAC_SERIES)]
        self.fields["option_diplome"].choices = [
            ("", "Choisir une option"),
            ("Options BAC", bac_choices),
            ("Options DEAT", DEAT_OPTIONS),
            ("Options DT", DT_OPTIONS),
        ]
        self.fields["option_diplome"].required = True
        self.fields["option_diplome"].label = "Option"
        for field_name in ["nom", "prenom", "sexe", "departement", "annee_bac", "type_candidat", "diplome_examen", "option_diplome"]:
            self.fields[field_name].required = True
        for field_name in ["date_naissance", "telephone"]:
            self.fields[field_name].required = False
        for field_name, field in self.fields.items():
            current_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{current_class} aftec-field".strip()
            if field_name in {"nom", "prenom", "departement", "telephone"}:
                field.widget.attrs.setdefault("placeholder", field.label or "")
        matieres = Matiere.objects.filter(coefficients_series__isnull=False).distinct()
        matieres = matieres | Matiere.objects.filter(matiereclassement__isnull=False).distinct()
        self.note_matieres = sorted(set(matieres), key=lambda item: item.nom)
        self.note_fields = []
        for matiere in self.note_matieres:
            field_name = f"note_{matiere.id}"
            self.fields[field_name] = forms.DecimalField(
                label=matiere.nom,
                required=False,
                min_value=Decimal("0"),
                max_value=Decimal("20"),
                decimal_places=2,
                widget=forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "20"}),
            )
            self.note_fields.append((matiere, self[field_name]))

    def clean(self):
        cleaned_data = super().clean()
        diplome = cleaned_data.get("diplome_examen")
        option = cleaned_data.get("option_diplome")
        if not diplome or not option:
            return cleaned_data

        if diplome == Candidat.DiplomeExamen.BAC:
            allowed_options = set(BAC_SERIES)
            serie_code = option
        elif diplome == Candidat.DiplomeExamen.DEAT:
            allowed_options = {value for value, _ in DEAT_OPTIONS}
            serie_code = "DEAT"
        elif diplome == Candidat.DiplomeExamen.DT:
            allowed_options = {value for value, _ in DT_OPTIONS}
            serie_code = "DT"
        else:
            raise forms.ValidationError("Diplôme ou examen invalide.")

        if option not in allowed_options:
            self.add_error("option_diplome", "Cette option ne correspond pas au diplôme ou examen choisi.")
            return cleaned_data

        try:
            cleaned_data["serie_bac"] = self.fields["serie_bac"].queryset.get(code=serie_code)
        except SerieBac.DoesNotExist:
            self.add_error("diplome_examen", "Ce diplôme ou examen n'est pas disponible dans le catalogue importé.")
        return cleaned_data

    def save(self, commit=True):
        candidat = super().save(commit=commit)
        if commit:
            for matiere in self.note_matieres:
                value = self.cleaned_data.get(f"note_{matiere.id}")
                if value is not None:
                    NoteBac.objects.update_or_create(candidat=candidat, matiere=matiere, defaults={"note": value})
            candidat.moyenne_generale = calculer_moyenne_generale(candidat)[0]
            candidat.save(update_fields=["moyenne_generale"])
        return candidat
