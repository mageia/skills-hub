import importlib.util
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
LOGIN_PATH = SKILL_DIR / 'scripts' / 'verify_christies_login.py'


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ChristiesLoginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loginmod = load_module(LOGIN_PATH, 'christies_login_mod')

    def test_login_classifier_requires_positive_signal(self):
        classify = self.loginmod.classify_login_state
        self.assertTrue(classify('link "LOG OUT"', 'LOG OUT MY ACCOUNT')[0])
        self.assertFalse(classify('button "SIGN IN"', 'SIGN IN')[0])
        self.assertFalse(classify('', '')[0])

    def test_conflicting_markers_fail_closed(self):
        ok, reason = self.loginmod.classify_login_state('link "LOG OUT"', 'SIGN IN MY ACCOUNT')
        self.assertFalse(ok)
        self.assertIn('conflicting', reason)


if __name__ == '__main__':
    unittest.main()
