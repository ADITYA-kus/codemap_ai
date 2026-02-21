import unittest

from security_utils import redact_secrets


class TestSecurityRedaction(unittest.TestCase):
    def test_redacts_github_token(self):
        raw = "token=ghp_abcdefghijklmnopqrstuvwxyz123456"
        masked = redact_secrets(raw)
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz123456", masked)
        self.assertTrue("ghp_************" in masked or "token=[REDACTED]" in masked)

    def test_redacts_bearer(self):
        raw = "Authorization: Bearer abc.def.ghi"
        masked = redact_secrets(raw)
        self.assertNotIn("abc.def.ghi", masked)
        self.assertIn("Bearer ********", masked)

    def test_redacts_basic(self):
        raw = "Authorization: Basic Zm9vOmJhcg=="
        masked = redact_secrets(raw)
        self.assertNotIn("Zm9vOmJhcg==", masked)
        self.assertIn("Basic ********", masked)

    def test_redacts_embedded_url_credentials(self):
        raw = "https://user:secretpass@github.com/org/repo.git"
        masked = redact_secrets(raw)
        self.assertNotIn("secretpass", masked)
        self.assertIn("https://***:***@github.com/org/repo.git", masked)


if __name__ == "__main__":
    unittest.main()
