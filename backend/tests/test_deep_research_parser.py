import unittest

from app.core.deep_research import DeepResearchEngine


class DeepResearchParserTests(unittest.TestCase):
    def test_extracts_result_when_attributes_are_reordered(self):
        html = '''
        <a href="https://www.python.org/" class="result__a">Python</a>
        <a class="result__a" href="https://docs.python.org/3/">Documentation</a>
        '''
        self.assertEqual(
            DeepResearchEngine._extract_search_urls(html, limit=5),
            ["https://www.python.org/", "https://docs.python.org/3/"],
        )

    def test_decodes_duckduckgo_redirect(self):
        html = '''
        <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.python.org%2Fdownloads%2F&amp;rut=abc">Downloads</a>
        '''
        self.assertEqual(
            DeepResearchEngine._extract_search_urls(html, limit=5),
            ["https://www.python.org/downloads/"],
        )

    def test_deduplicates_and_respects_limit(self):
        html = '''
        <a class="result__a" href="https://example.com/one">One</a>
        <a class="result__a" href="https://example.com/one">Duplicate</a>
        <a class="result__a" href="https://example.com/two">Two</a>
        '''
        self.assertEqual(
            DeepResearchEngine._extract_search_urls(html, limit=2),
            ["https://example.com/one", "https://example.com/two"],
        )


if __name__ == "__main__":
    unittest.main()
