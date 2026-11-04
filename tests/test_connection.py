import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from stocks.verify_connection import NoRedirect, verify


class ConnectionTests(unittest.TestCase):
    def test_only_reads_expected_paper_account(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'credentials.json'
            path.write_text(json.dumps(dict(key_id='test', secret_key='fake',
                                           expected_account_number='paper-test')))
            response = dict(account_number='paper-test', status='ACTIVE', currency='USD',
                            trading_blocked=False, account_blocked=False,
                            trade_suspended_by_user=False, cash='2000', equity='2000')
            opener = MagicMock()
            opener.open.return_value.__enter__.return_value = io.StringIO(json.dumps(response))
            with patch('urllib.request.build_opener', return_value=opener):
                result = verify(path)
            request = opener.open.call_args.args[0]
            self.assertEqual(request.full_url, 'https://paper-api.alpaca.markets/v2/account')
            self.assertEqual(request.get_method(), 'GET')
            self.assertTrue(result['paper_api_verified'])
            response['account_number'] = 'wrong-account'
            opener.open.return_value.__enter__.return_value = io.StringIO(json.dumps(response))
            with patch('urllib.request.build_opener', return_value=opener):
                with self.assertRaises(ValueError):
                    verify(path)

    def test_credentials_never_follow_redirects(self):
        with self.assertRaises(ValueError):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com')
