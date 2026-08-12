# Plateforme d'Orientation Universitaire AFTEC 2026

Application Django + SQLite destinée à la journée d'orientation AFTEC/KcoMat Académie. Elle calcule la moyenne de classement par filière, affiche les quotas MESRS et génère un rapport PDF indicatif.

## Installation

```powershell
python -m pip install django weasyprint
python manage.py migrate
python manage.py import_guide_text --clear
python manage.py runserver
```

Ouvrir ensuite `http://127.0.0.1:8000/`.

## Commandes utiles

```powershell
python manage.py seed_sample
python manage.py import_guide_text --clear
python manage.py validate_data
python manage.py import_guido --file fixtures/guide.json
python manage.py test
```

`import_guide_text --clear` charge le catalogue complet depuis `Guide_orientation_2026_2027.txt` : 224 offres publiques/assimilées avec quotas, séries et matières de classement, plus les formations EPES disponibles dans l'annuaire. `seed_sample` reste disponible pour un petit jeu de démonstration. `import_guido` accepte un JSON structuré avec les champs `categorie_code`, `categorie_nom`, `etablissement`, `filiere`, `bourse`, `aide_fpp`, `series` et `matieres`.

## Administration

Créer un compte :

```powershell
python manage.py createsuperuser
```

L'administration permet d'ajuster les coefficients de matières, les seuils indicatifs de bourse/aide et les informations des filières.

## Avertissement

Les recommandations sont des estimations basées sur les quotas et critères publiés par le MESRS dans le Guide d'information 2026-2027. Elles ne constituent pas une décision officielle.
