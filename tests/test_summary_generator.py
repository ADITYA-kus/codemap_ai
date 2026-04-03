import unittest

from analysis.explain.summary_generator import _first_line


class TestSummaryGenerator(unittest.TestCase):
    def test_first_line_returns_none_for_whitespace_only_docstring(self):
        self.assertIsNone(_first_line("   \n\t  "))


if __name__ == "__main__":
    unittest.main()
