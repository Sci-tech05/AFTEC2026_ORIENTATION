from django.test import SimpleTestCase

from apps.catalogue.management.commands.import_guide_docx import extract_matieres_by_serie


class GuideDocxParsingTests(SimpleTestCase):
    def test_extracts_matieres_for_each_serie_when_groups_are_glued(self):
        value = (
            "B : Culture g\u00e9n\u00e9rale, Economie "
            "C, D : Culture g\u00e9n\u00e9rale, Maths"
            "G2, G3 : Culture g\u00e9n\u00e9rale, Etude de Cas "
            "DT/CoM : Culture g\u00e9n\u00e9rale, Techn Compta et Mercatique"
        )

        result = extract_matieres_by_serie(value, ["B", "C", "D", "G2", "G3", "DT"])

        self.assertEqual(result["B"], ["Culture g\u00e9n\u00e9rale", "Economie"])
        self.assertEqual(result["C"], ["Culture g\u00e9n\u00e9rale", "Maths"])
        self.assertEqual(result["D"], ["Culture g\u00e9n\u00e9rale", "Maths"])
        self.assertEqual(result["G2"], ["Culture g\u00e9n\u00e9rale", "Etude de Cas"])
        self.assertEqual(result["G3"], ["Culture g\u00e9n\u00e9rale", "Etude de Cas"])
        self.assertEqual(result["DT"], ["Culture g\u00e9n\u00e9rale", "Techn Compta et Mercatique"])

    def test_extracts_f3_and_deat_without_leaking_series_as_matieres(self):
        value = (
            "C, D : Anglais, Maths, PCT "
            "E, F1, DT/CEMS, DT/FM : Construction M\u00e9canique, Maths, PCT"
            "F3, DT/Electrotech : Electrotech, Maths, PCT "
            "F2 : EST, Maths, PCT"
            "DEAT/AER : Les trois (03) mati\u00e8res \u00e9crites"
        )

        result = extract_matieres_by_serie(value, ["C", "D", "E", "F1", "F2", "F3", "DT", "DEAT"])

        self.assertEqual(result["C"], ["Anglais", "Maths", "PCT"])
        self.assertEqual(result["D"], ["Anglais", "Maths", "PCT"])
        self.assertEqual(result["E"], ["Construction M\u00e9canique", "Maths", "PCT"])
        self.assertEqual(result["F1"], ["Construction M\u00e9canique", "Maths", "PCT"])
        self.assertEqual(result["F2"], ["Etude de Syst\u00e8me Technique", "Maths", "PCT"])
        self.assertEqual(result["F3"], ["Electrotechnique", "Maths", "PCT"])
        self.assertEqual(result["DT"], ["Electrotechnique", "Maths", "PCT"])
        self.assertEqual(result["DEAT"], ["Mati\u00e8res professionnelles"])

    def test_lv1_is_normalized_to_anglais(self):
        value = "A1, A2, B, C, D : Anglais (LV1), Fran\u00e7ais, Hist-G\u00e9o"

        result = extract_matieres_by_serie(value, ["A1", "A2", "B", "C", "D"])

        self.assertEqual(result["C"], ["Anglais", "Fran\u00e7ais", "Hist-G\u00e9o"])
