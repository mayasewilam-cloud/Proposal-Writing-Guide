"""
BioEthics Integration Adapter for the Trusted Research Workflow Agent.
Provides a clean, validated integration bridge to the separate Google Apps Script
BioEthics Portal. Implements mock/test simulation and a live HTTP webhook client.
"""

from typing import Dict, Any, Optional
import datetime
import os
import requests


class BioEthicsAdapter:
    """
    Adapter bridging Proposal Portal with the standalone BioEthics Portal.
    """
    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.environ.get("BIOETHICS_APPS_SCRIPT_URL")

    def validate_dossier_payload(self, dossier: Dict[str, Any]) -> Dict[str, Any]:
        """Validates that dossier meets the intake schema required by BioEthics applications."""
        errors = []
        if not dossier.get("dossier_id"):
            errors.append("Missing 'dossier_id'.")
        meta = dossier.get("metadata", {})
        if not meta.get("project_id"):
            errors.append("Missing metadata: 'project_id'.")
        if not meta.get("proposal_title"):
            errors.append("Missing metadata: 'proposal_title'.")
        if not dossier.get("entity_verification_matrix"):
            errors.append("Missing 'entity_verification_matrix'.")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def dispatch_dossier(
        self,
        dossier: Dict[str, Any],
        mode: str = "auto"
    ) -> Dict[str, Any]:
        """
        Dispatches the pre-submission dossier to the BioEthics Portal.
        Falls back to validated mock simulation if endpoint URL is not configured.
        """
        val_res = self.validate_dossier_payload(dossier)
        if not val_res["valid"]:
            return {
                "success": False,
                "error": f"Schema validation failed: {'; '.join(val_res['errors'])}"
            }

        project_id = dossier.get("metadata", {}).get("project_id", "001")
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # If live URL configured and requested
        if (mode == "live" or mode == "auto") and self.endpoint_url:
            try:
                resp = requests.post(
                    self.endpoint_url,
                    json={
                        "action": "import_proposal_dossier",
                        "dossier": dossier
                    },
                    timeout=8.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "success": True,
                        "mode": "live_apps_script",
                        "remote_application_id": data.get("application_id", f"ETH-LIVE-{project_id}"),
                        "status": "SUBMITTED_TO_COORDINATOR",
                        "dispatched_at": now_iso,
                        "response": data
                    }
            except Exception as e:
                # If live call fails, record error
                return {
                    "success": False,
                    "mode": "live_apps_script_failed",
                    "error": f"Live webhook connection error: {str(e)}"
                }

        # Validated Mock Simulation (Default for local/offline testing)
        mock_remote_id = f"ETH-MSA-{project_id}-2026"
        return {
            "success": True,
            "mode": "mock_simulation",
            "remote_application_id": mock_remote_id,
            "status": "SIMULATED_HANDOFF_COMPLETED",
            "dispatched_at": now_iso,
            "message": "SIMULATED HANDOFF — NOT A REAL INSTITUTIONAL SUBMISSION. Dossier validated by BioEthics Intake Adapter (Local Mock Mode).",
            "assigned_coordinator": "Dr. Ethics Coordinator (Simulated Faculty Officer, MSA)",
            "next_step": "Coordinator or Reviewer conducts human review gate in local/test environment."
        }

    def check_application_status(self, remote_id: str) -> Dict[str, Any]:
        """Queries status of an ethics application by remote ID."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return {
            "remote_application_id": remote_id,
            "status": "PENDING_REVIEW",
            "checked_at": now_iso,
            "active_annexes": ["Annex C (Biosafety Containment)"],
            "committee_decision": "AWAITING_REVIEWER_ASSIGNMENT"
        }
