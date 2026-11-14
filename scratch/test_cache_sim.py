import sys
sys.path.insert(0, 'upload')
from core.reference_service import validate_citation_text, _CITATION_STATUS_CACHE

_CITATION_STATUS_CACHE["10.1016/j.cell.2020.test_ret"] = {
    "success": True,
    "title": "Fabricated CRISPR Assay",
    "year": 2020,
    "update_to": [{"type": "retraction", "label": "Retraction", "doi": "10.1016/j.cell.2021.01"}]
}

_CITATION_STATUS_CACHE["10.1038/s41586.test_clean"] = {
    "success": True,
    "title": "Clean Nature Study",
    "year": 2020,
    "update_to": []
}

val_ret = validate_citation_text("10.1016/j.cell.2020.test_ret", use_network=False)
print("Retracted check:")
print("  has_retracted:", val_ret["has_retracted"])
print("  retracted_citations:", len(val_ret["retracted_citations"]))
print("  status_type:", val_ret["references"][0]["status_type"])

val_clean = validate_citation_text("10.1038/s41586.test_clean", use_network=False)
print("Clean check:")
print("  has_retracted:", val_clean["has_retracted"])
print("  status_type:", val_clean["references"][0]["status_type"])
