import os
import sys

# Ajouter la racine du projet au PYTHONPATH pour importer le module `config`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django

django.setup()

from apps.candidats.models import Candidat
from apps.moteur.services import calculer_recommandations
from apps.rapports.views import _build_pdf_response

c = Candidat.objects.first()
if not c:
    print('Aucun candidat trouvé dans la base. Créez au moins un candidat pour le test.')
    sys.exit(1)

recs = calculer_recommandations(c)
response = _build_pdf_response(c, recs)
output = 'test_rapport.pdf'
with open(output, 'wb') as fh:
    fh.write(response.content)
print(f'PDF généré: {output}')
