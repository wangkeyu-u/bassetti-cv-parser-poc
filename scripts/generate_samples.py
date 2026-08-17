#!/usr/bin/env python3
"""Generate three entirely fictional CV PDFs and their deterministic gold fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
FIXTURES = ROOT / "fixtures" / "gold"
ORANGE = HexColor("#EC6408"); INK = HexColor("#292521"); MUTED = HexColor("#6F665F"); WARM = HexColor("#F3EFE8")


def styles():
    s = getSampleStyleSheet()
    return {
        "name": ParagraphStyle("Name", parent=s["Title"], fontName="Helvetica-Bold", fontSize=24, leading=27, textColor=INK, spaceAfter=5),
        "role": ParagraphStyle("Role", parent=s["Normal"], fontName="Helvetica", fontSize=11, textColor=ORANGE, spaceAfter=12),
        "h": ParagraphStyle("Head", parent=s["Heading2"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=ORANGE, spaceBefore=10, spaceAfter=5),
        "body": ParagraphStyle("Body", parent=s["Normal"], fontName="Helvetica", fontSize=8.6, leading=12, textColor=INK, spaceAfter=3),
        "small": ParagraphStyle("Small", parent=s["Normal"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTED, spaceAfter=2),
    }


def footer(canvas, doc):
    canvas.saveState(); canvas.setFont("Helvetica", 7); canvas.setFillColor(MUTED)
    canvas.drawString(18*mm, 10*mm, "FICTIONAL / ANONYMOUS DEMO CV - NOT A REAL PERSON")
    canvas.drawRightString(192*mm, 10*mm, f"Page {doc.page}"); canvas.restoreState()


def p(text, style): return Paragraph(text.replace("&", "&amp;"), style)


def single_column(path: Path):
    st=styles(); doc=BaseDocTemplate(str(path),pagesize=A4,leftMargin=19*mm,rightMargin=19*mm,topMargin=18*mm,bottomMargin=18*mm)
    frame=Frame(doc.leftMargin,doc.bottomMargin,doc.width,doc.height,id="normal");doc.addPageTemplates(PageTemplate(id="single",frames=[frame],onPage=footer))
    story=[p("Maya Laurent",st["name"]),p("Industrial Data Coordinator",st["role"]),p("Email: maya.laurent@example.test | Phone: +33 6 00 00 01 27",st["body"]),p("Location: Lyon, France",st["body"]),p("PROFILE",st["h"]),p("Fictional coordinator experienced in controlled engineering information and technical documentation.",st["body"]),p("EXPERIENCE",st["h"]),p("Asteron Systems | Data Coordinator | Lyon, France | 2022 - Present",st["body"]),p("- Maintained controlled equipment records and coordinated data-quality reviews.",st["body"]),p("- Prepared weekly exception reports for engineering teams.",st["body"]),p("Novalume Industrie | Documentation Assistant | Grenoble, France | 2020 - 2022",st["body"]),p("- Indexed technical files and supported document-change workflows.",st["body"]),p("EDUCATION",st["h"]),p("Institut Fictif de Lyon | Master | Information Management | 2018 - 2020",st["body"]),p("Université Exemple Alpes | Bachelor | Applied Languages | 2015 - 2018",st["body"]),p("SKILLS: Data governance, Excel, SQL, Technical documentation, Change control",st["body"]),p("LANGUAGES",st["h"]),p("French: Native",st["body"]),p("English: Fluent",st["body"]),p("German: B1",st["body"])]
    doc.build(story)


def two_column(path: Path):
    st=styles(); doc=BaseDocTemplate(str(path),pagesize=A4,leftMargin=15*mm,rightMargin=15*mm,topMargin=16*mm,bottomMargin=18*mm)
    left=Frame(15*mm,18*mm,56*mm,263*mm,id="left",leftPadding=6*mm,rightPadding=6*mm,topPadding=8*mm,bottomPadding=5*mm,showBoundary=0)
    right=Frame(78*mm,18*mm,117*mm,263*mm,id="right",leftPadding=5*mm,rightPadding=2*mm,topPadding=8*mm,bottomPadding=5*mm)
    doc.addPageTemplates(PageTemplate(id="two",frames=[left,right],onPage=footer))
    # FrameBreak would hurt extraction ordering; a narrow sidebar-shaped table creates
    # genuine complex layout while preserving explicit text in extraction.
    sidebar=[p("CONTACT",st["h"]),p("Name: Oliver Chen",st["body"]),p("Email: oliver.chen@example.test",st["body"]),p("Phone: +44 7700 900 412",st["body"]),p("Location: Bristol, UK",st["body"]),p("SKILLS",st["h"]),p("Skills: Python, Power BI, ETL, PostgreSQL, Data quality",st["body"]),p("LANGUAGES",st["h"]),p("English: Native",st["body"]),p("Mandarin: Conversational",st["body"])]
    main=[p("OLIVER CHEN",st["name"]),p("Technical Information Analyst",st["role"]),p("EXPERIENCE",st["h"]),p("Fictional Works Ltd | Information Analyst | Bristol, UK | 2023 - Present",st["body"]),p("- Built repeatable data-quality checks for controlled product records.",st["body"]),p("- Documented exception handling with engineering stakeholders.",st["body"]),p("Northbridge Demo PLC | Junior Data Analyst | Bath, UK | 2021 - 2023",st["body"]),p("- Produced operational dashboards and reconciled source extracts.",st["body"]),p("EDUCATION",st["h"]),p("Westborough Fictional University | BSc | Information Systems | 2018 - 2021",st["body"])]
    table=Table([[sidebar,main]],colWidths=[60*mm,115*mm],style=TableStyle([('BACKGROUND',(0,0),(0,0),WARM),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6*mm),('RIGHTPADDING',(0,0),(-1,-1),6*mm),('TOPPADDING',(0,0),(-1,-1),5*mm),('BOTTOMPADDING',(0,0),(-1,-1),5*mm),('LINEBEFORE',(1,0),(1,0),1,ORANGE)]))
    # Use a full-page normal frame for the table.
    normal=Frame(doc.leftMargin,doc.bottomMargin,doc.width,doc.height,id="normal");doc.pageTemplates=[PageTemplate(id="complex",frames=[normal],onPage=footer)]
    doc.build([table])


def mixed(path: Path):
    st=styles();doc=BaseDocTemplate(str(path),pagesize=A4,leftMargin=19*mm,rightMargin=19*mm,topMargin=18*mm,bottomMargin=18*mm);frame=Frame(doc.leftMargin,doc.bottomMargin,doc.width,doc.height,id="normal");doc.addPageTemplates(PageTemplate(id="single",frames=[frame],onPage=footer))
    story=[p("Name: Camille Moreau",st["name"]),p("Cheffe de projet data / Data Project Lead",st["role"]),p("Email: camille.moreau@example.test",st["body"]),p("Location: Toulouse, France",st["body"]),p("EXPÉRIENCE",st["h"]),p("Atelier Horizon SAS | Cheffe de projet data | Toulouse, France | 03/04/2022 - Present",st["body"]),p("- Coordination d'un projet de migration documentaire bilingue.",st["body"]),p("Demo Aero Services | Data Specialist | Remote | 2021 - 2022",st["body"]),p("- Cleaned product records and documented open data issues.",st["body"]),p("Mission parallèle fictive | Consultante | Paris, France | 2022 - 2022",st["body"]),p("- Supported a short controlled-vocabulary workshop.",st["body"]),p("FORMATION",st["h"]),p("École Démonstration Occitanie | MSc | Gestion des connaissances | 2019 - 2021",st["body"]),p("COMPÉTENCES: Gestion de projet, SQL, Taxonomies, Documentation technique",st["body"]),p("LANGUES",st["h"]),p("Français: Langue maternelle",st["body"]),p("English: Fluent",st["body"]),p("Español: Niveau professionnel",st["body"]),p("ADDITIONAL INFORMATION",st["h"]),p("National ID: DEMO-ONLY-0000 (synthetic placeholder; should not be extracted)",st["small"]),p("Note: no phone number is written as text; imagine a phone icon without a readable value.",st["small"])]
    doc.build(story)


GOLD={
"normal_single_column":{"contact.name":"Maya Laurent","contact.email":"maya.laurent@example.test","contact.phone":"+33 6 00 00 01 27","location":"Lyon, France","education_count":2,"work_experience_count":2,"skills_count":5,"languages":[{"language":"French","original_level":"Native","cefr":"Not specified"},{"language":"English","original_level":"Fluent","cefr":"Not specified"},{"language":"German","original_level":"B1","cefr":"B1"}]},
"complex_two_column":{"contact.name":"Oliver Chen","contact.email":"oliver.chen@example.test","contact.phone":"+44 7700 900 412","location":"Bristol, UK","education_count":1,"work_experience_count":2,"skills_count":5,"languages":[{"language":"English","original_level":"Native","cefr":"Not specified"},{"language":"Mandarin","original_level":"Conversational","cefr":"Not specified"}]},
"mixed_fr_en_ambiguous":{"contact.name":"Camille Moreau","contact.email":"camille.moreau@example.test","contact.phone":None,"location":"Toulouse, France","education_count":1,"work_experience_count":3,"skills_count":4,"languages":[{"language":"Français","original_level":"Langue maternelle","cefr":"Not specified"},{"language":"English","original_level":"Fluent","cefr":"Not specified"},{"language":"Español","original_level":"Niveau professionnel","cefr":"Not specified"}]}}


def main():
    SAMPLES.mkdir(parents=True,exist_ok=True);FIXTURES.mkdir(parents=True,exist_ok=True)
    single_column(SAMPLES/"normal_single_column.pdf");two_column(SAMPLES/"complex_two_column.pdf");mixed(SAMPLES/"mixed_fr_en_ambiguous.pdf")
    for name,data in GOLD.items():(FIXTURES/f"{name}.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Generated",len(GOLD),"fictional PDFs and gold fixtures")
if __name__=="__main__":main()

