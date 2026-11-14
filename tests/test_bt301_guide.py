"""
Unit tests for the BT301 Complete Student Guide, Sentence Formulation Coach,
and Deliberate Contextual Guidance Engine.
"""

import unittest
import sys
import os

# Add parent directory of tests (upload) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.bt301_guide import (
    load_guide_data,
    get_all_chapters,
    get_chapter,
    search_guide,
    get_quick_finder,
    get_sentence_formulation_guide
)
from core.copilot_brain import generate_socratic_thinking_response
from app import app


class TestBT301Guide(unittest.TestCase):

    def test_load_all_31_chapters(self):
        chapters = get_all_chapters()
        self.assertEqual(len(chapters), 31)
        ch_numbers = [c["number"] for c in chapters]
        self.assertEqual(ch_numbers, list(range(1, 32)))
        self.assertIsNone(get_chapter(32))

    def test_chapter_13_building_a_sentence(self):
        ch13 = get_chapter(13)
        self.assertIsNotNone(ch13)
        self.assertEqual(ch13["number"], 13)
        self.assertIn("Building a Sentence", ch13["title"])
        self.assertIn("Subject + Verb + Object", ch13["content"])
        self.assertIn("Active vs. Passive", ch13["content"])
        self.assertIn("Choosing the Verb", ch13["content"])

    def test_chapter_29_templates(self):
        ch29 = get_chapter(29)
        self.assertIsNotNone(ch29)
        self.assertIn("Templates", ch29["title"])

    def test_search_guide(self):
        res = search_guide("hypothesis")
        self.assertGreater(len(res), 0)
        ch_nums = [r["number"] for r in res]
        self.assertIn(9, ch_nums)

    def test_quick_finder(self):
        finder = get_quick_finder()
        self.assertGreaterEqual(len(finder), 9)
        problems = [f["problem"] for f in finder]
        self.assertTrue(any("sentence" in p.lower() for p in problems))

    def test_sentence_formulation_guide(self):
        guide = get_sentence_formulation_guide()
        self.assertIn("core_formula", guide)
        self.assertIn("archetypes", guide)
        self.assertEqual(len(guide["archetypes"]), 5)

    def test_copilot_brain_sentence_query(self):
        response = generate_socratic_thinking_response(
            "can you help me and guide on how to formulate a sentence",
            {"title": "Active Proposal Draft"},
            []
        )
        self.assertEqual(response.get("concept"), "bt301_sentence_coaching")
        reply = response.get("reply", "")
        self.assertIn("Chapter 13", reply)
        self.assertIn("Subject", reply)
        self.assertIn("Active Action Verb", reply)
        self.assertNotIn("Help Me, Rhonda", reply)
        self.assertNotIn("toilet alarms", reply)

    def test_copilot_brain_guidance_query(self):
        # When user asks general "help me do this" or "guide me"
        response = generate_socratic_thinking_response(
            "help me do this",
            {"title": "the effect of detector"},
            []
        )
        self.assertEqual(response.get("concept"), "bt301_contextual_guidance")
        reply = response.get("reply", "")
        self.assertIn("the effect of detector", reply)
        self.assertIn("Diagnostic", reply)
        self.assertIn("BT301 Master Workflow", reply)
        self.assertIn("4-Part Title", reply)
        self.assertNotIn("Help Me, Rhonda", reply)

        # Another variant: "guide me"
        response2 = generate_socratic_thinking_response(
            "guide me",
            {"title": "Active Plant Formulation"},
            []
        )
        self.assertEqual(response2.get("concept"), "bt301_contextual_guidance")

    def test_copilot_brain_hypothesis_query(self):
        response = generate_socratic_thinking_response(
            "how to write a mechanistic hypothesis sentence",
            {},
            []
        )
        self.assertEqual(response.get("concept"), "bt301_hypothesis_coaching")
        reply = response.get("reply", "")
        self.assertIn("Chapter 9", reply)
        self.assertIn("We hypothesize that", reply)

    def test_copilot_brain_guide_query(self):
        response = generate_socratic_thinking_response(
            "show me the bt301 course guide",
            {},
            []
        )
        self.assertEqual(response.get("concept"), "bt301_guide_navigation")
        reply = response.get("reply", "")
        self.assertIn("31 Chapters", reply)
        self.assertIn("Part A", reply)

    def test_api_guide_endpoints(self):
        client = app.test_client()

        # 1. Chapters list
        r1 = client.get("/api/guide/chapters")
        self.assertEqual(r1.status_code, 200)
        data1 = r1.get_json()
        self.assertEqual(data1.get("total"), 31)
        r_404 = client.get("/api/guide/chapter/32")
        self.assertEqual(r_404.status_code, 404)

        # 2. Single chapter
        r2 = client.get("/api/guide/chapter/13")
        self.assertEqual(r2.status_code, 200)
        data2 = r2.get_json()
        self.assertEqual(data2.get("chapter", {}).get("number"), 13)

        # 3. Quick finder
        r3 = client.get("/api/guide/quick_finder")
        self.assertEqual(r3.status_code, 200)

        # 4. Search
        r4 = client.get("/api/guide/search?q=hypothesis")
        self.assertEqual(r4.status_code, 200)
        data4 = r4.get_json()
        self.assertGreater(len(data4.get("results", [])), 0)

        # 5. Sentence coach
        r5 = client.get("/api/guide/sentence_coach")
        self.assertEqual(r5.status_code, 200)


    def test_chapter_5_apa_7th_content(self):
        ch5 = get_chapter(5)
        self.assertIsNotNone(ch5)
        content = ch5.get("content", "")
        self.assertIn("5.2 Citing Sources in APA Style (7th Edition)", content)
        self.assertIn("5.2.1 The Two Parts of Every Citation", content)
        self.assertIn("5.2.2 In-Text Citations", content)
        self.assertIn("5.2.3 The Reference List", content)
        self.assertIn("5.2.4 Reference Formats by Source Type", content)
        self.assertIn("A. Journal article", content)
        self.assertIn("D. Report by an organization", content)
        self.assertIn("G. Preprint", content)
        self.assertIn("5.2.5 A Complete Sample Reference List", content)
        self.assertIn("5.2.6 Common APA Mistakes", content)
        self.assertIn("5.2.7 Making APA Easier with a Reference Manager", content)
        self.assertIn("5.2.8 Vancouver in Brief", content)
        self.assertIn("5.2.9 APA Quick Checklist", content)
        self.assertIn("5.3 AI Tools", content)
        self.assertIn("5.4 Research Ethics and Biosafety", content)
        self.assertIn("5.5 Tools You Will Use", content)
        self.assertIn("Chapter 5 Checklist", content)
        self.assertIn("PART B — FINDING AND SHAPING YOUR PROJECT", content)
        self.assertGreater(ch5.get("word_count", 0), 2500)

    def test_quick_finder_apa_citations(self):
        qf = get_quick_finder()
        citation_items = [item for item in qf if "cite" in item.get("problem", "").lower() or "apa" in item.get("problem", "").lower()]
        self.assertGreater(len(citation_items), 0)
        self.assertIn(5, citation_items[0].get("chapters", []))

    def test_copilot_apa_citation_coach(self):
        # General APA inquiry
        r1 = generate_socratic_thinking_response("how to cite in APA 7th style", {}, [])
        self.assertEqual(r1.get("concept"), "bt301_apa_citations")
        self.assertIn("Matching Rule", r1.get("reply", ""))
        self.assertGreater(len(r1.get("thinking", [])), 0)
        self.assertGreater(len(r1.get("actions", [])), 0)

        # Author count and et al. inquiry
        r2 = generate_socratic_thinking_response("how many authors before et al in APA", {}, [])
        self.assertEqual(r2.get("concept"), "bt301_apa_citations")
        self.assertIn("Three or more authors", r2.get("reply", ""))

        # Common mistakes inquiry
        r3 = generate_socratic_thinking_response("what are common APA citation mistakes", {}, [])
        self.assertEqual(r3.get("concept"), "bt301_apa_citations")
        self.assertIn("sentence case", r3.get("reply", "").lower())

        # Specific preprint template inquiry
        r4 = generate_socratic_thinking_response("how to cite a preprint on biorxiv in APA", {}, [])
        self.assertEqual(r4.get("concept"), "bt301_apa_citations")
        self.assertIn("bioRxiv", r4.get("reply", ""))

    def test_socratic_engine_section_10_and_in_text(self):
        from core.socratic_engine import analyze_student_draft

        # Section 10 reference audit
        draft_refs = """Livak, K. J., & Schmittgen, T. D. (2001). Analysis of relative gene expression data. Methods, 25(4), 402-408. https://doi.org/10.1006/meth.2001.1262
Rahman, M. A. and Lopez, J. (2023). Study of Calendula Cream. Journal of Dermatology, 10(2), 1-10. doi: 10.1234/derm.2023.01.
Chen, L. et al. (2024). Lipid nanoparticles for herbal delivery. bioRxiv. https://doi.org/10.1101/2024.01.01.
"""
        res = analyze_student_draft("Section 10 - References Cited", draft_refs)
        self.assertEqual(res.get("status"), "analyzed")
        needs_att = " ".join(res.get("needs_attention", []))
        self.assertIn("Alphabetical Order", needs_att)
        self.assertIn("Modern DOI Format", needs_att)
        self.assertIn("No Trailing Period", needs_att)
        self.assertIn("Author List Syntax", needs_att)

        # Section 2 in-text citation diagnostics
        prose = "Inflammation is a common skin problem (Rahman and Lopez, 2023). Another team found similar results (Chen, Smith, and Davis, 2021). Others agreed et. al recently."
        res_prose = analyze_student_draft("Section 2 - Introduction", prose)
        needs_att_prose = " ".join(res_prose.get("needs_attention", []))
        self.assertIn("ampersand", needs_att_prose.lower())
        self.assertIn("et al.", needs_att_prose)
        self.assertIn("3+ authors", needs_att_prose.lower())



    def test_scientific_proposal_and_expected_outcomes_purity(self):
        # 1. Chapter 26 must be dedicated to Section 5 Expected Outcomes & Alternative Strategies
        ch26 = get_chapter(26)
        self.assertIsNotNone(ch26)
        content = ch26['content']
        self.assertIn('Expected Outcomes & Technical Benchmarks', ch26['title'])
        self.assertIn('Dynamic Light Scattering', content)
        self.assertIn('RAW 264.7', content)
        self.assertNotIn("The Reviewer's Safety Check", content)
        
        # Must have zero corporate/HR filler words
        self.assertNotIn('4 students trained', content.lower())
        self.assertNotIn('training log', content.lower())
        self.assertNotIn('1 poster, 1 manuscript draft', content.lower())
        
        # 2. Chapter 19 must outline the 10-section proposal
        ch19 = get_chapter(19)
        self.assertIsNotNone(ch19)
        self.assertIn('Ten-Section Architecture', ch19['title'])
        self.assertIn('Expected Outcomes & Technical Benchmarks', ch19['content'])
        self.assertIn('References Cited — APA 7th Edition', ch19['content'])


if __name__ == "__main__":
    unittest.main()
