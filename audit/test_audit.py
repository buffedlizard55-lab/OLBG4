"""Offline tests: structural acceptance must not become factual verification."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('publication', Path(__file__).resolve().parents[1] / 'scripts/audit_publication.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def test_domain_boundary(self):
        self.assertTrue(audit.official_candidate('https://www.nba.com/schedule'))
        self.assertFalse(audit.official_candidate('https://nba.com.attacker.example/'))
        self.assertFalse(audit.official_candidate('https://evilnba.com/'))
        self.assertFalse(audit.official_candidate('http://www.nba.com/'))
        self.assertFalse(audit.official_candidate('https://user@nba.com/'))
        self.assertFalse(audit.official_candidate('https://www.olbg.com/'))

    def test_all_rows_unverified(self):
        rows = audit.rows()
        self.assertTrue(rows)
        self.assertEqual({r['build'] for r in rows}, {'A archive', 'B consensus', 'C model', 'D hub', 'E feed'})
        self.assertTrue(all(r['status'] == 'unverified' and r['verified_values'] == {} for r in rows))
        self.assertTrue(all(not r['official_source_candidates'] for r in rows if r['build'] == 'B consensus'))
        self.assertTrue(all(r['official_source_candidates'] for r in rows if r['build'] == 'C model'))

    def test_links_paths_and_missing_target(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'nested').mkdir()
            (root / 'nested/index.html').write_text('<a href="../index.html">home</a>')
            (root / 'space file.html').write_text('ok')
            (root / 'index.html').write_text('<a href="nested/">a</a><a href="/OLBG4/nested/">b</a>'
                '<a href="space%20file.html?q=1#section">c</a><a href="https://example.com">d</a>'
                '<a href="#section">e</a><a href="missing.html">f</a><img src="absent.png">')
            with patch.object(audit, 'ROOT', root):
                count, broken = audit.local_links()
            self.assertEqual(count, 6)
            self.assertEqual({r['url'] for r in broken}, {'missing.html', 'absent.png'})

    def test_html_escaped(self):
        report = {'build_counts': {}, 'rows': [{'build': '<script>alert(1)</script>', 'file': 'x', 'row': 1,
            'sport': '', 'match': '<img onerror=bad>', 'date': '', 'official_source_candidates': [],
            'other_sources': [], 'findings': ['<bad>']}]}
        rendered = audit.render(report)
        self.assertNotIn('<img onerror=bad>', rendered)
        self.assertIn('&lt;img onerror=bad&gt;', rendered)


if __name__ == '__main__':
    unittest.main()
