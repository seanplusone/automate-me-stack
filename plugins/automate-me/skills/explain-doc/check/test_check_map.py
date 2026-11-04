import copy
import unittest

from check_map import check
from render_page import render

GOOD = {
    "title": "Sync Link",
    "source": {"path": "docs/design/x.md"},
    "big_picture": "Records A, B and C link to rows 1, 2 and 3. A reload can renumber them. The design stops the sync before it writes.",
    "flow": {"stages": [{"name": "Read", "text": "The sync reads every row.",
                         "table": {"head": ["If", "Then"], "rows": [["A row moved", "The sync stops"]]}}]},
    "sections": [{"name": "Summary", "lines": "11-24", "summary": "The design in five rules.", "points": ["One record per row."]}],
    "wrong": [{"text": "Two counts disagree.", "lines": "36, 978", "label": "measured"}],
    "legend": {"sync": "The job that copies rows into records."},
}


def errors(m):
    return check(m)[0]


class CheckMap(unittest.TestCase):
    def test_good_map_passes(self):
        self.assertEqual(errors(GOOD), [])

    def test_long_big_picture_fails(self):
        m = copy.deepcopy(GOOD)
        m["big_picture"] = "One. Two. Three. Four. Five. Six."
        self.assertTrue(any("big_picture" in e for e in errors(m)))

    def test_section_without_lines_fails(self):
        m = copy.deepcopy(GOOD)
        m["sections"][0]["lines"] = "early on"
        self.assertTrue(any("lines" in e for e in errors(m)))

    def test_ragged_table_fails(self):
        m = copy.deepcopy(GOOD)
        m["flow"]["stages"][0]["table"]["rows"] = [["only one cell"]]
        self.assertTrue(any("cells" in e for e in errors(m)))

    def test_unlabeled_wrong_item_fails(self):
        m = copy.deepcopy(GOOD)
        m["wrong"][0]["label"] = "probably"
        self.assertTrue(any("label" in e for e in errors(m)))

    def test_too_many_sections_fails(self):
        m = copy.deepcopy(GOOD)
        m["sections"] = m["sections"] * 16
        self.assertTrue(any("sections, limit" in e for e in errors(m)))

    def test_unused_legend_term_fails(self):
        m = copy.deepcopy(GOOD)
        m["legend"]["fingerprint"] = "A hash of a row."
        self.assertTrue(any("never used" in e for e in errors(m)))

    def test_code_pr_section_takes_files(self):
        m = copy.deepcopy(GOOD)
        m["sections"][0] = {"name": "The endpoint", "files": ["app/X.php"], "summary": "It adds a route."}
        self.assertEqual(errors(m), [])

    def test_render_puts_hover_on_first_use_only(self):
        page = render(GOOD)
        self.assertEqual(page.count('data-tip="The job that copies rows into records."'), 2)  # big picture block and stage block
        self.assertIn("<title>Sync Link</title>", page)


if __name__ == "__main__":
    unittest.main()
