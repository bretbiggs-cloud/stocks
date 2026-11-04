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

    def test_tampered_history_is_rejected_before_replay(self):
        import tempfile
        from pathlib import Path
        from stocks.history_check import prepared
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"2020-01-02.json").write_text("{}")
            manifest={"calendar":[{"date":"2020-01-02"}],"sha256":{"2020-01-02.json":"invalid"}}
            with self.assertRaisesRegex(ValueError,"hash mismatch"):
                list(prepared(manifest,root,["2020-01-02"]))

    def test_incomplete_cache_cannot_produce_evaluation(self):
        import tempfile,json,sys
        from pathlib import Path
        from unittest.mock import patch
        from stocks.history_check import main
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"manifest.json").write_text(json.dumps({"calendar":[{"date":"2020-01-02"}],"sha256":{}}))
            with patch.object(sys,"argv",["history_check","--root",tmp,"--evaluate","orb_baseline"]):
                with self.assertRaises(SystemExit) as error:main()
            self.assertEqual(error.exception.code,2)
            self.assertEqual(len(list(root.glob("orb_baseline*.json"))),0)
