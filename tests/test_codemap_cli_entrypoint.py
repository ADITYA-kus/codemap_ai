import unittest

import codemap_cli


class TestCodeMapCliEntrypoint(unittest.TestCase):
    def test_console_entrypoint_uses_project_specific_module(self):
        self.assertEqual(codemap_cli._main.__module__, "codemap_app")


if __name__ == "__main__":
    unittest.main()
