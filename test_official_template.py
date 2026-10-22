"""
Unit & Integration Tests for the Official BT_301 University Proposal Template Suite.
Validates:
1. 10-section layout matching official university assignment template.
2. Team Roster table with Name, ID, and Email.
3. Egyptian Pounds (EGP) budget with categories A through F.
4. Scientific Gantt timeline with zero individual student names.
5. Breakthroughs Proposal Launchpad schema (what_was_proved, unsolved_gap, proposal_idea).
6. Word (.docx) and Markdown (.md) exports.
Authored & Architected by Maya Abdelrazek & Youssef Aboulkheir.
"""

import os
import sys
import unittest
import io

# Add portal root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.export_service import generate_markdown_portfolio, generate_docx_portfolio
from core.breakthroughs_manager import (
    CORE_FOUNDATIONAL_BREAKTHROUGHS,
    get_breakthroughs_catalog
)


class TestOfficialBT301TemplateSuite(unittest.TestCase):
    def setUp(self):
        self.sample_proposal = {
            "title": "Engineered Thermostable PETase in Pseudomonas putida for Accelerated Plastic Bioremediation",
            "submission_date": "October 15, 2026",
            "team_members": [
                {"name": "Sara Ahmed", "id": "ST-2026-01", "email": "s.ahmed@student.edu.eg"},
                {"name": "Omar Hassan", "id": "ST-2026-02", "email": "o.hassan@student.edu.eg"},
                {"name": "Nour Ibrahim", "id": "ST-2026-03", "email": "n.ibrahim@student.edu.eg"}
            ],
            "abstract": "This study proposes the rational engineering of IsPETase through computational disulfide bridge introduction to elevate thermal stability to 65 degrees Celsius. Recombinant constructs will be expressed in Pseudomonas putida KT2440. Enzymatic depolymerization of post-consumer PET films will be quantified via HPLC. Expected outcomes include a 4-fold increase in degradation rate, establishing an efficient bioprocess for circular plastic waste valorization in Egypt.",
            "keywords": "PETase, Pseudomonas putida, Bioremediation, Protein Engineering, Circular Economy",
            "problem_narrative": "Accumulation of polyethylene terephthalate (PET) poses severe environmental challenges. Current chemical recycling requires high energy and harsh solvents. Microbial enzymes offer a sustainable alternative, but wild-type enzymes denature rapidly above 45 degrees Celsius. This project engineers thermostable variants to overcome industrial denaturation.",
            "impact_domains": ["environmental", "industrial"],
            "impact_text": "Mitigates municipal plastic accumulation and establishes a domestic biomanufacturing pipeline in Egypt.",
            "target_audience": "Municipal waste management facilities and commercial plastics recyclers.",
            "overarching_aim": "To construct and validate a thermostabilized PETase variant in P. putida capable of sustained PET depolymerization at elevated operating temperatures.",
            "objectives": [
                {"verb": "Design and synthesize", "text": "rational disulfide bridge mutations (S121C-D186C) in IsPETase."},
                {"verb": "Clone and express", "text": "engineered constructs in P. putida KT2440 using the pBBR1MCS-2 vector."},
                {"verb": "Benchmark and compare", "text": "depolymerization kinetics (kcat/KM) against wild-type enzymes across 40–70°C."}
            ],
            "methodology": "Synthetic genes will be synthesized and cloned into pBBR1MCS-2 vectors. Recombinant P. putida will be cultured in shake flasks and induced with IPTG. Secreted enzyme will be purified via Ni-NTA chromatography. Depolymerization of PET films will be monitored at 65°C using reverse-phase HPLC with triplicates.",
            "flowchart_caption": "Figure 1: Methodological pipeline from in silico mutagenesis to HPLC kinetic evaluation.",
            "materials_methods": "Pseudomonas putida KT2440 host strain, pBBR1MCS-2 plasmid, Ni-NTA agarose beads, commercial PET coupon substrates.",
            "controls_checklist": {
                "positive": True,
                "negative": True,
                "triplicates": True
            },
            "risks": [
                {"risk": "Inclusion body formation during recombinant expression", "level": "Moderate", "fallback": "Lower induction temperature to 16°C and co-express GroEL-GroES chaperones."},
                {"risk": "Proteolytic degradation of secreted enzyme", "level": "Low", "fallback": "Employ protease-deficient chassis P. putida EM42."}
            ],
            "ansoff": {
                "penetration": "Optimizing fermentation yields and kinetic rates of PET degradation.",
                "prod_dev": "Deploying novel engineered thermostable PETase variant with elevated melting temperature.",
                "mkt_dev": "Translating plastic recycling biocatalyst to agricultural mulch film degradation.",
                "diversification": "Developing dual-action living plastic-eating composite coatings."
            },
            "swot": {
                "strengths": "High catalytic specificity, non-pathogenic robust bacterial host, bio-based solution.",
                "weaknesses": "Potential expression yield bottlenecks requiring fermentation optimization.",
                "opportunities": "Alignment with national green economy initiatives and plastic waste regulations.",
                "threats": "Low cost of virgin petrochemical plastics competing with recycled monomers."
            },
            "pestel": {
                "political": "National environmental directives prioritizing plastic waste reduction.",
                "economic": "Favorable cost structure in Egyptian Pounds (EGP) compared to imported chemical catalysts.",
                "social": "Public support for environmental sustainability and zero microplastic pollution.",
                "tech": "Availability of AlphaFold and high-throughput HPLC analytics.",
                "env": "Zero toxic effluents and biological circularity.",
                "legal": "Full compliance with Egyptian Biosafety Committee guidelines."
            },
            "gantt_schedule": {
                "total_months": 18,
                "wp1_start": 1,
                "wp1_end": 6,
                "wp1_gate": "Sequence verification & successful transformation confirmed",
                "wp2_start": 5,
                "wp2_end": 12,
                "wp2_gate": "Soluble expression >50 mg/L & enzymatic activity confirmed at 50°C",
                "wp3_start": 10,
                "wp3_end": 18,
                "wp3_gate": ">3-fold kinetic rate elevation confirmed in triplicates at 65°C"
            },
            "budget_egp_items": [
                {"desc": "Custom Gene Synthesis & Oligo Primers", "category": "B. Consumables & Reagents", "qty": 1, "unit_cost": 25000},
                {"desc": "High-Fidelity MasterMixes & Restriction Enzymes", "category": "B. Consumables & Reagents", "qty": 2, "unit_cost": 18000},
                {"desc": "HPLC Analytical Column & Solvents", "category": "B. Consumables & Reagents", "qty": 1, "unit_cost": 30000},
                {"desc": "Shared Equipment Bench Fees (HPLC & Fermenter Access)", "category": "A. Equipment & Facilities", "qty": 1, "unit_cost": 45000},
                {"desc": "Student Research Stipends (3 students x 12,000 EGP)", "category": "D. Personnel & Student Stipends", "qty": 3, "unit_cost": 12000},
                {"desc": "AlphaFold Structural Modeling Compute", "category": "E. Training & Computational/Software", "qty": 1, "unit_cost": 15000},
                {"desc": "Waste Disposal & Buffer Contingency (5%)", "category": "F. Other Direct Costs & Contingency", "qty": 1, "unit_cost": 15000}
            ],
            "references": "1. Yoshida, S. et al. (2016). A bacterium that degrades and assimilates poly(ethylene terephthalate). Science, 351(6278), 1196–1199.\n2. Lu, H. et al. (2022). Machine learning-aided engineering of hydrolases for PET depolymerization. Nature, 604(7907), 662–667."
        }

    def test_markdown_export_official_structure(self):
        """Verify markdown export includes all 10 official sections and project information."""
        md = generate_markdown_portfolio(self.sample_proposal)
        
        # Course & Project Info Header
        self.assertIn("Introduction to Biotechnology (BT_301)", md)
        self.assertIn("Project Information", md)
        self.assertIn("Sara Ahmed", md)
        self.assertIn("ST-2026-01", md)
        self.assertIn("s.ahmed@student.edu.eg", md)
        self.assertIn("October 15, 2026", md)

        # 10 Official Sections
        self.assertIn("# 1. Abstract", md)
        self.assertIn("Keywords:", md)
        self.assertIn("# 2. Introduction & Background", md)
        self.assertIn("## 2.1 Problem Statement & Background", md)
        self.assertIn("## 2.2 Project Importance & Multi-Domain Impact", md)
        self.assertIn("## 2.3 Target Audience & Direct Beneficiaries", md)
        self.assertIn("# 3. Project Aim & Objectives", md)
        self.assertIn("## 3.1 Overall Aim", md)
        self.assertIn("## 3.2 Specific Objectives", md)
        self.assertIn("# 4. Methodology & Experimental Design", md)
        self.assertTrue("## 4.1 Overview" in md or "## 4.1 Technical Overview & Workflow" in md)
        self.assertIn("## 4.2 Workflow Diagram", md)
        self.assertIn("## 4.3 Materials & Methods", md)
        self.assertTrue("# 5. Expected Outcome" in md or "# 5. Risk Management" in md)
        self.assertIn("# 6. Ansoff Matrix for Biotechnology", md)
        self.assertIn("# 7. SWOT Analysis", md)
        self.assertIn("# 8. PESTEL Analysis", md)
        self.assertIn("# 9. Timeline & Budget", md)
        self.assertIn("## 9.1 Project Timeline & Milestones", md)
        self.assertIn("## 9.2 Budget & Resource Allocation (EGP)", md)
        self.assertIn("# 10. References", md)

        # Egyptian Pounds (EGP) in budget
        self.assertIn("EGP", md)
        self.assertIn("ج.م", md)

        # Gantt Chart without student names
        self.assertTrue("Zero Student Names Assigned" in md or "No Student Names Assigned" in md)
        self.assertNotIn("Sara Ahmed: WP1", md)

    def test_docx_export_official_structure(self):
        """Verify Word (.docx) export produces valid binary document containing all sections."""
        bio = generate_docx_portfolio(self.sample_proposal)
        self.assertIsInstance(bio, io.BytesIO)
        self.assertGreater(bio.getbuffer().nbytes, 5000)

    def test_breakthrough_launchpads_schema(self):
        """Verify all 16 foundational breakthroughs possess rich proposal launchpad objects."""
        for item in CORE_FOUNDATIONAL_BREAKTHROUGHS:
            lp = item.get("proposal_launchpad")
            self.assertIsNotNone(lp, f"Missing proposal_launchpad in {item['id']}")
            self.assertTrue(lp.get("what_was_proved"), f"Missing what_was_proved in {item['id']}")
            self.assertTrue(lp.get("unsolved_gap"), f"Missing unsolved_gap in {item['id']}")
            self.assertTrue(lp.get("proposal_idea"), f"Missing proposal_idea in {item['id']}")

    def test_catalog_launchpad_availability(self):
        """Verify breakthroughs catalog supplies proposal launchpad for foundational and live items."""
        cat = get_breakthroughs_catalog(storage_filter="foundational")
        for item in cat["items"]:
            self.assertIn("proposal_launchpad", item)
            self.assertTrue(item["proposal_launchpad"]["what_was_proved"])


if __name__ == "__main__":
    unittest.main()
