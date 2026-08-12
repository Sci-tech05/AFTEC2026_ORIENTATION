from decimal import Decimal


def calculer_moyenne_generale(candidat):
    coefficients = candidat.serie_bac.coefficients_bac.select_related("matiere")
    notes = {note.matiere_id: note.note for note in candidat.notes.all()}
    total = Decimal("0")
    total_coef = Decimal("0")
    details = []

    for item in coefficients:
        note = notes.get(item.matiere_id)
        contribution = note * item.coefficient if note is not None else None
        if contribution is not None:
            total += contribution
            total_coef += Decimal(item.coefficient)
        details.append(
            {
                "matiere": item.matiere.nom,
                "note": note,
                "coefficient": item.coefficient,
                "contribution": contribution,
            }
        )

    moyenne = (total / total_coef).quantize(Decimal("0.01")) if total_coef else None
    return moyenne, details
