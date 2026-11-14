import sys
sys.path.insert(0, 'upload')
from core.reference_service import validate_citation_text, _CITATION_STATUS_CACHE

_CITATION_STATUS_CACHE["10.1016/j.cell.2020.test_ret"] = {
    "success": True,
    "is_retracted": True,
    "is_expression_of_concern": False,
    "is_preprint": False,
    "is_corrected": False,
    "title": "Fabricated CRISPR Assay",
    "year": 2020
}

val_ret = validate_citation_text("10.1016/j.cell.2020.test_ret", use_network=False)
print("has_retracted:", val_ret["has_retracted"])
print("retracted_citations:", len(val_ret["retracted_citations"]))
print("status_type:", val_ret["references"][0]["status_type"])
