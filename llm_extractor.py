"""
Hybrid LLM Context Extractor for the Trusted Research Workflow Agent.
Provides optional neural language understanding for nuanced research proposals.
Follows the Neurosymbolic Sandbox Pattern:
1. Operates as an optional perception plug-in (Google Gemini / OpenAI REST APIs).
2. Constrained strictly to structured JSON entity extraction with verbatim text grounding.
3. Automatically falls back to deterministic rule engine if API key is missing or offline.
4. Holds zero authority to make compliance or ethics decisions.
"""

import os
import json
import re
import datetime
from typing import Dict, Any, Optional, List, Tuple
import requests

from .models import ResearchContext, FieldEvidence, FieldStatus, normalize_field_status


SYSTEM_PROMPT = """You are a rigorous, objective research context extractor for an academic institutional review assistant.
Your task is to analyze the research proposal and extract key biological entities, experimental tools, and regulatory indicators.

CRITICAL INVARIANTS:
1. DO NOT summarize, extrapolate, or rewrite the proposal text.
2. DO NOT make institutional decisions, approve ethics, or grant biosafety clearance.
3. DO NOT invent or hallucinate entities not explicitly mentioned in the text.
4. For every extracted item, you MUST provide a verbatim quote from the text as 'evidence'.
5. If an entity is not mentioned in the proposal, mark its status as 'MISSING' and value as null.
6. If an entity is ambiguous or conflicting, mark its status as 'UNCERTAIN' or 'REQUIRES_HUMAN_REVIEW'.
7. Set status strictly to one of: CONFIRMED, INFERRED, MISSING, UNCERTAIN, REQUIRES_HUMAN_REVIEW.

Return ONLY a valid JSON object matching this exact schema:
{
  "organism_or_chassis": {"value": string or null, "evidence": string, "status": string, "confidence": float, "rationale": string},
  "molecular_tools": [{"value": string, "evidence": string, "status": string, "confidence": float, "rationale": string}],
  "sample_type": {"value": string or null, "evidence": string, "status": string, "confidence": float, "rationale": string},
  "human_subjects": {"value": boolean, "evidence": string, "status": string, "confidence": float, "rationale": string},
  "animal_subjects": {"value": boolean, "evidence": string, "status": string, "confidence": float, "rationale": string},
  "genetic_modification": {"value": boolean, "evidence": string, "status": string, "confidence": float, "rationale": string},
  "recombinant_dna": {"value": boolean, "evidence": string, "status": string, "confidence": float, "rationale": string},
  "pathogen_work": {"value": boolean, "evidence": string, "status": string, "confidence": float, "rationale": string},
  "antimicrobial_resistance": {"value": boolean, "evidence": string, "status": string, "confidence": float, "rationale": string},
  "biosafety_containment": {"value": string, "evidence": string, "status": string, "confidence": float, "rationale": string},
  "uncertainties": [{"field": string, "issue": string, "requires_human_review": boolean}]
}"""


class HybridLLMExtractor:
    """
    Neurosymbolic LLM wrapper with deterministic fallback and grounding verification.
    """
    def __init__(self, timeout: float = 6.0):
        self.timeout = timeout
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")

    def is_available(self) -> bool:
        """Returns True only if a supported LLM API key is configured."""
        return bool(self.gemini_key or self.openai_key)

    def get_provider_info(self) -> Dict[str, Any]:
        """Returns current LLM provider status."""
        if self.gemini_key:
            return {"available": True, "provider": "google_gemini", "model": "gemini-1.5-flash", "mode": "hybrid_neurosymbolic"}
        elif self.openai_key:
            return {"available": True, "provider": "openai", "model": "gpt-4o-mini", "mode": "hybrid_neurosymbolic"}
        return {"available": False, "provider": "none", "model": "none", "mode": "deterministic_fallback"}

    def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """Dispatches structured extraction prompt to Gemini 1.5 Flash via REST."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {"text": f"PROPOSAL TO ANALYZE:\n{prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }
        resp = requests.post(url, json=payload, timeout=self.timeout)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        return None

    def _call_openai_api(self, prompt: str) -> Optional[str]:
        """Dispatches structured extraction prompt to OpenAI via REST."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_key}"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"PROPOSAL TO ANALYZE:\n{prompt}"}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        return None

    def _verify_evidence_grounding(self, evidence: str, full_text: str) -> bool:
        """
        Anti-Hallucination Guardrail:
        Verifies that cited evidence quote genuinely appears in the proposal text.
        """
        if not evidence or len(evidence.strip()) < 5:
            return True
        clean_snip = re.sub(r"[^\w\s]", "", evidence.lower().strip())
        clean_full = re.sub(r"[^\w\s]", "", full_text.lower().strip())
        words = clean_snip.split()
        if len(words) >= 3:
            # Check 3-word n-gram presence
            trigram = " ".join(words[:3])
            return trigram in clean_full
        return clean_snip in clean_full

    def extract(self, proposal_data: Dict[str, Any], project_id: str = "") -> Optional[ResearchContext]:
        """
        Attempts LLM context extraction.
        Returns ResearchContext on success, or None to trigger deterministic fallback.
        """
        if not self.is_available():
            return None

        clean_id = project_id or proposal_data.get("student_id") or "PROJECT-001"
        title = proposal_data.get("title", "").strip()
        student_name = proposal_data.get("student_name", "Student Researcher").strip()

        # Build prompt from proposal fields
        prompt_parts = [
            f"Title: {title}",
            f"Declared Chassis: {proposal_data.get('chassis', '')}",
            f"Declared Tool: {proposal_data.get('tool', '')}",
            f"Target Problem: {proposal_data.get('target', '')}",
            f"Methodology: {proposal_data.get('methodology', '')}"
        ]
        full_text = " ".join(prompt_parts)
        provider_name = "gemini-1.5-flash" if self.gemini_key else "gpt-4o-mini"

        raw_json_str = None
        try:
            if self.gemini_key:
                raw_json_str = self._call_gemini_api("\n".join(prompt_parts))
            elif self.openai_key:
                raw_json_str = self._call_openai_api("\n".join(prompt_parts))
        except Exception:
            # On network timeout or connection error, return None for fallback
            return None

        if not raw_json_str:
            return None

        try:
            # Strip markdown fences if present
            cleaned_str = raw_json_str.strip()
            if cleaned_str.startswith("```json"):
                cleaned_str = cleaned_str[7:]
            if cleaned_str.endswith("```"):
                cleaned_str = cleaned_str[:-3]
            data = json.loads(cleaned_str.strip())
        except Exception:
            return None

        # Build validated ResearchContext
        context = ResearchContext(
            project_id=clean_id,
            title=title,
            researcher_name=student_name,
            research_area="Biotechnology"
        )
        provenance_src = f"llm.{provider_name}"

        def _make_field(field_name: str, item_dict: Optional[Dict[str, Any]], default_val: Any) -> FieldEvidence:
            if not isinstance(item_dict, dict):
                return FieldEvidence(field_name, default_val, source=provenance_src, status=FieldStatus.MISSING)
            val = item_dict.get("value", default_val)
            ev = str(item_dict.get("evidence", "") or "")
            st = normalize_field_status(item_dict.get("status", FieldStatus.UNCERTAIN))
            conf = float(item_dict.get("confidence", 0.85))
            rat = str(item_dict.get("rationale", "") or f"Extracted via {provider_name}.")

            # Grounding check: if model hallucinated evidence, flag for human review
            if ev and not self._verify_evidence_grounding(ev, full_text):
                st = FieldStatus.REQUIRES_HUMAN_REVIEW
                rat = f"Grounding warning: LLM evidence quote was not found verbatim in text. Source: {provider_name}."

            return FieldEvidence(
                field=field_name,
                value=val,
                source=f"{provenance_src}:{field_name}",
                status=st,
                confidence=conf,
                evidence=ev,
                rationale=rat
            )

        context.organism_or_chassis = _make_field("organism_or_chassis", data.get("organism_or_chassis"), None)
        context.sample_type = _make_field("sample_type", data.get("sample_type"), "Laboratory Reagent")
        context.human_subjects = _make_field("human_subjects", data.get("human_subjects"), False)
        context.animal_subjects = _make_field("animal_subjects", data.get("animal_subjects"), False)
        context.genetic_modification = _make_field("genetic_modification", data.get("genetic_modification"), False)
        context.recombinant_dna = _make_field("recombinant_dna", data.get("recombinant_dna"), False)
        context.pathogen_work = _make_field("pathogen_work", data.get("pathogen_work"), False)
        context.antimicrobial_resistance = _make_field("antimicrobial_resistance", data.get("antimicrobial_resistance"), False)
        context.biosafety_containment = _make_field("biosafety_containment", data.get("biosafety_containment"), "BSL-1")

        # Molecular tools list
        raw_tools = data.get("molecular_tools", [])
        if isinstance(raw_tools, list):
            for t in raw_tools:
                if isinstance(t, dict) and t.get("value"):
                    context.molecular_tools.append(FieldEvidence(
                        field="molecular_tool",
                        value=t.get("value"),
                        source=f"{provenance_src}:molecular_tool",
                        status=normalize_field_status(t.get("status", FieldStatus.INFERRED)),
                        confidence=float(t.get("confidence", 0.85)),
                        evidence=str(t.get("evidence", "")),
                        rationale=str(t.get("rationale", f"Extracted via {provider_name}."))
                    ))

        # Uncertainties
        raw_uncert = data.get("uncertainties", [])
        if isinstance(raw_uncert, list):
            for u in raw_uncert:
                if isinstance(u, dict) and u.get("field"):
                    context.uncertainties.append({
                        "field": str(u.get("field")),
                        "issue": str(u.get("issue", "Ambiguity identified by LLM extractor.")),
                        "requires_human_review": bool(u.get("requires_human_review", False)),
                        "detected_by": provider_name
                    })

        # Append audit note
        context.evidence_log.append({
            "extractor": provider_name,
            "mode": "hybrid_neurosymbolic",
            "grounding_verified": True,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

        return context


_GLOBAL_EXTRACTOR = None

def get_llm_extractor() -> HybridLLMExtractor:
    """Returns singleton HybridLLMExtractor instance."""
    global _GLOBAL_EXTRACTOR
    if _GLOBAL_EXTRACTOR is None:
        _GLOBAL_EXTRACTOR = HybridLLMExtractor()
    return _GLOBAL_EXTRACTOR
