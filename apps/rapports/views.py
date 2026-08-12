from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from apps.candidats.models import Candidat
from apps.catalogue.services import calculer_moyenne_generale
from apps.moteur.services import calculer_recommandations

# ---------------------------------------------------------------------------
# Palette / constantes de style
# ---------------------------------------------------------------------------
NAVY = colors.HexColor("#12304D")
GOLD = colors.HexColor("#B98A1B")
GOLD_LIGHT = colors.HexColor("#E3C46A")
CREAM = colors.HexColor("#FFF8DF")
CARD_BG = colors.HexColor("#FAFAF7")
CARD_BORDER = colors.HexColor("#E2D6B7")
GREY_TEXT = colors.HexColor("#6A7280")
ROW_ALT = colors.HexColor("#FAFCFE")
GRID_LINE = colors.HexColor("#D7DEE8")
TOP_ROW_HIGHLIGHT = colors.HexColor("#FFF3D6")


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Eyebrow", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=8.5, leading=10, textColor=GOLD, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=21, leading=24, textColor=NAVY, alignment=TA_LEFT, spaceAfter=0,
    ))
    styles.add(ParagraphStyle(
        name="IdentityLabel", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=7.5, leading=9, textColor=GOLD, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="IdentityValue", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=10, leading=12.5, textColor=NAVY, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12.5, leading=15, textColor=NAVY, spaceBefore=2, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="CardLabel", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=8, leading=9.5, textColor=GOLD, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="CardValue", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=11.5, leading=13.5, textColor=NAVY, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="SmallNote", parent=styles["BodyText"], fontName="Helvetica-Oblique",
        fontSize=7.8, leading=10, textColor=GREY_TEXT,
    ))
    styles.add(ParagraphStyle(
        name="TableText", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.3, leading=10.5, textColor=colors.HexColor("#24313F"),
    ))
    styles.add(ParagraphStyle(
        name="TableHeader", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=8.3, leading=10.5, textColor=colors.white, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="MoyenneFinale", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=10.5, leading=13, textColor=NAVY,
    ))
    return styles


def _preference_label(value):
    mapping = {
        "classement": "Classement", "concours": "Concours",
        "dossier": "Dossier", "public": "Public", "prive": "Privé",
    }
    return mapping.get((value or "").strip().lower(), "Indifférent")


def _card(styles, label, value, width):
    return Table(
        [[Paragraph(label, styles["CardLabel"])], [Paragraph(value, styles["CardValue"])]],
        colWidths=[width * mm],
        rowHeights=[7 * mm, 15 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
            ("BOX", (0, 0), (-1, -1), 0.7, CARD_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]),
    )


def _identity_box(styles, label, value, width):
    return Table(
        [[Paragraph(label.upper(), styles["IdentityLabel"])],
         [Paragraph(value, styles["IdentityValue"])]],
        colWidths=[width * mm],
        style=TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (0, 0), 0),
            ("BOTTOMPADDING", (0, 0), (0, 0), 2),
            ("TOPPADDING", (0, 1), (0, 1), 0),
            ("BOTTOMPADDING", (0, 1), (0, 1), 0),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]),
    )


def _draw_page(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 14 * mm, width, 14 * mm, stroke=0, fill=1)
    canvas.setFillColor(GOLD)
    canvas.rect(0, height - 15.6 * mm, width, 1.6 * mm, stroke=0, fill=1)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.setFillColor(colors.white)
    canvas.drawString(doc.leftMargin, height - 9 * mm, "AFTEC Orientation 2026")
    canvas.setFont("Helvetica", 8.5)
    canvas.drawRightString(width - doc.rightMargin, height - 9 * mm, f"Page {canvas.getPageNumber()}")
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY_TEXT)
    canvas.drawString(doc.leftMargin, 9 * mm, "Rapport généré automatiquement")
    canvas.drawRightString(width - doc.rightMargin, 9 * mm, "Conçu pour une lecture mobile et imprimable")
    canvas.restoreState()


def _build_story(candidat, recommandations):
    styles = _build_styles()
    page_width, _ = A4
    content_width = page_width - (16 * mm) - (16 * mm)
    story = []

    # ---- En-tête : bandeau titre --------------------------------------
    header_cell = Table(
        [[Paragraph("AFTEC ORIENTATION 2026", styles["Eyebrow"])],
         [Paragraph("Rapport de classement", styles["ReportTitle"])]],
        colWidths=[content_width],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CREAM),
            ("BOX", (0, 0), (-1, -1), 1, GOLD_LIGHT),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (0, 0), 10),
            ("BOTTOMPADDING", (0, 0), (0, 0), 0),
            ("TOPPADDING", (0, 1), (0, 1), 1),
            ("BOTTOMPADDING", (0, 1), (0, 1), 10),
        ]),
    )
    story.append(header_cell)
    story.append(Spacer(1, 4 * mm))

    # ---- Identité candidat ---------------------------------------------
    diplome = " ".join(str(p) for p in [candidat.diplome_examen, candidat.option_diplome] if p)
    identity_row = [
        _identity_box(styles, "Candidat", f"{candidat.prenom} {candidat.nom}", content_width / 3 / mm - 3),
        _identity_box(styles, "Diplôme / examen", diplome or "--", content_width / 3 / mm - 3),
        _identity_box(styles, "Série", str(candidat.serie_bac) if candidat.serie_bac else "--", content_width / 3 / mm - 3),
    ]
    identity_table = Table(
        [identity_row], colWidths=[content_width / 3] * 3,
        style=TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.6, GRID_LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]),
    )
    story.append(identity_table)
    story.append(Spacer(1, 4 * mm))

    # ---- Cartes de synthèse ---------------------------------------------
    moyenne_generale = candidat.moyenne_generale
    meilleure_recommandation = recommandations[0] if recommandations else None
    cards = [
        _card(styles, "Moyenne générale", f"{moyenne_generale}/20" if moyenne_generale is not None else "--", content_width * 0.17 / mm),
        _card(styles, "Top recommandation", meilleure_recommandation.filiere.intitule if meilleure_recommandation else "Aucune", content_width * 0.33 / mm),
        _card(styles, "Mode", _preference_label(candidat.preference_mode_entree), content_width * 0.25 / mm),
        _card(styles, "Secteur", _preference_label(candidat.preference_secteur), content_width * 0.25 / mm),
    ]
    cards_table = Table(
        [cards],
        colWidths=[content_width * 0.17, content_width * 0.33, content_width * 0.25, content_width * 0.25],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )
    story.append(cards_table)
    story.append(Spacer(1, 5 * mm))

    # ---- Résumé des recommandations -------------------------------------
    story.append(Paragraph("Résumé des recommandations", styles["SectionHeading"]))
    recommendation_rows = [[
        Paragraph("Filière", styles["TableHeader"]),
        Paragraph("Établissement", styles["TableHeader"]),
        Paragraph("Moy. classement", styles["TableHeader"]),
        Paragraph("Bourse", styles["TableHeader"]),
        Paragraph("Aide/FPP", styles["TableHeader"]),
        Paragraph("Mode", styles["TableHeader"]),
    ]]
    for item in recommandations[:8]:
        recommendation_rows.append([
            Paragraph(item.filiere.intitule, styles["TableText"]),
            Paragraph(f"{item.filiere.etablissement}", styles["TableText"]),
            Paragraph(f"{item.moyenne_classement}/20" if item.moyenne_classement is not None else "--", styles["TableText"]),
            Paragraph(str(item.filiere.quota_bourse), styles["TableText"]),
            Paragraph(str(item.filiere.quota_aide_fpp), styles["TableText"]),
            Paragraph(item.filiere.get_mode_entree_display(), styles["TableText"]),
        ])

    row_backgrounds = [colors.white, ROW_ALT]
    reco_style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID_LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (1, -1), "LEFT"),
    ]
    # Zébrage + mise en avant discrète de la meilleure recommandation (1re ligne,
    # déjà triée par potentiel/composite_score dans calculer_recommandations)
    for i in range(1, len(recommendation_rows)):
        bg = TOP_ROW_HIGHLIGHT if i == 1 else row_backgrounds[i % 2]
        reco_style.append(("BACKGROUND", (0, i), (-1, i), bg))

    recommendations_table = Table(
        recommendation_rows,
        colWidths=[42 * mm, 40 * mm, 24 * mm, 18 * mm, 20 * mm, 26 * mm],
        repeatRows=1,
        style=TableStyle(reco_style),
    )
    story.append(recommendations_table)
    story.append(Spacer(1, 4 * mm))

    # ---- Détail des notes -------------------------------------------------
    story.append(Paragraph("Détail des notes", styles["SectionHeading"]))
    moyenne_generale_detail, details_generale = calculer_moyenne_generale(candidat)
    notes_rows = [[
        Paragraph("Matière", styles["TableHeader"]),
        Paragraph("Note", styles["TableHeader"]),
        Paragraph("Coefficient", styles["TableHeader"]),
        Paragraph("Contribution", styles["TableHeader"]),
    ]]
    for detail in details_generale:
        notes_rows.append([
            Paragraph(detail["matiere"], styles["TableText"]),
            Paragraph(f"{detail['note']}/20" if detail["note"] is not None else "--", styles["TableText"]),
            Paragraph(str(detail["coefficient"]), styles["TableText"]),
            Paragraph(f"{detail['contribution']}" if detail["contribution"] is not None else "--", styles["TableText"]),
        ])
    notes_table = Table(
        notes_rows,
        colWidths=[70 * mm, 30 * mm, 30 * mm, 38 * mm],
        repeatRows=1,
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, GRID_LINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]),
    )
    story.append(notes_table)
    story.append(Spacer(1, 4 * mm))

    # ---- Bloc de clôture (gardé groupé pour éviter une page presque vide) --
    closing_block = KeepTogether([
        Paragraph(
            f"Moyenne générale calculée : {moyenne_generale_detail}/20"
            if moyenne_generale_detail is not None else "Moyenne générale calculée : --",
            styles["MoyenneFinale"],
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            "Estimation indicative basée sur les critères disponibles dans le catalogue importé. "
            "Seule la plateforme officielle du MESRS fait foi.",
            styles["SmallNote"],
        ),
    ])
    story.append(closing_block)
    return story


def _build_pdf_response(candidat, recommandations):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=20 * mm,
        bottomMargin=16 * mm,
        title=f"Rapport orientation {candidat.prenom} {candidat.nom}",
        author="AFTEC Orientation 2026",
    )
    story = _build_story(candidat, recommandations)
    document.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="rapport_orientation_{candidat.pk}.pdf"'
    return response


def rapport_pdf(request, candidat_id):
    candidat = get_object_or_404(
        Candidat.objects.select_related("serie_bac").prefetch_related("notes__matiere"),
        pk=candidat_id,
    )
    recommandations = calculer_recommandations(candidat)
    return _build_pdf_response(candidat, recommandations)