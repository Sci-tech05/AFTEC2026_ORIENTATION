from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.catalogue.models import CategorieEtablissement, Etablissement, Filiere, Universite


class EtablissementSearchTests(TestCase):
	def setUp(self):
		categorie = CategorieEtablissement.objects.create(code="I", nom="Université", type="public_universite")
		universite = Universite.objects.create(categorie=categorie, nom="Université d'Abomey Calavi", sigle="UAC")
		institut = Etablissement.objects.create(categorie=categorie, universite=universite, nom="Institut National de l'Eau", sigle="INE", secteur=Etablissement.Secteur.PUBLIC)
		autre = Etablissement.objects.create(categorie=categorie, universite=universite, nom="Faculté des Sciences", sigle="FSS", secteur=Etablissement.Secteur.PUBLIC)
		Filiere.objects.create(etablissement=institut, intitule="Hydrologie et Gestion de l'Eau", mode_entree=Filiere.ModeEntree.CLASSEMENT)
		Filiere.objects.create(etablissement=autre, intitule="Mathématiques", mode_entree=Filiere.ModeEntree.CLASSEMENT)

	def test_la_recherche_prefere_les_etablissements_et_filieres_correspondants(self):
		response = self.client.get(reverse("core:etablissements"), {"q": "insti"})

		self.assertContains(response, "Institut National de l'Eau", html=True)
		self.assertNotContains(response, "Faculté des Sciences")
		self.assertNotContains(response, "Mathématiques")


class AdminInterfaceTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_superuser(username="admin", email="admin@example.com", password="password12345")

	def test_login_page_is_customized(self):
		response = self.client.get(reverse("admin:index"), follow=True)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "AFTEC Admin")
		self.assertContains(response, "Gérez le guide, les candidats et les filières")

	def test_dashboard_is_accessible_for_staff(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse("admin:index"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "AFTEC Admin")
		self.assertContains(response, "Pilotage du contenu")
