import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
FETCH_PATH = SKILL_DIR / 'scripts' / 'fetch_christies_auctions.py'
ANALYZE_PATH = SKILL_DIR / 'scripts' / 'analyze_christies_auctions.py'


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ChristiesDataPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fetch = load_module(FETCH_PATH, 'christies_fetch_mod')
        cls.analyze = load_module(ANALYZE_PATH, 'christies_analyze_mod')

    def test_extract_results_candidates_filters_by_closing_date_and_jewellery(self):
        payload = {
            'events': [
                {
                    'event_id': '31073',
                    'filter_ids': '|category_9|location_35|event_115|',
                    'landing_url': 'https://onlineonly.christies.com/sso?SaleID=31073&SaleNumber=24371',
                    'title_txt': 'Jewels Online: The Hong Kong Edit',
                    'subtitle_txt': 'Online Auction 24371 | CLOSED',
                    'date_display_txt': '23 March – 1 April',
                    'location_txt': 'Hong Kong',
                    'sale_total_value_txt': 'HKD 22,380,321',
                    'start_date': '2026-03-23T04:00:00.000Z',
                    'end_date': '2026-04-01T04:00:00.000Z',
                    'is_live': False,
                },
                {
                    'event_id': '31074',
                    'filter_ids': '|category_9|location_35|event_115|',
                    'landing_url': 'https://onlineonly.christies.com/sso?SaleID=31074&SaleNumber=24372',
                    'title_txt': 'Important Watches Online',
                    'subtitle_txt': 'Online Auction 24372 | CLOSED',
                    'date_display_txt': '23 March – 1 April',
                    'location_txt': 'Hong Kong',
                    'sale_total_value_txt': 'HKD 3,000,000',
                    'start_date': '2026-03-23T04:00:00.000Z',
                    'end_date': '2026-04-01T04:00:00.000Z',
                    'is_live': False,
                },
                {
                    'event_id': '31075',
                    'filter_ids': '|category_9|location_35|event_115|',
                    'landing_url': 'https://onlineonly.christies.com/sso?SaleID=31075&SaleNumber=24373',
                    'title_txt': 'Jewels Online: Earlier Edit',
                    'subtitle_txt': 'Online Auction 24373 | CLOSED',
                    'date_display_txt': '1 March – 10 March',
                    'location_txt': 'Hong Kong',
                    'sale_total_value_txt': 'HKD 1,000,000',
                    'start_date': '2026-03-01T04:00:00.000Z',
                    'end_date': '2026-03-10T04:00:00.000Z',
                    'is_live': False,
                },
            ]
        }
        candidates = self.fetch.extract_results_candidates(
            payload,
            category='Jewellery',
            from_date='2026-03-20',
            to_date='2026-04-29',
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['title'], 'Jewels Online: The Hong Kong Edit')
        self.assertEqual(candidates[0]['end_at'], '2026-04-01')
        self.assertEqual(candidates[0]['sale_total'], 22380321.0)
        self.assertEqual(candidates[0]['sale_total_currency'], 'HKD')

    def test_extract_lots_from_cache_prefers_structured_rows(self):
        payload = {
            'chrComponents': {
                'auctionLots': {
                    'data': {
                        'sale_total_value_txt': 'HKD 22,380,321',
                        'lots': [
                            {
                                'lot_number': '1',
                                'title_primary_txt': 'DIAMOND NECKLACE',
                                'title_secondary_txt': 'Cartier',
                                'estimate_low': '1300000.00',
                                'estimate_high': '1900000.00',
                                'estimate_txt': 'HKD 1,300,000 - 1,900,000',
                                'price_realised': '1397000.00',
                                'price_realised_txt': 'HKD 1,397,000',
                                'bid_count_txt': ' - 101 bids',
                                'url': '/s/jewels-online-hong-kong-edit/diamond-necklace-1/292884?ldp_breadcrumb=back',
                                'lot_withdrawn': False,
                                'online_only_static_lot_data': {'lot_id': 292594},
                                'online_only_dynamic_lot_data': {'item_status': 'Closed'},
                            },
                            {
                                'lot_number': '2',
                                'title_primary_txt': 'DIAMOND RING',
                                'title_secondary_txt': 'Graff',
                                'estimate_low': '300000.00',
                                'estimate_high': '500000.00',
                                'estimate_txt': 'HKD 300,000 - 500,000',
                                'price_realised': '',
                                'price_realised_txt': '',
                                'bid_count_txt': '',
                                'url': '/s/jewels-online-hong-kong-edit/diamond-ring-2/292885?ldp_breadcrumb=back',
                                'lot_withdrawn': False,
                                'online_only_static_lot_data': {'lot_id': 292595},
                                'online_only_dynamic_lot_data': {'item_status': 'Closed'},
                            },
                        ],
                    }
                }
            },
            'briDataModel': {
                'saleData': {
                    'saleId': 3910,
                    'saleNumber': '24371',
                    'saleTitle': 'Jewels Online: The Hong Kong Edit',
                    'location': 'Hong Kong',
                }
            },
        }
        lots = self.fetch.extract_lots_from_cache(payload, 'Jewellery')
        self.assertEqual(len(lots), 2)
        self.assertEqual(lots[0]['final_price'], 1397000.0)
        self.assertEqual(lots[0]['sold_state'], 'sold')
        self.assertEqual(lots[0]['url'], 'https://onlineonly.christies.com/s/jewels-online-hong-kong-edit/diamond-necklace-1/292884?ldp_breadcrumb=back')
        self.assertEqual(lots[1]['result_visibility'], 'hidden')
        self.assertEqual(lots[1]['sold_state'], 'hidden')

    def test_render_report_and_csv_contract(self):
        data = {
            'query': {'date_from': '2026-03-20', 'date_to': '2026-04-29', 'category': 'Jewellery'},
            'auctions': [
                {
                    'auction_id': '31073',
                    'title': 'Jewels Online: The Hong Kong Edit',
                    'url': 'https://onlineonly.christies.com/sso?SaleID=31073&SaleNumber=24371',
                    'category': 'Jewellery',
                    'location': 'Hong Kong',
                    'sales_type': 'Online',
                    'date_text': '23 March – 1 April',
                    'start_at': '2026-03-23',
                    'end_at': '2026-04-01',
                    'matched_by_date_range': True,
                    'sale_total': 22380321.0,
                    'sale_total_currency': 'HKD',
                }
            ],
            'lots': [
                {
                    'auction_id': '31073',
                    'lot_id': '292594',
                    'lot_number': '1',
                    'title': 'DIAMOND NECKLACE',
                    'creator': 'Cartier',
                    'estimate_low': 1300000.0,
                    'estimate_high': 1900000.0,
                    'currency': 'HKD',
                    'bid_ask': None,
                    'final_price': 1397000.0,
                    'result_visibility': 'visible',
                    'lot_state': 'Closed',
                    'sold_state': 'sold',
                    'reserve_met': None,
                    'withdrawn': False,
                    'url': 'https://onlineonly.christies.com/s/lot-1',
                    'category_match_method': 'auction_listing',
                    'number_of_bids': 101,
                },
                {
                    'auction_id': '31073',
                    'lot_id': '292595',
                    'lot_number': '2',
                    'title': 'DIAMOND RING',
                    'creator': 'Graff',
                    'estimate_low': 300000.0,
                    'estimate_high': 500000.0,
                    'currency': 'HKD',
                    'bid_ask': None,
                    'final_price': None,
                    'result_visibility': 'hidden',
                    'lot_state': 'Closed',
                    'sold_state': 'hidden',
                    'reserve_met': None,
                    'withdrawn': False,
                    'url': 'https://onlineonly.christies.com/s/lot-2',
                    'category_match_method': 'auction_listing',
                    'number_of_bids': 0,
                },
            ],
            'summary': {},
            'errors': [],
        }
        summary = self.analyze.build_summary(data)
        text = self.analyze.render_report(data, summary)
        self.assertIn('## 拍卖列表', text)
        self.assertIn('## All lots', text)
        self.assertIn('22,380,321 HKD', text)
        self.assertIn('| Lot | Creator | Title | Estimate | Realized | Variance% | Status | Link |', text)
        self.assertIn('[查看](https://onlineonly.christies.com/s/lot-1)', text)
        self.assertIn('1,397,000 HKD', text)
        self.assertLess(text.index('## 数据说明 / 异常说明'), text.index('## All lots'))
        self.assertTrue(text.rstrip().endswith('| 2 | Graff | DIAMOND RING | 300,000 - 500,000 HKD | N/A | N/A | hidden | [查看](https://onlineonly.christies.com/s/lot-2) |'))

        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / 'raw-data.json'
            report = Path(td) / 'report.md'
            raw.write_text(json.dumps(data), encoding='utf-8')
            subprocess.run(
                ['python3', str(ANALYZE_PATH), '--input', str(raw), '--output', str(report), '--write-summary'],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
            )
            csv_path = Path(td) / 'all-lots.csv'
            self.assertTrue(csv_path.exists())
            csv_text = csv_path.read_text(encoding='utf-8')
            self.assertIn(
                'auction_title,auction_date,auction_location,lot_number,creator,title,estimate_low,estimate_high,currency,final_price,variance_pct,sold_state,reserve_met,number_of_bids,category_match_method,url',
                csv_text,
            )


if __name__ == '__main__':
    unittest.main()
