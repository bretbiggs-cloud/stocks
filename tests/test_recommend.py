import copy
import unittest
from stocks.recommend import NAMES, recommend

class RecommendationTests(unittest.TestCase):
    def evidence(self):
        r={"net_modeled_pnl":10,"trade_count":12,"win_rate":.6,"max_drawdown":5,"review_locked":False,"incomplete_exit_days":[]}
        candidate={"base":{p:copy.deepcopy(r) for p in ("validation","holdout")},"stress":{p:copy.deepcopy(r) for p in ("validation","holdout")},"lower_mean_daily_pnl":.1}
        return {"phases":{p:{"start":"2020-01-01","end":"2020-03-01","sessions":40} for p in ("validation","holdout")},"limitations":"Synthetic fixture", "candidates":{k:copy.deepcopy(candidate) for k in NAMES}}
    def test_three_options_and_no_mutation(self):
        report=self.evidence();before=copy.deepcopy(report)
        result=recommend(report)
        self.assertEqual(len(result["options"]),3)
        self.assertEqual(result["decision"],"review_candidate")
        self.assertEqual(report,before)
    def test_losses_cannot_be_recommended_even_if_flag_claims_qualified(self):
        report=self.evidence()
        for c in report["candidates"].values():
            c["qualified"]=True;c["stress"]["holdout"]["net_modeled_pnl"]=-1
        self.assertEqual(recommend(report)["decision"],"none_qualified")
    def test_missing_candidate_is_not_invented(self):
        report=self.evidence();report["candidates"]={}
        result=recommend(report)
        self.assertEqual(result["decision"],"none_qualified")
        self.assertTrue(all(c["status"]=="missing_evidence" for c in result["options"]))
    def test_nonfinite_metrics_rejected(self):
        report=self.evidence();report["candidates"]["orb_baseline"]["lower_mean_daily_pnl"]=float('nan')
        with self.assertRaises(ValueError):recommend(report)
    def test_missing_exit_blocks_review(self):
        report=self.evidence()
        for c in report["candidates"].values():c["base"]["validation"]["incomplete_exit_days"]=['2020-02-01']
        self.assertEqual(recommend(report)["decision"],"none_qualified")
