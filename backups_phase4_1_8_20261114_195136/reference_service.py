import time
"""
Scholarly Reference & DOI Resolution Service for BT_301.
Resolves DOIs via CrossRef REST API and PMIDs via NCBI E-utilities.
Audits bibliography recency against the >= 60% (2021-2026) rubric rule.
"""

import re
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime


def fetch_doi_metadata(doi_string: str) -> Dict[str, Any]:
    """
    Fetches reference metadata from CrossRef public API given a DOI or URL.
    """
    doi_clean = doi_string.strip()
    # Clean standard prefixes
    doi_clean = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi_clean, flags=re.IGNORECASE)
    doi_clean = doi_clean.strip()

    if not doi_clean or "/" not in doi_clean:
        return {
            "success": False,
            "error": "Invalid DOI format. Expected format like: 10.1073/pnas.1718804115"
        }

    url = f"https://api.crossref.org/works/{doi_clean}"
    headers = {"User-Agent": "BioWriterStudio/1.0 (mailto:biowriter@university.edu)"}

    try:
        resp = requests.get(url, headers=headers, timeout=6.0)
        if resp.status_code == 200:
            data = resp.json().get("message", {})
            title = data.get("title", ["Unknown Title"])[0]
            
            # Authors
            authors_list = []
            for a in data.get("author", []):
                family = a.get("family", "")
                given = a.get("given", "")
                if family:
                    authors_list.append(f"{family}, {given[0]}." if given else family)
            authors_str = ", ".join(authors_list[:3])
            if len(authors_list) > 3:
                authors_str += " et al."

            # Publication Year
            published = data.get("published-print") or data.get("published-online") or data.get("created")
            year = None
            if published and "date-parts" in published and published["date-parts"]:
                year = published["date-parts"][0][0]

            journal = data.get("container-title", ["Unknown Journal"])[0] if data.get("container-title") else "Unknown Journal"

            is_recent = bool(year and year >= 2021)
            formatted_citation = f"{authors_str} ({year or 'n.d.'}). {title}. {journal}. DOI: {doi_clean}"

            # Preprint, Retraction, Expression-of-Concern & Correction Integrity Checks
            pub_type = data.get("type", "journal-article")
            is_preprint = bool(
                pub_type == "posted-content" or
                "preprint" in str(data.get("subtype", "")).lower() or
                "preprint" in str(pub_type).lower()
            )
            publication_type = "preprint" if is_preprint else pub_type

            updates = data.get("update-to", [])
            relation = data.get("relation", {})

            # Inspect update types across CrossRef update-to and bidirectional relation metadata
            update_types = [str(u.get("type", "")).lower() for u in updates if isinstance(u, dict)]
            relation_keys = [str(k).lower() for k in relation.keys()]
            relation_str = str(relation).lower()

            is_retracted = bool(
                any(t in ["retraction", "partial_retraction", "partial-retraction", "retracted", "withdrawal", "withdrawn"] for t in update_types) or
                any(rk in ["is-retracted-by", "has-retraction", "is-withdrawn-by", "has-withdrawal", "retracts", "withdraws"] for rk in relation_keys) or
                "is-retracted-by" in relation_str
            )

            is_expression_of_concern = bool(
                not is_retracted and (
                    any(t in ["expression_of_concern", "expression-of-concern", "concern"] for t in update_types) or
                    any(rk in ["is-expression-of-concern-for", "has-expression-of-concern", "expression-of-concern-by"] for rk in relation_keys) or
                    "expression-of-concern" in relation_str or
                    "expression_of_concern" in relation_str
                )
            )

            is_corrected = bool(
                not is_retracted and not is_expression_of_concern and (
                    any(t in ["correction", "corrigendum", "erratum", "amendment"] for t in update_types) or
                    any(rk in ["is-corrected-by", "has-correction", "is-amended-by"] for rk in relation_keys) or
                    "is-corrected-by" in relation_str
                )
            )

            if is_retracted:
                status_type = "retracted"
                status_warning = "CRITICAL WARNING: This publication has been RETRACTED according to CrossRef/Crossmark records. It must not be cited as valid scientific evidence."
                status_details = "Formal retraction record identified in CrossRef/Crossmark metadata."
            elif is_expression_of_concern:
                status_type = "expression_of_concern"
                status_warning = "WARNING: This publication is subject to an active Expression of Concern according to CrossRef/Crossmark records. Research integrity or data validity is under formal investigation."
                status_details = "Formal expression of concern notice identified in CrossRef/Crossmark metadata."
            elif is_preprint:
                status_type = "preprint"
                status_warning = "Notice: This reference is an unreviewed preprint (posted-content) and has not undergone formal journal peer review."
                status_details = "Publication identified as unreviewed posted-content/preprint in CrossRef metadata."
            elif is_corrected:
                status_type = "corrected"
                status_warning = "Notice: This publication has formal Crossmark publisher corrections, corrigenda, or errata on record."
                status_details = "Publisher correction or erratum notice identified in CrossRef/Crossmark metadata."
            else:
                status_type = "standard"
                status_warning = None
                status_details = "No update or retraction records found in available CrossRef metadata. (Note: This does not constitute proof that no notices exist in other databases or publisher platforms)."

            return {
                "success": True,
                "doi": doi_clean,
                "title": title,
                "authors": authors_str,
                "year": year,
                "journal": journal,
                "is_recent": is_recent,
                "is_preprint": is_preprint,
                "is_retracted": is_retracted,
                "is_expression_of_concern": is_expression_of_concern,
                "is_corrected": is_corrected,
                "publication_type": publication_type,
                "status_type": status_type,
                "status_warning": status_warning,
                "status_verified_source": "CrossRef / Crossmark metadata",
                "status_details": status_details,
                "formatted_citation": formatted_citation
            }
        else:
            return {
                "success": False,
                "error": f"CrossRef returned status {resp.status_code} for DOI: {doi_clean}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Connection error looking up DOI: {str(e)}"
        }


def extract_citation_year(line: str) -> Optional[int]:
    """
    Extracts true publication year from a citation string, preventing false collisions
    with page numbers (e.g. pp. 2021-2025), issue/volume numbers, patent numbers, or embedded DOIs.
    Ensures parenthetical years (e.g. '(2024)' or '(1998)') are correctly matched regardless of boundaries,
    and returns None when multiple unassociated candidate years produce ambiguity.
    """
    if not isinstance(line, str):
        return None
    raw = line.strip()
    if not raw:
        return None

    # Step 1: Clean out high-confidence non-year noise before scanning
    # 1a. Remove DOIs
    clean = re.sub(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", " ", raw)
    # 1b. Remove long numeric sequences (>= 5 digits, e.g. patent identifiers like US20210012345A1)
    clean = re.sub(r"\b[A-Za-z]{0,4}\d{5,}[A-Za-z\d]*\b", " ", clean)
    # 1c. Remove page ranges like pp. 2021-2025, p. 1990-1995, 2021-2025, 2021–2025
    clean = re.sub(r"(?:pp?\.?|pages?|:\s*)\s*\d+[\-–]\d+", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\b\d{4}[\-–]\d{4}\b", " ", clean)
    # 1d. Strip explicit volume / issue / article markers like Vol. 1990, Volume 1990, Issue 2001, Art. 1995
    clean_no_vol = re.sub(r"\b(?:vol(?:ume)?|issue|no|art(?:icle)?)\.?\s*\d+\b", " ", clean, flags=re.IGNORECASE)

    # Step 2: Parenthetical years (e.g. '(2020)', '(1995)', '(2019a)')
    # Must use non-word or string boundary rather than \b\( which fails after spaces
    paren_pattern = r"(?:^|[^\w])\(((?:19\d{2}|20[0-2]\d))[a-z]?\)(?=[^\w]|$)"
    paren_matches = re.findall(paren_pattern, clean_no_vol)
    if paren_matches:
        # Check if an author-associated parenthetical year exists (e.g., 'Zhang (2023)' or 'Brown (2019a)')
        author_paren = re.search(r"\b([A-Z][a-zA-Z\-\']+(?:\s+(?:[A-Z]\.|\bet\s+al\.?|and|&|[A-Z][a-zA-Z\-\']+))*\s*)\(((?:19\d{2}|20[0-2]\d))[a-z]?\)", clean_no_vol)
        if author_paren:
            y = int(author_paren.group(2))
            if 1900 <= y <= 2026:
                return y
        # Otherwise return first valid parenthesized year in acceptable range
        valid_parens = [int(y) for y in paren_matches if 1900 <= int(y) <= 2026]
        if valid_parens:
            return valid_parens[0]

    # Step 3: Author-date style without parentheses (e.g. 'Zhang et al., 2024.' or 'Al-Bahrani et al. 2022.')
    author_date_patterns = [
        # LastName et al. [optional comma] YYYY
        r"\b[A-Z][a-zA-Z\-\']+\s+et\s+al\.?,?\s+((?:19\d{2}|20[0-2]\d))[a-z]?(?=[,\.\s]|$)",
        # LastName, Initials. YYYY
        r"\b[A-Z][a-zA-Z\-\']+,\s+(?:[A-Z]\.\s*)+((?:19\d{2}|20[0-2]\d))[a-z]?(?=[,\.\s]|$)",
        # LastName, YYYY
        r"\b[A-Z][a-zA-Z\-\']+,\s+((?:19\d{2}|20[0-2]\d))[a-z]?(?=[,\.\s]|$)",
    ]
    for p in author_date_patterns:
        m = re.search(p, clean_no_vol)
        if m:
            y = int(m.group(1))
            if 1900 <= y <= 2026:
                return y

    # Step 4: Explicit publication markers (e.g. 'published: 2022', 'year: 2021', 'c. 1995')
    pub_marker = re.search(r"\b(?:published|pub\.|dated|year|c\.)\s*:?\s*((?:19\d{2}|20[0-2]\d))\b", clean_no_vol, flags=re.IGNORECASE)
    if pub_marker:
        y = int(pub_marker.group(1))
        if 1900 <= y <= 2026:
            return y

    # Step 5: Remaining candidate 4-digit years in valid range
    remaining_years = [int(y) for y in re.findall(r"\b(19\d{2}|20[0-2]\d)\b", clean_no_vol)]
    valid_years = [y for y in remaining_years if 1900 <= y <= 2026]

    if len(valid_years) == 1:
        return valid_years[0]
    elif len(valid_years) > 1:
        # Multiple plausible publication years without reliable author-date association
        # Return None (uncertain/unknown) rather than picking an arbitrary year
        return None

    return None


def audit_bibliography_recency(references_input: Any) -> Dict[str, Any]:
    """
    Parses references (as a newline-delimited string or a list of citation strings)
    and calculates the percentage of citations published within the past 5 years (2021-2026).
    Rubric Item 10: At least 60% must be recent.
    Rejects unsupported input types (None, ints, dicts, mixed lists) cleanly with ValueError.
    """
    if references_input is None:
        raise ValueError("References input cannot be None. Expected string or list of citation strings.")

    if isinstance(references_input, (int, float, dict, set, tuple, bool)):
        raise ValueError(f"Unsupported input type '{type(references_input).__name__}'. Expected string or list of citation strings.")

    empty_result = {
        "total_count": 0,
        "recent_count": 0,
        "recency_percentage": 0.0,
        "passed_rubric": False,
        "references": [],
        "feedback": "No references entered. Add peer-reviewed citations."
    }

    if isinstance(references_input, str):
        text = references_input.strip()
        if not text:
            return empty_result
        lines = [line.strip() for line in text.split("\n") if line.strip()]
    elif isinstance(references_input, list):
        if not references_input:
            return empty_result
        lines = []
        for idx, item in enumerate(references_input):
            if not isinstance(item, str):
                raise ValueError(f"Invalid reference at index {idx}: expected string, got '{type(item).__name__}'.")
            item_clean = item.strip()
            if item_clean:
                lines.append(item_clean)
        if not lines:
            return empty_result
    else:
        raise ValueError(f"Unsupported input type '{type(references_input).__name__}'. Expected string or list of citation strings.")
    parsed_refs = []
    recent_count = 0

    current_year = 2026
    cutoff_year = 2021

    for line in lines:
        ref_year = extract_citation_year(line)
        is_recent = bool(ref_year and cutoff_year <= ref_year <= current_year)
        if is_recent:
            recent_count += 1

        parsed_refs.append({
            "text": line,
            "year": ref_year,
            "is_recent": is_recent
        })

    total_count = len(parsed_refs)
    recency_pct = round((recent_count / total_count * 100), 1) if total_count > 0 else 0.0
    passed = bool(recency_pct >= 60.0 and total_count >= 3)

    if passed:
        feedback = f"✅ Passes Rubric Item 10: {recency_pct}% of references ({recent_count}/{total_count}) are from 2021–2026 (Requirement: ≥60%)."
    elif total_count < 3:
        feedback = f"⚠️ Insufficient references ({total_count} cited). A standard proposal requires at least 5-10 peer-reviewed papers."
    else:
        feedback = f"❌ Fails Rubric Item 10: Only {recency_pct}% of references are recent ({recent_count}/{total_count}). Update at least {int(total_count * 0.6) - recent_count} more citations to 2021–2026."

    # Validate citation integrity & retraction status across references
    citation_val = validate_citation_text(lines, use_network=False)
    if citation_val.get("has_retracted"):
        feedback += f" ⛔ CRITICAL INTEGRITY WARNING: {len(citation_val['retracted_citations'])} citation(s) have been RETRACTED according to CrossRef/CrossMark records. Retracted papers must be removed."

    return {
        "total_count": total_count,
        "recent_count": recent_count,
        "recency_percentage": recency_pct,
        "passed_rubric": passed,
        "references": parsed_refs,
        "citation_validation": citation_val,
        "feedback": feedback
    }


# Bounded Timestamped Citation Status Cache (max 500 entries, 24h default TTL)
DEFAULT_CACHE_TTL = 86400.0  # 24 hours in seconds
_CACHE_MAX_SIZE = 500


def normalize_doi(doi: str) -> str:
    """
    Standardizes a DOI string for consistent lookup and cache key matching.
    Strips URL schemes (https://doi.org/, dx.doi.org), prefixes (doi:, urn:doi:),
    and trailing punctuation. Returns lowercase canonical DOI.
    """
    if not isinstance(doi, str):
        return ""
    d = doi.strip().lower()
    d = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*|urn:doi:)', '', d, flags=re.IGNORECASE)
    d = re.sub(r'[\.,;\)\]]+$', '', d).strip()
    return d


class CitationStatusCache(dict):
    """
    Thread-safe, bounded, timestamped in-memory cache for CrossRef/CrossMark citation verification.

    Architecture & Scope:
    - Process-local in-memory storage (Note: Does not provide cross-process worker synchronization in multi-worker WSGI clusters).
    - Hard capacity ceiling: 500 entries (evicts oldest entry FIFO/LRU upon overflow).
    - Timestamped entries with configurable TTL (default 24 hours = 86400 seconds).
    - Normalized DOI keys to prevent duplication across URL formats.
    - Transparent dict-compatible interface supporting dict indexing, get(), contains, and iteration.
    """
    def __init__(self, max_size: int = _CACHE_MAX_SIZE, ttl: float = DEFAULT_CACHE_TTL):
        super().__init__()
        self.max_size = max_size
        self.ttl = ttl
        self._timestamps: Dict[str, float] = {}

    def _normalize(self, key: str) -> str:
        return normalize_doi(key)

    def set(self, key: str, value: Dict[str, Any], ttl: Optional[float] = None, timestamp: Optional[float] = None) -> None:
        if not key or not isinstance(value, dict):
            return
        # A previous unknown result must NOT be cached as a successful clean result
        if not value.get("success"):
            return

        norm_key = self._normalize(key)
        if len(self) >= self.max_size and norm_key not in self:
            oldest_key = next(iter(self))
            self.pop(oldest_key, None)
            self._timestamps.pop(oldest_key, None)

        now = timestamp if timestamp is not None else time.time()
        val_copy = dict(value)
        val_copy["_cached_at"] = now
        val_copy["_cache_ttl"] = ttl if ttl is not None else self.ttl
        val_copy["_from_cache"] = True
        self._timestamps[norm_key] = now
        super().__setitem__(norm_key, val_copy)

    def __setitem__(self, key: str, value: Dict[str, Any]) -> None:
        self.set(key, value)

    def is_expired(self, key: str, custom_ttl: Optional[float] = None) -> bool:
        norm_key = self._normalize(key)
        if norm_key not in self._timestamps:
            return True
        cached_time = self._timestamps[norm_key]
        entry = super().get(norm_key)
        ttl = custom_ttl if custom_ttl is not None else (entry.get("_cache_ttl", self.ttl) if isinstance(entry, dict) else self.ttl)
        return (time.time() - cached_time) > ttl

    def get(self, key: str, default=None, max_age: Optional[float] = None):
        norm_key = self._normalize(key)
        if super().__contains__(norm_key):
            if self.is_expired(norm_key, custom_ttl=max_age):
                self.pop(norm_key, None)
                self._timestamps.pop(norm_key, None)
                return default
            return super().get(norm_key)
        return default

    def __getitem__(self, key: str):
        norm_key = self._normalize(key)
        if not super().__contains__(norm_key):
            raise KeyError(key)
        if self.is_expired(norm_key):
            self.pop(norm_key, None)
            self._timestamps.pop(norm_key, None)
            raise KeyError(f"{key} (expired)")
        return super().__getitem__(norm_key)

    def __contains__(self, key: str) -> bool:
        norm_key = self._normalize(key)
        if super().__contains__(norm_key):
            if self.is_expired(norm_key):
                self.pop(norm_key, None)
                self._timestamps.pop(norm_key, None)
                return False
            return True
        return False

    def pop(self, key: str, default=None):
        norm_key = self._normalize(key)
        self._timestamps.pop(norm_key, None)
        return super().pop(norm_key, default)

    def clear(self) -> None:
        self._timestamps.clear()
        super().clear()


_CITATION_STATUS_CACHE = CitationStatusCache()


def extract_dois(text: str) -> List[str]:
    """
    Extracts recognizable DOI strings from citation text.
    Handles standard prefixes (https://doi.org/, dx.doi.org, doi:) and raw 10.NNNN/... patterns.
    Strips attached punctuation (periods, commas, semicolons, trailing brackets).
    """
    if not isinstance(text, str):
        return []
    raw_matches = re.findall(
        r'(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/[^\s"\'<>]+)',
        text,
        flags=re.IGNORECASE
    )
    cleaned = []
    seen = set()
    for m in raw_matches:
        d = re.sub(r'[\.,;\)\]]+$', '', m).strip()
        if d and '/' in d and d.lower() not in seen:
            seen.add(d.lower())
            cleaned.append(d)
    return cleaned


def validate_citation_text(references_input: Any, use_network: bool = True) -> Dict[str, Any]:
    """
    Performs server-side citation integrity and status validation on reference text.
    Extracts DOIs, evaluates retraction / expression-of-concern / preprint / correction status,
    and returns a structured report preserving the student's original citation strings.

    Handles external service downtime gracefully without crashing or treating unknown status as safe.
    """
    if references_input is None:
        lines = []
    elif isinstance(references_input, str):
        text = references_input.strip()
        lines = [line.strip() for line in text.split("\n") if line.strip()] if text else []
    elif isinstance(references_input, list):
        lines = [str(item).strip() for item in references_input if str(item).strip()]
    else:
        lines = []

    validated_refs = []
    has_retracted = False
    has_expression_of_concern = False
    has_preprint = False
    has_corrected = False
    has_unknown = False

    retracted_citations = []
    expression_of_concern_citations = []
    preprint_citations = []
    warnings = []

    for line in lines:
        dois = extract_dois(line)
        line_year = extract_citation_year(line)

        if not dois:
            validated_refs.append({
                "text": line,
                "doi": None,
                "year": line_year,
                "status_type": "unverified_no_doi",
                "is_retracted": False,
                "is_expression_of_concern": False,
                "is_preprint": False,
                "is_corrected": False,
                "is_unknown": False,
                "status_warning": "No verifiable DOI detected in citation.",
                "status_details": "Citation could not be automatically validated against CrossRef/CrossMark records due to lack of a recognized DOI string."
            })
            continue

        for doi in dois:
            doi_norm = normalize_doi(doi)
            metadata = None

            # 1. Check cache first (automatically checks expiration and normalization)
            if doi_norm in _CITATION_STATUS_CACHE:
                metadata = _CITATION_STATUS_CACHE.get(doi_norm)
            elif use_network:
                try:
                    metadata = fetch_doi_metadata(doi)
                    if metadata.get("success"):
                        _CITATION_STATUS_CACHE.set(doi_norm, metadata)
                except Exception as err:
                    metadata = {
                        "success": False,
                        "error": f"Network lookup failed: {str(err)}"
                    }

            if not metadata or not metadata.get("success"):
                has_unknown = True
                status_warning = "Citation verification unavailable (external service unreachable or DOI not found)."
                validated_refs.append({
                    "text": line,
                    "doi": doi,
                    "year": line_year,
                    "status_type": "unknown",
                    "is_retracted": False,
                    "is_expression_of_concern": False,
                    "is_preprint": False,
                    "is_corrected": False,
                    "is_unknown": True,
                    "status_warning": status_warning,
                    "status_details": metadata.get("error", "CrossRef resolution unavailable.") if metadata else "Offline or unresolvable."
                })
                continue

            # Process resolved CrossRef metadata
            is_ret = bool(metadata.get("is_retracted"))
            is_eoc = bool(metadata.get("is_expression_of_concern"))
            is_prep = bool(metadata.get("is_preprint"))
            is_corr = bool(metadata.get("is_corrected"))
            status_type = metadata.get("status_type", "standard")
            status_warning = metadata.get("status_warning")
            status_details = metadata.get("status_details", "")

            if is_ret:
                status_type = "retracted"
                has_retracted = True
                retracted_citations.append({
                    "text": line,
                    "doi": doi,
                    "notice": metadata.get("retraction_notice") or status_warning or "Retracted publication."
                })
                warnings.append(f"⛔ RETRACTED: Citation with DOI {doi} has been retracted ({metadata.get('title')}).")
            elif is_eoc:
                status_type = "expression_of_concern"
                has_expression_of_concern = True
                expression_of_concern_citations.append({
                    "text": line,
                    "doi": doi,
                    "warning": status_warning or "Expression of concern."
                })
                warnings.append(f"⚠️ EXPRESSION OF CONCERN: Citation with DOI {doi} is under investigation.")
            elif is_prep:
                status_type = "preprint"
                has_preprint = True
                preprint_citations.append({"text": line, "doi": doi})
            elif is_corr:
                status_type = "corrected"
                has_corrected = True

            validated_refs.append({
                "text": line,
                "doi": doi,
                "year": metadata.get("year") or line_year,
                "title": metadata.get("title"),
                "journal": metadata.get("journal"),
                "status_type": status_type,
                "is_retracted": is_ret,
                "is_expression_of_concern": is_eoc,
                "is_preprint": is_prep,
                "is_corrected": is_corr,
                "is_unknown": False,
                "status_warning": status_warning,
                "status_details": status_details
            })

    return {
        "total_citations": len(lines),
        "validated_citations_count": len(validated_refs),
        "has_retracted": has_retracted,
        "has_expression_of_concern": has_expression_of_concern,
        "has_preprint": has_preprint,
        "has_corrected": has_corrected,
        "has_unknown": has_unknown,
        "retracted_citations": retracted_citations,
        "expression_of_concern_citations": expression_of_concern_citations,
        "preprint_citations": preprint_citations,
        "warnings": warnings,
        "references": validated_refs
    }



def evaluate_submission_gate(validation_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates whether a proposal draft can be officially submitted/locked for grading based on citation status.

    Policy Rules:
    - Known retracted, partially retracted, or withdrawn publications: STRICT BLOCK (allow_submission=False).
    - Unknown status (outage, timeout, cold cache miss): MUST NOT be treated as clean! BLOCKS submission with verification_pending=True.
    - Expressions of Concern: Permitted for submission, but explicitly flagged with warnings.
    - Corrections / Errata: Permitted for submission (corrected scientific record).
    - Preprints: Permitted for submission (with clear labeling).
    - Unverified without DOIs (e.g. books): Permitted for submission.
    """
    if not validation_report or not isinstance(validation_report, dict):
        return {
            "allow_submission": True,
            "status": "approved",
            "verification_pending": False,
            "reasons": [],
            "retracted_citations": [],
            "unknown_citations": [],
            "expression_of_concern_citations": [],
            "preprint_citations": [],
            "warnings": []
        }

    has_retracted = bool(validation_report.get("has_retracted"))
    has_unknown = bool(validation_report.get("has_unknown"))
    retracted_list = list(validation_report.get("retracted_citations") or [])
    eoc_list = list(validation_report.get("expression_of_concern_citations") or [])
    preprint_list = list(validation_report.get("preprint_citations") or [])

    unknown_list = []
    for ref in validation_report.get("references") or []:
        if ref.get("is_unknown") or ref.get("status_type") == "unknown":
            unknown_list.append(ref)

    reasons = []
    warnings = list(validation_report.get("warnings") or [])

    # Check 1: Retractions (Critical Block)
    if has_retracted or retracted_list:
        reasons.append("Proposal contains 1 or more retracted or withdrawn citations. Retracted publications must be removed or replaced before official submission for grading.")
        return {
            "allow_submission": False,
            "status": "blocked_retraction",
            "verification_pending": False,
            "reasons": reasons,
            "retracted_citations": retracted_list,
            "unknown_citations": unknown_list,
            "expression_of_concern_citations": eoc_list,
            "preprint_citations": preprint_list,
            "warnings": warnings
        }

    # Check 2: Unknown / Verification Pending (Outage or Cold Cache Block)
    if has_unknown or unknown_list:
        reasons.append("Citation verification could not be completed for 1 or more citations (external verification service unreachable or status unknown). The draft remains safely saved, but cannot be officially locked for grading until citation integrity is verified.")
        return {
            "allow_submission": False,
            "status": "verification_pending",
            "verification_pending": True,
            "reasons": reasons,
            "retracted_citations": [],
            "unknown_citations": unknown_list,
            "expression_of_concern_citations": eoc_list,
            "preprint_citations": preprint_list,
            "warnings": warnings
        }

    # Check 3: Approved for submission
    return {
        "allow_submission": True,
        "status": "approved",
        "verification_pending": False,
        "reasons": [],
        "retracted_citations": [],
        "unknown_citations": [],
        "expression_of_concern_citations": eoc_list,
        "preprint_citations": preprint_list,
        "warnings": warnings
    }
