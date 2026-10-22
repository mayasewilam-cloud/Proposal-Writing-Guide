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

    def test_load_all_34_chapters(self):
        chapters = get_all_chapters()
        self.assertEqual(len(chapters), 29)
        ch_numbers = [c["number"] for c in chapters]
        self.assertEqual(ch_numbers, list(range(1, 27)) + [31, 32, 33])

    def test_chapter_13_building_a_sentence(self):
        ch13 = get_chapter(13)
        self.assertIsNotNone(ch13)
        self.assertEqual(ch13["number"], 13)
        self.assertIn("Building a Sentence", ch13["title"])
        self.assertIn("Subject + Verb + Object", ch13["content"])
        self.assertIn("Active vs. Passive", ch13["content"])
        self.assertIn("Choosing the Verb", ch13["content"])

    def test_chapter_31_templates(self):
        ch31 = get_chapter(31)
        self.assertIsNotNone(ch31)
        self.assertIn("Templates", ch31["title"])

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
        self.assertIn("29 Chapters", reply)
        self.assertIn("Part A", reply)

    def test_api_guide_endpoints(self):
        client = app.test_client()

        # 1. Chapters list
        r1 = client.get("/api/guide/chapters")
        self.assertEqual(r1.status_code, 200)
        data1 = r1.get_json()
        self.assertEqual(data1.get("total"), 29)

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


if __name__ == "__main__":
    unittest.main()
