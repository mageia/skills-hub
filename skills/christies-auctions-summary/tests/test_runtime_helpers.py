import importlib.util
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
RUN_PATH = SKILL_DIR / 'scripts' / 'run_christies_summary.py'


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ChristiesRuntimeHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runmod = load_module(RUN_PATH, 'christies_run_mod')

    def test_remote_cdp_does_not_require_local_profile(self):
        cfg = {
            'date_range': {'from': '2026-04-20', 'to': '2026-04-29'},
            'category': 'Jewellery',
            'cdp': {'url': 'https://cdp.example.test', 'auto_launch': False},
            'output': {'dir': './tmp-out', 'format': ['markdown', 'json', 'csv']},
        }
        norm = self.runmod.normalize_config(cfg)
        self.assertEqual(norm['cdp']['url'], 'https://cdp.example.test')
        self.assertEqual(norm['category'], 'Jewellery')

    def test_local_chrome_command_is_preserved(self):
        cfg = {
            'date_range': {'from': '2026-04-20', 'to': '2026-04-29'},
            'category': 'Jewellery',
            'cdp': {'chrome_command': 'google-chrome', 'auto_launch': True, 'user_data_dir': '~/.chrome-debug-profile'},
            'output': {'dir': './tmp-out', 'format': ['markdown', 'json', 'csv']},
        }
        norm = self.runmod.normalize_config(cfg)
        self.assertEqual(norm['cdp']['chrome_command'], 'google-chrome')

    def test_skill_md_has_no_absolute_validator_path(self):
        skill_md = (SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
        self.assertNotIn('/Users/', skill_md)
        self.assertNotIn('Google Chrome.app/Contents/MacOS/Google Chrome', skill_md)


if __name__ == '__main__':
    unittest.main()
