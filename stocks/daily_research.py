"""Bounded premarket discovery. News activity is not verified positive sentiment."""
from datetime import datetime, timedelta
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from stocks.news import eligible_articles
from stocks.strategy import number, stamp

ET = ZoneInfo('America/New_York')
VERSION = 'daily-news-volume-v2'
RULES = {'version': VERSION, 'news_hours': 48, 'max_pages': 200, 'max_symbols': 100,
         'minimum_price': 5, 'minimum_iex_dollars': 5000000, 'minimum_relative_volume': 1.2,
         'shortlist_size': 8, 'history_sessions': 21}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def stock_asset(a):
    """Conservative broker-metadata screen; ambiguous classifications are excluded."""
    name = a.get('name', '').lower()
    return (re.fullmatch(r'[A-Z]{1,5}', a.get('symbol', '')) is not None
            and a.get('class') == 'us_equity' and a.get('exchange') in ('NASDAQ', 'NYSE')
            and a.get('status') == 'active' and a.get('tradable') is True
            and a.get('fractionable') is True
            and any(x in name for x in ('common stock', 'ordinary shares', 'american depositary'))
            and not re.search(r'\b(etf|etn|fund|trust|leveraged|inverse|preferred|warrant|units|bull|bear)\b|[2-9]x', name))


def metrics(rows, dates):
    if len(rows) != 21 or [stamp(r['t']).astimezone(ET).date().isoformat() for r in rows] != dates:
        raise ValueError('missing_or_duplicate_daily_bars')
    for r in rows:
        for k in ('o', 'h', 'l', 'c', 'v', 'vw'):
            number(r[k])
        if number(r['h']) < max(number(r['o']), number(r['c']), number(r['l'])) or number(r['l']) > min(number(r['o']), number(r['c'])):
            raise ValueError('invalid_daily_ohlc')
    prior = rows[:-1]
    liquidity = sum(number(r['v']) * number(r['vw']) for r in prior) / 20
    ratio = number(rows[-1]['v']) / (sum(number(r['v']) for r in prior) / 20)
    if number(rows[-1]['c']) < 5 or liquidity < 5000000 or ratio < D('1.2'):
        raise ValueError('price_liquidity_or_volume_filter')
    return {'relative_volume': str(ratio), 'mean_iex_dollars': str(liquidity), 'last_close': str(rows[-1]['c'])}


def select(rows):
    return sorted(rows, key=lambda r: (-D(r['relative_volume']), -D(r['mean_iex_dollars']), r['symbol']))[:8]


def validate_artifact(a, now):
    if not isinstance(a, dict) or a.get('complete') is not True or a.get('version') != VERSION:
        raise ValueError('daily_research_missing_or_incomplete')
    if a.get('rules_hash') != digest(RULES) or a.get('session') != now.astimezone(ET).date().isoformat():
        raise ValueError('daily_research_wrong_session_or_rules')
    if not stamp(a['created_at']) <= now < stamp(a['expires_at']):
        raise ValueError('daily_research_expired_or_future')
    body = {k: v for k, v in a.items() if k != 'hash'}
    if a.get('hash') != digest(body):
        raise ValueError('daily_research_hash_mismatch')
    candidates = a['candidates']
    if not isinstance(candidates, list) or len(candidates) > 8 or len({r['symbol'] for r in candidates}) != len(candidates):
        raise ValueError('invalid_shortlist')
    for r in candidates:
        if not stock_asset(r['asset']) or r['asset']['symbol'] != r['symbol']:
            raise ValueError('invalid_shortlist_asset')
        number(r['relative_volume']); number(r['mean_iex_dollars'])
    return a


def eligible_candidates(a, now):
    validate_artifact(a, now)
    return [r for r in a['candidates'] if eligible_articles(r['evidence'], r['symbol'], now, hours=48)]


def read_artifact(store, now):
    return validate_artifact(store.get('daily_research:' + now.astimezone(ET).date().isoformat()), now)


def advance(broker, store, root, now, status, host_ok):
    """At most one network request, only while closed, flat and reconciled. Resume on restart."""
    local = now.astimezone(ET)
    if (status.get('market_open') is not False or status.get('positions') != 0 or status.get('open_orders') != 0
            or status.get('uncertain_order') is not False or status.get('position_reconciliation_pending')
            or status.get('review_lock') or status.get('attention')
            or not (3 <= local.hour and (local.hour, local.minute) < (9, 15))):
        return
    session = local.date().isoformat()
    key = 'daily_research_progress:' + session
    state = store.get(key)
    if state and state['phase'] in ('done', 'failed'):
        return
    if not host_ok():
        return
    if state is None:
        state = {'session': session, 'phase': 'calendar', 'start': now.isoformat(), 'articles': [],
                 'pages': 0, 'rejected': [], 'qualified': [], 'input_hashes': []}
    try:
        phase = state['phase']
        if phase == 'calendar':
            cal = broker.request('/v2/calendar', params={'start': (local.date()-timedelta(days=60)).isoformat(), 'end': session})
            state['input_hashes'].append(digest(cal))
            if not cal or cal[-1]['date'] != session:
                state.update(phase='done', reason='not_a_trading_session')
            else:
                state['dates'] = [d['date'] for d in cal[:-1]][-21:]
                if len(state['dates']) != 21 or len(set(state['dates'])) != 21:
                    raise ValueError('calendar_history_incomplete')
                state['expires_at'] = datetime.fromisoformat(session+'T'+cal[-1]['close']).replace(tzinfo=ET).isoformat()
                state['phase'] = 'news'
        elif phase == 'news':
            params = {'start': (stamp(state['start'])-timedelta(hours=48)).isoformat(),
                      'end': state['start'], 'limit': 50, 'sort': 'desc', 'include_content': 'false'}
            if state.get('token'):
                params['page_token'] = state['token']
            page = broker.request('/v1beta1/news', data=True, params=params)
            state['input_hashes'].append(digest(page))
            if not isinstance(page.get('news'), list) or len(page['news']) > 50:
                raise ValueError('invalid_news_page')
            for row in page['news']:
                item = {k: row.get(k) for k in ('id','symbols','source','url','headline','created_at','updated_at')}
                item['first_observed_at'] = now.isoformat()
                state['articles'].append(item)
            state['pages'] += 1
            token = page.get('next_page_token')
            if token and (token == state.get('token') or state['pages'] >= 200):
                raise ValueError('news_pagination_incomplete')
            state['token'] = token
            if not token:
                state['phase'] = 'assets'
        elif phase == 'assets':
            assets = broker.request('/v2/assets', params={'status': 'active', 'asset_class': 'us_equity'})
            state['input_hashes'].append(digest(assets))
            by_symbol = {a['symbol']: a for a in assets if stock_asset(a)}
            # Newest eligible article first, stable symbol tie-break. Explicitly bounded discovery.
            indexed = {}
            for article in state['articles']:
                if isinstance(article.get('symbols'), list):
                    for symbol in article['symbols']:
                        if isinstance(symbol, str):
                            indexed.setdefault(symbol, []).append(article)
            discovered = []
            for s in sorted(indexed):
                evidence = eligible_articles(indexed[s], s, now, hours=48)
                if s in by_symbol and evidence:
                    discovered.append({'symbol': s, 'asset': by_symbol[s], 'evidence': sorted(evidence, key=lambda a: stamp(a['created_at']), reverse=True)[:5]})
                else:
                    state['rejected'].append({'symbol': s, 'reason': 'instrument_or_news_ineligible'})
            discovered.sort(key=lambda r: (max(stamp(a['created_at']) for a in r['evidence']), r['symbol']), reverse=True)
            state['candidate_count_before_cap'] = len(discovered)
            state['rejected'].extend({'symbol':r['symbol'], 'reason':'discovery_cap'} for r in discovered[100:])
            state['universe'] = discovered[:100]
            state['index'] = 0
            state['articles_hash'] = digest(state['articles'])
            state['phase'] = 'bars' if state['universe'] else 'publish'
        elif phase == 'bars':
            batch = state['universe'][state['index']:state['index']+20]
            params = {'symbols': ','.join(r['symbol'] for r in batch), 'timeframe': '1Day', 'feed': 'iex',
                      'adjustment': 'split', 'start': datetime.fromisoformat(state['dates'][0]+'T00:00:00').replace(tzinfo=ET).isoformat(),
                      'end': datetime.fromisoformat(session+'T00:00:00').replace(tzinfo=ET).isoformat(), 'limit': 10000}
            page = broker.request('/v2/stocks/bars', data=True, params=params)
            state['input_hashes'].append(digest(page))
            if page.get('next_page_token'):
                raise ValueError('daily_bars_pagination_incomplete')
            for row in batch:
                try:
                    m = metrics(page.get('bars', {}).get(row['symbol'], []), state['dates'])
                    state['qualified'].append(dict(row, **m))
                except (ValueError, KeyError, TypeError) as exc:
                    state['rejected'].append({'symbol': row['symbol'], 'reason': type(exc).__name__+':daily_data_or_filter'})
            state['index'] += len(batch)
            if state['index'] >= len(state['universe']):
                state['phase'] = 'publish'
        elif phase == 'publish':
            selected = select(state['qualified'])
            a = {'version': VERSION, 'rules_hash': digest(RULES), 'session': session, 'complete': True,
                 'created_at': now.isoformat(), 'expires_at': state['expires_at'], 'candidates': selected,
                 'input_hashes': state['input_hashes'], 'rejected': state['rejected'],
                 'screened_count': len(state['universe']), 'candidate_count_before_cap': state['candidate_count_before_cap'],
                 'news_pages': state['pages'], 'qualified': state['qualified'], 'articles_hash': state['articles_hash'], 'selection_note': 'Experimental IEX/news-activity ranking; no sentiment or verified bullish catalyst. Historical validation incomplete.'}
            a['hash'] = digest(a)
            validate_artifact(a, now)
            store.put('daily_research:'+session, a)
            reports = Path(root)/'reports'; reports.mkdir(parents=True, exist_ok=True)
            tmp = reports/('research-'+session+'.json.tmp')
            tmp.write_text(json.dumps(a, indent=2), encoding='utf-8');tmp.replace(reports/('research-'+session+'.json'))
            store.event(now, 'daily_research_complete', {'session':session, 'hash':a['hash'], 'symbols':[r['symbol'] for r in selected]})
            state['phase'] = 'done'
        store.put(key, state)
    except Exception as exc:
        state.update(phase='failed', error_type=type(exc).__name__)
        store.put(key, state)
        store.event(now, 'daily_research_failed', {'session':session, 'error_type':type(exc).__name__})
