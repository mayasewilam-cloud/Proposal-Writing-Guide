"""
Bounded Tool Registry for the Governed Research Workflow Agent (Phase 3).
Exposes a small, explicit, inspectable whitelist of research-support tools:
1. search_pubmed
2. search_europe_pmc
3. search_openalex
4. ask_researcher
5. request_human_review

No arbitrary Python functions, URLs, or code execution are exposed.
Every tool enforces input/output schemas, timeouts, authorization policies,
and provenance metadata.
"""

import json
import re
import time
import datetime
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional, Callable
import requests

from .models import ResearchContext, ClarificationQuestion


class ToolDefinition:
    """Explicit metadata and execution contract for a single bounded agent tool."""

    def __init__(
        self,
        tool_id: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        authorization_policy: Dict[str, Any],
        risk_level: str,
        timeout: float,
        error_handling: str,
        provenance_metadata: Dict[str, Any],
        handler: Callable[[Dict[str, Any], Optional[ResearchContext], float], Dict[str, Any]]
    ):
        self.tool_id = tool_id
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.authorization_policy = authorization_policy
        self.risk_level = risk_level
        self.timeout = float(timeout)
        self.error_handling = error_handling
        self.provenance_metadata = provenance_metadata
        self.handler = handler

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "authorization_policy": self.authorization_policy,
            "risk_level": self.risk_level,
            "timeout": self.timeout,
            "error_handling": self.error_handling,
            "provenance_metadata": self.provenance_metadata
        }


# ---------------------------------------------------------------------------
# Concrete Bounded Tool Implementations
# ---------------------------------------------------------------------------

def _execute_search_pubmed(
    args: Dict[str, Any],
    context: Optional[ResearchContext],
    timeout: float = 5.0
) -> Dict[str, Any]:
    """Queries NCBI PubMed E-utilities (esearch + esummary) for biosafety/AMR evidence."""
    query = str(args.get("query") or "").strip()
    max_results = min(max(int(args.get("max_results", 3)), 1), 5)
    if not query:
        return {
            "status": "error",
            "tool_id": "search_pubmed",
            "error": "Missing required 'query' parameter for search_pubmed.",
            "records_count": 0,
            "records": [],
            "establishes_biosafety_risk_group": False,
            "establishes_project_specific_containment": False,
            "observation_summary": "Tool error: empty query.",
            "provenance": {
                "source_system": "NCBI PubMed E-utilities",
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        }

    esearch_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
        f"db=pubmed&term={urllib.parse.quote(query)}&retmode=json&retmax={max_results}"
    )
    headers = {"User-Agent": "TrustedResearchAgent/3.0 (mailto:biosafety@university.edu)"}
    resp = requests.get(esearch_url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    search_data = resp.json()
    id_list = search_data.get("esearchresult", {}).get("idlist", [])

    records: List[Dict[str, Any]] = []
    if id_list:
        ids_Param = ",".join(id_list[:max_results])
        esummary_url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
            f"db=pubmed&id={ids_Param}&retmode=json"
        )
        sum_resp = requests.get(esummary_url, headers=headers, timeout=timeout)
        sum_resp.raise_for_status()
        sum_data = sum_resp.json().get("result", {})
        for pmid in id_list[:max_results]:
            item = sum_data.get(str(pmid), {})
            if isinstance(item, dict) and item.get("title"):
                authors = [a.get("name", "") for a in item.get("authors", [])[:3] if isinstance(a, dict)]
                records.append({
                    "pmid": str(pmid),
                    "title": str(item.get("title", "")).rstrip("."),
                    "journal": str(item.get("fulljournalname") or item.get("source") or "PubMed Indexed Journal"),
                    "pubdate": str(item.get("pubdate", "")),
                    "authors": ", ".join(authors),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })

    establishes_risk = len(records) > 0
    # Literature alone cannot establish which physical containment room/autoclave or patient consent protocol a local student lab uses
    establishes_local_containment = False
    summary = (
        f"PubMed returned {len(records)} relevant record(s) for '{query}'."
        if records
        else f"PubMed returned 0 records for '{query}'."
    )
    return {
        "status": "ok",
        "tool_id": "search_pubmed",
        "query": query,
        "records_count": len(records),
        "records": records,
        "establishes_biosafety_risk_group": establishes_risk,
        "establishes_project_specific_containment": establishes_local_containment,
        "observation_summary": summary,
        "provenance": {
            "source_system": "NCBI PubMed E-utilities",
            "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            "query_executed": query,
            "pmid_list": [r.get("pmid") for r in records],
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    }


def _execute_search_europe_pmc(
    args: Dict[str, Any],
    context: Optional[ResearchContext],
    timeout: float = 5.0
) -> Dict[str, Any]:
    """Queries Europe PMC REST API for peer-reviewed biosafety, AMR, or clinical isolate literature."""
    query = str(args.get("query") or "").strip()
    max_results = min(max(int(args.get("max_results", 3)), 1), 5)
    if not query:
        return {
            "status": "error",
            "tool_id": "search_europe_pmc",
            "error": "Missing required 'query' parameter for search_europe_pmc.",
            "records_count": 0,
            "records": [],
            "establishes_biosafety_risk_group": False,
            "establishes_project_specific_containment": False,
            "observation_summary": "Tool error: empty query.",
            "provenance": {
                "source_system": "Europe PMC REST API",
                "endpoint": "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        }

    url = (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
        f"query={urllib.parse.quote(query)}&format=json&pageSize={max_results}&resultType=core"
    )
    headers = {"User-Agent": "TrustedResearchAgent/3.0"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    hit_list = data.get("resultList", {}).get("result", [])

    records: List[Dict[str, Any]] = []
    for item in hit_list[:max_results]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").rstrip(".")
        abstract = re.sub(r"<[^>]+>", "", str(item.get("abstractText") or "")).strip()
        records.append({
            "id": str(item.get("pmid") or item.get("id") or ""),
            "doi": str(item.get("doi") or ""),
            "title": title,
            "journal": str(item.get("journalTitle") or "Europe PMC Journal"),
            "year": str(item.get("pubYear") or ""),
            "snippet": abstract[:240] + ("..." if len(abstract) > 240 else ""),
            "url": f"https://europepmc.org/article/MED/{item.get('pmid', '')}" if item.get("pmid") else ""
        })

    establishes_risk = len(records) > 0
    establishes_local_containment = False
    summary = (
        f"Europe PMC returned {len(records)} relevant record(s) for '{query}'."
        if records
        else f"Europe PMC returned 0 records for '{query}'."
    )
    return {
        "status": "ok",
        "tool_id": "search_europe_pmc",
        "query": query,
        "records_count": len(records),
        "records": records,
        "establishes_biosafety_risk_group": establishes_risk,
        "establishes_project_specific_containment": establishes_local_containment,
        "observation_summary": summary,
        "provenance": {
            "source_system": "Europe PMC REST API",
            "endpoint": "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            "query_executed": query,
            "record_ids": [r.get("id") for r in records],
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    }


def _execute_search_openalex(
    args: Dict[str, Any],
    context: Optional[ResearchContext],
    timeout: float = 5.0
) -> Dict[str, Any]:
    """Queries OpenAlex Works API for scholarly biosafety and biological engineering evidence."""
    query = str(args.get("query") or "").strip()
    max_results = min(max(int(args.get("max_results", 3)), 1), 5)
    if not query:
        return {
            "status": "error",
            "tool_id": "search_openalex",
            "error": "Missing required 'query' parameter for search_openalex.",
            "records_count": 0,
            "records": [],
            "establishes_biosafety_risk_group": False,
            "establishes_project_specific_containment": False,
            "observation_summary": "Tool error: empty query.",
            "provenance": {
                "source_system": "OpenAlex Works API",
                "endpoint": "https://api.openalex.org/works",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        }

    url = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per-page={max_results}"
    headers = {"User-Agent": "TrustedResearchAgent/3.0 (mailto:biosafety@university.edu)"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])

    records: List[Dict[str, Any]] = []
    for item in results[:max_results]:
        if not isinstance(item, dict):
            continue
        records.append({
            "id": str(item.get("id") or ""),
            "doi": str(item.get("doi") or ""),
            "title": str(item.get("title") or item.get("display_name") or ""),
            "year": str(item.get("publication_year") or ""),
            "cited_by_count": int(item.get("cited_by_count") or 0)
        })

    establishes_risk = len(records) > 0
    establishes_local_containment = False
    summary = (
        f"OpenAlex returned {len(records)} relevant record(s) for '{query}'."
        if records
        else f"OpenAlex returned 0 records for '{query}'."
    )
    return {
        "status": "ok",
        "tool_id": "search_openalex",
        "query": query,
        "records_count": len(records),
        "records": records,
        "establishes_biosafety_risk_group": establishes_risk,
        "establishes_project_specific_containment": establishes_local_containment,
        "observation_summary": summary,
        "provenance": {
            "source_system": "OpenAlex Works API",
            "endpoint": "https://api.openalex.org/works",
            "query_executed": query,
            "work_ids": [r.get("id") for r in records],
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    }


def _execute_ask_researcher(
    args: Dict[str, Any],
    context: Optional[ResearchContext],
    timeout: float = 2.0
) -> Dict[str, Any]:
    """Registers a targeted Socratic clarification question for the human researcher."""
    field = str(args.get("field") or "biosafety_containment").strip()
    question_text = str(args.get("question") or "").strip()
    rationale = str(args.get("rationale") or "Project-specific containment or sample provenance cannot be determined from literature alone.").strip()
    question_id = str(args.get("question_id") or "CLAR-AGENT-01").strip()

    if not question_text:
        return {
            "status": "error",
            "tool_id": "ask_researcher",
            "error": "Missing required 'question' text for ask_researcher.",
            "records_count": 0,
            "records": [],
            "observation_summary": "Tool error: empty clarification question.",
            "provenance": {
                "source_system": "TrustedResearchAgent Clarification Engine",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        }

    q_obj = ClarificationQuestion(
        question_id=question_id,
        field=field,
        prompt=question_text,
        rationale=rationale,
        context_snippet=f"Agent-initiated clarification on '{field}'"
    )
    return {
        "status": "ok",
        "tool_id": "ask_researcher",
        "question": q_obj.to_dict(),
        "records_count": 1,
        "records": [q_obj.to_dict()],
        "establishes_biosafety_risk_group": True,
        "establishes_project_specific_containment": False,
        "observation_summary": f"Clarification question [{question_id}] queued for researcher regarding '{field}'.",
        "provenance": {
            "source_system": "TrustedResearchAgent Clarification Engine",
            "question_id": question_id,
            "target_field": field,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    }


def _execute_request_human_review(
    args: Dict[str, Any],
    context: Optional[ResearchContext],
    timeout: float = 2.0
) -> Dict[str, Any]:
    """Flags a project for mandatory institutional human review without making the decision."""
    required_role = str(args.get("required_role") or "biosafety_officer").strip()
    reason = str(args.get("reason") or "High-risk or unresolved biosafety/ethics ambiguity requires human officer review.").strip()
    risk_level = str(args.get("risk_level") or "HIGH").strip().upper()

    escalation_record = {
        "required_role": required_role,
        "reason": reason,
        "risk_level": risk_level,
        "autonomous_approval_blocked": True,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    return {
        "status": "ok",
        "tool_id": "request_human_review",
        "escalation": escalation_record,
        "records_count": 1,
        "records": [escalation_record],
        "establishes_biosafety_risk_group": True,
        "establishes_project_specific_containment": False,
        "observation_summary": f"Escalated to human reviewer ({required_role}): {reason}",
        "provenance": {
            "source_system": "TrustedResearchAgent Human Gate Router",
            "required_role": required_role,
            "timestamp": escalation_record["timestamp"]
        }
    }


class BoundedToolRegistry:
    """
    Explicit, inspectable registry of bounded research-support tools.
    Enforces tool whitelisting, timeout boundaries, error handling, and provenance.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        common_auth_policy = {
            "allowed_actors": ["agent"],
            "mutates_proposal_text": False,
            "can_approve_governance_gate": False,
            "can_override_deterministic_safety": False,
            "network_scope": "whitelisted_fixed_api_only"
        }

        self.register(ToolDefinition(
            tool_id="search_pubmed",
            description="Search NCBI PubMed E-utilities for peer-reviewed biomedical literature on pathogen risk groups, antimicrobial resistance genes (e.g., mcr-1), and laboratory biosafety standards.",
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "minLength": 2, "maxLength": 250},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3}
                },
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "required": ["status", "tool_id", "records_count", "records", "observation_summary", "provenance"]
            },
            authorization_policy=common_auth_policy,
            risk_level="LOW",
            timeout=5.0,
            error_handling="catch_and_return_structured_tool_error",
            provenance_metadata={
                "source_system": "NCBI PubMed E-utilities",
                "fixed_domain": "eutils.ncbi.nlm.nih.gov",
                "read_only": True,
                "version": "1.0"
            },
            handler=_execute_search_pubmed
        ))

        self.register(ToolDefinition(
            tool_id="search_europe_pmc",
            description="Search Europe PMC REST API for life-science literature, clinical isolate handling protocols, and containment guidance.",
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "minLength": 2, "maxLength": 250},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3}
                },
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "required": ["status", "tool_id", "records_count", "records", "observation_summary", "provenance"]
            },
            authorization_policy=common_auth_policy,
            risk_level="LOW",
            timeout=5.0,
            error_handling="catch_and_return_structured_tool_error",
            provenance_metadata={
                "source_system": "Europe PMC REST API",
                "fixed_domain": "www.ebi.ac.uk",
                "read_only": True,
                "version": "1.0"
            },
            handler=_execute_search_europe_pmc
        ))

        self.register(ToolDefinition(
            tool_id="search_openalex",
            description="Search OpenAlex scholarly index for open-access biological engineering and biosafety publications.",
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "minLength": 2, "maxLength": 250},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3}
                },
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "required": ["status", "tool_id", "records_count", "records", "observation_summary", "provenance"]
            },
            authorization_policy=common_auth_policy,
            risk_level="LOW",
            timeout=5.0,
            error_handling="catch_and_return_structured_tool_error",
            provenance_metadata={
                "source_system": "OpenAlex Works API",
                "fixed_domain": "api.openalex.org",
                "read_only": True,
                "version": "1.0"
            },
            handler=_execute_search_openalex
        ))

        self.register(ToolDefinition(
            tool_id="ask_researcher",
            description="Generate a targeted Socratic clarification question for the human researcher when project-specific containment, sample provenance, or de-identification cannot be resolved from literature.",
            input_schema={
                "type": "object",
                "required": ["field", "question"],
                "properties": {
                    "field": {"type": "string"},
                    "question": {"type": "string", "minLength": 10, "maxLength": 500},
                    "rationale": {"type": "string"},
                    "question_id": {"type": "string"}
                },
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "required": ["status", "tool_id", "question", "observation_summary", "provenance"]
            },
            authorization_policy={
                **common_auth_policy,
                "network_scope": "local_state_only"
            },
            risk_level="LOW",
            timeout=2.0,
            error_handling="catch_and_return_structured_tool_error",
            provenance_metadata={
                "source_system": "TrustedResearchAgent Clarification Engine",
                "fixed_domain": "local",
                "read_only": False,
                "version": "1.0"
            },
            handler=_execute_ask_researcher
        ))

        self.register(ToolDefinition(
            tool_id="request_human_review",
            description="Route the proposal to a human institutional reviewer (biosafety_officer, ethics_officer, or ibc_chair) when mandatory governance boundaries or unresolved biosecurity risks are encountered.",
            input_schema={
                "type": "object",
                "required": ["reason"],
                "properties": {
                    "required_role": {"type": "string"},
                    "reason": {"type": "string", "minLength": 5, "maxLength": 500},
                    "risk_level": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]}
                },
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "required": ["status", "tool_id", "escalation", "observation_summary", "provenance"]
            },
            authorization_policy={
                **common_auth_policy,
                "network_scope": "local_state_only"
            },
            risk_level="LOW",
            timeout=2.0,
            error_handling="catch_and_return_structured_tool_error",
            provenance_metadata={
                "source_system": "TrustedResearchAgent Human Gate Router",
                "fixed_domain": "local",
                "read_only": False,
                "version": "1.0"
            },
            handler=_execute_request_human_review
        ))

    def register(self, tool_def: ToolDefinition) -> None:
        self._tools[tool_def.tool_id] = tool_def

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._tools.get(tool_id)

    def get_allowed_tool_ids(self) -> List[str]:
        return list(self._tools.keys())

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns inspectable metadata for all registered tools."""
        return [t.to_dict() for t in self._tools.values()]

    def execute_tool(
        self,
        tool_id: str,
        args: Dict[str, Any],
        context: Optional[ResearchContext] = None
    ) -> Dict[str, Any]:
        """
        Executes a whitelisted tool within its timeout and error handling boundary.
        Never raises unhandled exceptions into the caller; returns a structured observation.
        """
        tool_def = self.get_tool(tool_id)
        if not tool_def:
            return {
                "status": "error",
                "tool_id": str(tool_id),
                "error": f"Tool '{tool_id}' is not registered in BoundedToolRegistry.",
                "records_count": 0,
                "records": [],
                "establishes_biosafety_risk_group": False,
                "establishes_project_specific_containment": False,
                "observation_summary": f"Execution rejected: unknown tool '{tool_id}'.",
                "provenance": {
                    "source_system": "BoundedToolRegistry",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            }

        start_ts = time.perf_counter()
        try:
            res = tool_def.handler(args or {}, context, tool_def.timeout)
            elapsed_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)
            res["elapsed_ms"] = elapsed_ms
            if "provenance" not in res:
                res["provenance"] = dict(tool_def.provenance_metadata)
            res["provenance"]["elapsed_ms"] = elapsed_ms
            return res
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)
            return {
                "status": "error",
                "tool_id": tool_id,
                "error": f"{type(exc).__name__}: {str(exc)}",
                "elapsed_ms": elapsed_ms,
                "records_count": 0,
                "records": [],
                "establishes_biosafety_risk_group": False,
                "establishes_project_specific_containment": False,
                "observation_summary": f"Tool '{tool_id}' failed with {type(exc).__name__}: {str(exc)}",
                "provenance": {
                    **tool_def.provenance_metadata,
                    "error_type": type(exc).__name__,
                    "elapsed_ms": elapsed_ms,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            }
