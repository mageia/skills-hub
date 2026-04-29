import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
FETCH_PATH = SKILL_DIR / 'scripts' / 'fetch_sothebys_auctions.py'
RUN_PATH = SKILL_DIR / 'scripts' / 'run_sothebys_summary.py'
ANALYZE_PATH = SKILL_DIR / 'scripts' / 'analyze_sothebys_auctions.py'
LOGIN_PATH = SKILL_DIR / 'scripts' / 'verify_sothebys_login.py'


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SkillRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fetch = load_module(FETCH_PATH, 'fetch_mod')
        cls.runmod = load_module(RUN_PATH, 'run_mod')
        cls.analyze = load_module(ANALYZE_PATH, 'analyze_mod')
        cls.loginmod = load_module(LOGIN_PATH, 'login_mod')

    def test_remote_cdp_does_not_require_local_profile(self):
        cfg = {
            'date_range': {'from': '2026-04-20', 'to': '2026-04-29'},
            'category': 'Jewelry',
            'cdp': {'url': 'https://cdp.example.test', 'auto_launch': False},
            'output': {'dir': './tmp-out', 'format': ['markdown', 'json']},
        }
        norm = self.runmod.normalize_config(cfg)
        self.assertEqual(norm['cdp']['url'], 'https://cdp.example.test')
        self.assertEqual(norm['category'], 'Jewelry')

    def test_local_chrome_command_is_preserved(self):
        cfg = {
            'date_range': {'from': '2026-04-20', 'to': '2026-04-29'},
            'category': 'Jewelry',
            'cdp': {'chrome_command': 'google-chrome', 'auto_launch': True, 'user_data_dir': '~/.chrome-debug-profile'},
            'output': {'dir': './tmp-out', 'format': ['markdown', 'json']},
        }
        norm = self.runmod.normalize_config(cfg)
        self.assertEqual(norm['cdp']['chrome_command'], 'google-chrome')

    def test_extract_lots_from_apollo_cache(self):
        apollo = {
            'LotCard:1': {
                '__typename': 'LotCard',
                'lotId': 'lot-1',
                'title': 'Lot One',
                'creatorsDisplayTitle': 'Cartier',
                'slug': {'lotSlug': 'lot-one'},
                'lotNumber': {'lotDisplayNumber': '1601'},
                'auction': {'currency': 'HKD', 'auctionId': 'a1', 'slug': {'name': 'high-jewelry-6', 'year': '2026'}},
                'estimateV2': {'lowEstimate': {'amount': '100'}, 'highEstimate': {'amount': '200'}},
                'withdrawnState': {'state': 'NotAffected'},
                'bidState': {'__ref': 'BidState:1'},
            },
            'BidState:1': {
                '__typename': 'BidState',
                'reserveMet': True,
                'numberOfBids': 2,
                'sold': {'__typename': 'ResultVisible', 'isSold': True, 'premiums': {'finalPriceV2': {'amount': '240', 'currency': 'HKD'}}},
                'currentBidV2': {'amount': '190', 'currency': 'HKD'},
            },
            'LotCard:2': {
                '__typename': 'LotCard',
                'lotId': 'lot-2',
                'title': 'Lot Two',
                'creatorsDisplayTitle': 'Unknown',
                'slug': {'lotSlug': 'lot-two'},
                'lotNumber': {'lotDisplayNumber': '1602'},
                'auction': {'currency': 'HKD', 'auctionId': 'a1', 'slug': {'name': 'high-jewelry-6', 'year': '2026'}},
                'estimateV2': {'lowEstimate': {'amount': '300'}, 'highEstimate': {'amount': '500'}},
                'withdrawnState': {'state': 'NotAffected'},
                'bidState': {'__ref': 'BidState:2'},
            },
            'BidState:2': {
                '__typename': 'BidState',
                'reserveMet': False,
                'numberOfBids': 0,
                'sold': {'__typename': 'ResultHidden'},
                'currentBidV2': None,
            },
        }
        lots = self.fetch.extract_lots_from_apollo(apollo, 'Jewelry')
        self.assertEqual(len(lots), 2)
        self.assertEqual(lots[0]['final_price'], 240.0)
        self.assertEqual(lots[0]['sold_state'], 'sold')
        self.assertEqual(lots[0]['url'], 'https://www.sothebys.com/en/buy/auction/2026/high-jewelry-6/lot-one')
        self.assertEqual(lots[1]['result_visibility'], 'hidden')

    def test_report_contains_all_lots_table(self):
        data = {
            'query': {'date_from': '2026-04-20', 'date_to': '2026-04-29', 'category': 'Jewelry'},
            'auctions': [{'auction_id': 'a1', 'title': 'High Jewelry', 'location': 'Hong Kong', 'sales_type': 'Live'}],
            'lots': [
                {'auction_id': 'a1', 'lot_id': 'lot-1', 'lot_number': '1601', 'title': 'Lot One', 'creator': 'Cartier', 'estimate_low': 100, 'estimate_high': 200, 'currency': 'HKD', 'final_price': 240, 'result_visibility': 'visible', 'sold_state': 'sold', 'withdrawn': False, 'url': 'https://example/1'},
                {'auction_id': 'a1', 'lot_id': 'lot-2', 'lot_number': '1602', 'title': 'Lot Two', 'creator': 'Graff', 'estimate_low': 300, 'estimate_high': 500, 'currency': 'HKD', 'final_price': None, 'result_visibility': 'hidden', 'sold_state': 'hidden', 'withdrawn': False, 'url': 'https://example/2'},
            ],
            'summary': {},
            'errors': [],
        }
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / 'raw.json'
            report = Path(td) / 'report.md'
            raw.write_text(json.dumps(data), encoding='utf-8')
            self.analyze.main = self.analyze.main  # keep import referenced
            summary = self.analyze.build_summary(data)
            text = self.analyze.render_report(data, summary)
            self.assertIn('## All lots', text)
            self.assertIn('| Lot | Creator | Low | High | Realized | Currency | Status | Link | Title |', text)
            self.assertIn('[原始链接](https://example/1)', text)
            self.assertIn('240', text)


    def test_login_classifier_requires_positive_logged_in_signal(self):
        classify = self.loginmod.classify_login_state
        self.assertTrue(classify('link "LOG OUT"', 'LOG OUT MY ACCOUNT')[0])
        self.assertFalse(classify('link "LOG IN"', 'LOG IN PREFERRED ACCESS')[0])
        self.assertFalse(classify('', 'PREFERRED ACCESS')[0])
        self.assertFalse(classify('', '')[0])

    def test_skill_md_has_no_absolute_validator_path(self):
        skill_md = (SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
        self.assertNotIn('/Users/', skill_md)
        self.assertNotIn('Google Chrome.app/Contents/MacOS/Google Chrome', skill_md)


if __name__ == '__main__':
    unittest.main()
