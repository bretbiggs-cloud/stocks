import unittest
from datetime import date, timedelta
from stocks.history_check import plan

class HistoryTests(unittest.TestCase):
    def test_chronological_disjoint_phases_and_warmup(self):
        days=[{"date":(date(2020,1,1)+timedelta(days=i)).isoformat()} for i in range(200)]
        result=plan(days[0]["date"],days[-1]["date"],days)
        parts=list(result["phases"].values())
        self.assertEqual(sum(map(len,parts)),186)
        self.assertLess(parts[0][-1],parts[1][0])
        self.assertLess(parts[1][-1],parts[2][0])
        self.assertEqual(parts[0][0],days[14]["date"])
        with self.assertRaises(ValueError):plan("2020-01-01","2020-01-05",days)
