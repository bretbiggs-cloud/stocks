import copy
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from stocks.daily_research import (ET, RULES, VERSION, advance, digest, eligible_candidates,
                                  metrics, read_artifact, select, stock_asset, validate_artifact)
from stocks.engine import Engine
from stocks.news import eligible_articles
from stocks.sizing import allocation, open_risk
from stocks.store import Store
from stocks.risk import Buy, Snapshot, validate_buy, Blocked, PAPER_ENDPOINT

NOW = datetime(2026, 11, 5, 8, tzinfo=timezone.utc)
ASSET = dict(symbol='QCOM', name='QUALCOMM Incorporated Common Stock', exchange='NASDAQ',
             status='active', tradable=True, fractionable=True, **{'class':'us_equity'})


def article(now=NOW):
    return dict(id=1, symbols=['QCOM'], source='provider', url='https://example.invalid/news',
                headline='Quarterly earnings report', created_at=(now-timedelta(hours=12)).isoformat(),
                updated_at=(now-timedelta(hours=12)).isoformat(), first_observed_at=now.isoformat())


def artifact(now=NOW):
    a = dict(version=VERSION, rules_hash=digest(RULES), session=now.astimezone(ET).date().isoformat(),
             complete=True, created_at=now.isoformat(), expires_at=(now+timedelta(hours=13)).isoformat(),
             candidates=[dict(symbol='QCOM', asset=ASSET, evidence=[article(now)], relative_volume='2', mean_iex_dollars='9000000')])
    a['hash'] = digest(a)
    return a


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root/'ledger.sqlite')
        self.status = dict(market_open=False, positions=0, open_orders=0, uncertain_order=False,
                           review_lock=False, position_reconciliation_pending=[], attention=None)
        self.dates = [(NOW.date()-timedelta(days=i)).isoformat() for i in range(21,0,-1)]
        self.bars = [dict(t=d+'T04:00:00Z' if d<'2026-11-01' else d+'T05:00:00Z',
                          o=100,h=101,l=99,c=100,v=100000 if i<20 else 200000,vw=100)
                     for i,d in enumerate(self.dates)]
        outer = self
        class Fake:
            def __init__(self):self.calls=[]
            def request(self,path,**kwargs):
                self.calls.append((path,kwargs))
                if path=='/v2/calendar':return [dict(date=d,open='09:30',close='16:00') for d in outer.dates+[NOW.date().isoformat()]]
                if path=='/v1beta1/news':return {'news':[article()]}
                if path=='/v2/assets':return [ASSET,dict(ASSET,symbol='BAD',name='Leveraged Fund Common Stock')]
                if path=='/v2/stocks/bars':return {'bars':{'QCOM':outer.bars}}
                raise AssertionError(path)
        self.broker=Fake()

    def tearDown(self):
        self.store.close();self.tmp.cleanup()

    def step(self,status=None,now=NOW,host=True):
        before=len(self.broker.calls)
        advance(self.broker,self.store,self.root,now,status or self.status,lambda:host)
        self.assertLessEqual(len(self.broker.calls)-before,1)

    def test_discover_new_symbol_restart_and_daily_expiry(self):
        self.step();self.step()
        self.store.close();self.store=Store(self.root/'ledger.sqlite')
        for _ in range(4):self.step()
        a=read_artifact(self.store,NOW)
        self.assertEqual([r['symbol'] for r in a['candidates']],['QCOM'])
        self.assertEqual(a['candidates'][0]['relative_volume'],'2')
        self.assertTrue((self.root/'reports/research-2026-11-05.json').exists())
        calls=len(self.broker.calls);self.step();self.assertEqual(len(self.broker.calls),calls)
        with self.assertRaises(ValueError):read_artifact(self.store,NOW+timedelta(days=1))

    def test_never_scan_during_positions_orders_open_market_or_busy_host(self):
        for change in [dict(positions=1),dict(open_orders=1),dict(market_open=True),dict(uncertain_order=True),dict(review_lock=True),dict(position_reconciliation_pending=['QCOM'])]:
            self.step(dict(self.status,**change))
        self.step(host=False);self.step(now=NOW+timedelta(hours=7))
        self.assertEqual(self.broker.calls,[])

    def test_pagination_failure_never_publishes_partial_candidates(self):
        self.step()
        def endless(path,**kwargs):
            self.broker.calls.append((path,kwargs));return {'news':[article()],'next_page_token':'same'}
        self.broker.request=endless
        self.step();self.step()
        state=self.store.get('daily_research_progress:2026-11-05')
        self.assertEqual(state['phase'],'failed')
        with self.assertRaises(ValueError):read_artifact(self.store,NOW)

    def test_api_failure_is_persistent_and_safe(self):
        self.broker.request=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('private response'))
        self.step()
        state=self.store.get('daily_research_progress:2026-11-05')
        self.assertEqual(state['error_type'],'RuntimeError')
        self.assertNotIn('private response',json.dumps(state))

    def test_missing_bars_yield_empty_list_without_test_list_fallback(self):
        self.bars.pop()
        for _ in range(6):self.step()
        self.assertEqual(read_artifact(self.store,NOW)['candidates'],[])

    def test_asset_screen_rejects_ambiguous_and_leveraged_instruments(self):
        self.assertTrue(stock_asset(ASSET))
        for update in [dict(name='Technology ETF'),dict(name='Bull 3x Common Stock'),dict(exchange='OTC'),dict(fractionable=False),dict(name='Unknown Company'),dict(symbol='../QCOM')]:
            self.assertFalse(stock_asset(dict(ASSET,**update)))

    def test_future_duplicate_and_invalid_bars_rejected(self):
        for rows in [self.bars[:-1],self.bars+[self.bars[-1]],self.bars[:-1]+[dict(self.bars[-1],v='NaN')],self.bars[:-1]+[dict(self.bars[-1],t='2099-01-01T05:00:00Z')]]:
            with self.assertRaises(ValueError):metrics(rows,self.dates)

    def test_artifact_corruption_wrong_rules_future_and_stale_rejected(self):
        a=artifact();self.assertEqual(len(eligible_candidates(a,NOW)),1)
        for update in [dict(session='2026-11-04'),dict(rules_hash='wrong'),dict(complete=False),dict(created_at=(NOW+timedelta(seconds=1)).isoformat()),dict(expires_at=NOW.isoformat())]:
            bad=dict(a,**update);bad['hash']=digest({k:v for k,v in bad.items() if k!='hash'})
            with self.assertRaises(ValueError):validate_artifact(bad,NOW)
        bad=copy.deepcopy(a);bad['candidates'][0]['symbol']='MSFT'
        with self.assertRaises(ValueError):validate_artifact(bad,NOW)

    def test_48_hours_does_not_allow_future_or_expired_news(self):
        row=article();self.assertEqual(eligible_articles([row],'QCOM',NOW),[])
        self.assertEqual(len(eligible_articles([row],'QCOM',NOW,hours=48)),1)
        for field,val in [('created_at',NOW-timedelta(hours=49)),('updated_at',NOW+timedelta(seconds=1)),('first_observed_at',NOW+timedelta(seconds=1))]:
            self.assertEqual(eligible_articles([dict(row,**{field:val.isoformat()})],'QCOM',NOW,hours=48),[])

    def test_ranking_deterministic_and_capped(self):
        rows=[dict(symbol=str(i),relative_volume='2',mean_iex_dollars='100') for i in range(10)]
        self.assertEqual(select(rows),select(list(reversed(rows))))
        self.assertEqual(len(select(rows)),8)


class SizingTests(unittest.TestCase):
    def test_sizes_from_stop_and_cost_instead_of_400(self):
        dollars=allocation('2000',[],[])
        self.assertGreater(dollars,400)
        self.assertEqual(dollars*D('.012'),D(10))

    def test_filled_and_pending_risk_reserved_without_double_counting(self):
        positions=[dict(qty='5',avg_entry_price='100')]
        orders=[dict(side='buy',type='limit',qty='10',filled_qty='5',limit_price='100')]
        self.assertEqual(open_risk(positions,orders),D(12))
        self.assertEqual(allocation('1500',positions,orders),0)
        with self.assertRaises(ValueError):open_risk([], [dict(orders[0],type='market')])

    def test_pure_validation_blocks_aggregate_risk_and_respects_cash(self):
        state=Snapshot(PAPER_ENDPOINT,'test',NOW,D(2000),D(2000),D(2000),D(2000),{}, {},True,True,True,False,False,False)
        order=Buy('QCOM',D(8),D(100),NOW,D('.001'))
        self.assertEqual(validate_buy(order,state,expected_account='test',allowed_symbols=frozenset({'QCOM'}),now=NOW,planned_open_risk=D(10)),800)
        with self.assertRaises(Blocked):validate_buy(order,state,expected_account='test',allowed_symbols=frozenset({'QCOM'}),now=NOW,planned_open_risk=D(11))

    def test_direct_submission_cannot_bypass_daily_research_and_risk(self):
        with tempfile.TemporaryDirectory() as t:
            store=Store(Path(t)/'ledger.sqlite')
            try:
                now=datetime.now(timezone.utc);a=artifact(now);store.put('daily_research:'+a['session'],a)
                engine=Engine(None,store,t,enabled=True,strategy_enabled=True,strategy_date=a['session'],daily_research=True)
                with self.assertRaises(ValueError):engine.submit(now,'test',dict(symbol='QCOM',side='buy',qty='1',type='limit',limit_price='100'))
                self.assertEqual(store.order_rows(),[])
            finally:store.close()

class DailyEngineTests(unittest.TestCase):
    def setUp(self):
        from test_engine import TickBroker
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'ledger.sqlite')
        self.now=datetime(2026,11,5,16,tzinfo=timezone.utc)
        fixed=self.now
        class FixedDatetime(datetime):
            @classmethod
            def now(cls,tz=None):return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)
        self.patch=patch('stocks.engine.datetime',FixedDatetime);self.patch.start()
        self.broker=TickBroker(self.now)
        self.broker.request=lambda *a,**k:[dict(date='2026-11-05',open='09:30',close='16:00')]
        self.broker.asset=lambda s:dict(ASSET,symbol=s)
        self.broker.quote=lambda s:dict(bp=99.99,ap=100,t=self.now.isoformat())
        self.broker.news=lambda *a:[article(self.now)]
        self.broker.bars=lambda symbols,*args:{s:[] for s in symbols}
        self.store.put('initialized',True);self.store.put('canary','passed');self.store.put('peak_close','2000')
        self.engine=Engine(self.broker,self.store,self.root,enabled=True,strategy_enabled=True,
                           strategy_date='2026-11-05',daily_research=True,host_ok=lambda:True)
        a=artifact(self.now);self.store.put('daily_research:2026-11-05',a)

    def tearDown(self):
        self.patch.stop();self.store.close();self.tmp.cleanup()

    def test_outside_test_list_can_submit_only_after_full_validation(self):
        with patch('stocks.engine.signal',return_value={'buy':True,'reason':'test','volume_ratio':'2'}):
            result=self.engine.tick()
        self.assertEqual(result['mode'],'daily_strategy_evaluated')
        self.assertEqual(len(self.broker.submissions),1)
        row=self.broker.submissions[0];self.assertEqual(row['symbol'],'QCOM')
        dollars=D(row['qty'])*D(row['limit_price'])
        self.assertGreater(dollars,800);self.assertLessEqual(dollars*D('.012'),10)
        # Restart cannot duplicate the ambiguous/pending entry.
        self.engine._entry_validation=None
        for order in self.broker.lookup.values():order['created_at']=self.now.isoformat()
        self.engine.tick();self.assertEqual(len(self.broker.submissions),1)

    def test_missing_artifact_blocks_new_entries_but_holding_outside_list_exits(self):
        self.store.put('daily_research:2026-11-05',None)
        self.assertEqual(self.engine.tick()['mode'],'daily_research_unavailable')
        cid=self.store.reserve('old',{'symbol':'AAPL','side':'buy'})
        self.store.record_order('old',dict(client_order_id=cid,symbol='AAPL',side='buy',status='filled',filled_qty='1',filled_avg_price='110'))
        self.broker.current_positions=[dict(symbol='AAPL',qty='1',qty_available='1',avg_entry_price='110',market_value='100')]
        self.engine.tick()
        self.assertEqual(self.broker.submissions[0]['side'],'sell')
        self.assertEqual(self.broker.submissions[0]['symbol'],'AAPL')

    def test_modeled_cost_triggers_daily_loss_lock(self):
        self.store.put('day','2026-11-05');self.store.put('day_start','2000');self.store.put('day_cost_start','0')
        self.broker.balance='1960.50'
        # Closed round trip: $1 of modeled costs with zero remaining position.
        for side in ('buy','sell'):
            cid=self.store.reserve(side,dict(symbol='QCOM',side=side))
            self.store.record_order(side,dict(client_order_id=cid,symbol='QCOM',side=side,status='filled',filled_qty='5',filled_avg_price='100'))
        self.engine.tick();self.assertTrue(self.store.get('daily_lock'))
        self.assertEqual(self.broker.submissions,[])

    def test_old_strategy_attempts_count_against_daily_cap(self):
        for i in range(4):
            key=f'news-volume-v1:2026-11-05:TEST{i}'
            cid=self.store.reserve(key,dict(symbol=f'TEST{i}',side='buy'))
            self.store.record_order(key,dict(client_order_id=cid,symbol=f'TEST{i}',side='buy',status='rejected',filled_qty='0',filled_avg_price=None))
        self.assertEqual(self.engine.tick()['mode'],'daily_entry_limit')
        self.assertEqual(self.broker.submissions,[])
