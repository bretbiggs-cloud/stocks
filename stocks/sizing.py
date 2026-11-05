"""Cost-aware planned risk. Local stops cannot guarantee these loss amounts."""
from decimal import Decimal as D
from stocks.strategy import number

STOP = D('.01')
COST = D('.002')
RISK = STOP + COST
TARGET = D('10')
TOTAL = D('20')


def open_risk(positions, orders):
    risk = D(0)
    for p in positions:
        risk += number(p['qty']) * number(p['avg_entry_price']) * RISK
    for o in orders:
        if o['side'] == 'buy':
            if o.get('type') != 'limit':
                raise ValueError('unbounded_pending_order')
            remaining = D(str(o['qty'])) - D(str(o['filled_qty']))
            if not remaining.is_finite() or remaining < 0:
                raise ValueError('invalid_pending_quantity')
            risk += remaining * number(o['limit_price']) * RISK
    return risk


def allocation(cash, positions, orders):
    risk_room = TOTAL - open_risk(positions, orders)
    pending = sum((max(D(0), D(str(o['qty']))-D(str(o['filled_qty']))) * number(o['limit_price'])
                   for o in orders if o['side'] == 'buy'), D(0))
    available = (number(cash) - pending - D(1)) / (1+COST)
    dollars = min(TARGET/RISK, risk_room/RISK, available)
    # Do not force undersized entries just to consume residual risk room.
    return dollars if dollars * RISK >= D('9.99') else D(0)
