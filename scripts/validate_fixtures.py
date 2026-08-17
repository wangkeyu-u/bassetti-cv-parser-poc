#!/usr/bin/env python3
"""Compare parser output against the small, human-authored fictional gold set."""
from __future__ import annotations
import json
from pathlib import Path
from bassetti_poc.extractor import parse_document

ROOT=Path(__file__).resolve().parents[1]

def compare(result,gold):
    f=result["fields"]; checks={
      "contact.name":f["contact.name"]["value"]==gold["contact.name"],
      "contact.email":f["contact.email"]["value"]==gold["contact.email"],
      "contact.phone":f["contact.phone"]["value"]==gold["contact.phone"],
      "location":f["location"]["value"]==gold["location"],
      "education":len(f["education"]["value"])==gold["education_count"],
      "work_experience":len(f["work_experience"]["value"])==gold["work_experience_count"],
      "skills":len(f["skills"]["value"])==gold["skills_count"],
      "languages":f["languages"]["value"]==gold["languages"],
    };return checks

def main():
    all_checks={};durations=[]
    for gold_path in sorted((ROOT/"fixtures/gold").glob("*.json")):
      name=gold_path.stem;gold=json.loads(gold_path.read_text(encoding="utf-8"));pdf=ROOT/"samples"/f"{name}.pdf";result=parse_document(pdf.name,pdf.read_bytes());durations.append(result["processing_ms"]);all_checks[name]=compare(result,gold)
    total=sum(len(x) for x in all_checks.values());correct=sum(sum(x.values()) for x in all_checks.values());summary={"measurement":"demo measurement","dataset":"3 fictional CV fixtures","correct_fields":correct,"total_fields":total,"field_accuracy_percent":round(correct/total*100,1),"average_processing_ms":round(sum(durations)/len(durations)),"per_fixture":all_checks,"disclaimer":"Not Bassetti internal data; small deterministic demo set, not a production benchmark."};(ROOT/"fixtures/validation_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8");print(json.dumps(summary,indent=2));return 0 if correct==total else 1
if __name__=="__main__":raise SystemExit(main())

