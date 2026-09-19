"""Сборка сайта: items.py + цены Петровича → docs/index.html.

    python build.py            # цены из базы парсера (../idea-parser-petrovich/data/petrovich.sqlite3)
    python build.py --offline  # цены из prices.json
"""
import argparse
import json
import sqlite3
from pathlib import Path

from items import GROUPS, ITEMS, MISSING

ROOT = Path(__file__).resolve().parent
DB = ROOT.parent / 'idea-parser-petrovich' / 'data' / 'petrovich.sqlite3'
PRICES = ROOT / 'prices.json'


def load_prices(codes, offline):
    if offline:
        snap = json.loads(PRICES.read_text(encoding='utf8'))
        return {int(k): v for k, v in snap['products'].items()}, snap['date']
    con = sqlite3.connect(DB)
    q = ','.join('?' * len(codes))
    out = {code: dict(title=t, unit=u, price=p, price_gold=g, url=url, updated=upd)
           for code, t, u, p, g, url, upd in con.execute(
               f'select code,title,unit,price_retail,price_gold,url,updated_at from products where code in ({q})', list(codes))}
    missing = set(codes) - set(out)
    if missing:
        raise SystemExit(f'Нет в базе Петровича: {sorted(missing)}')
    date = max(p['updated'] for p in out.values())[:10]
    PRICES.write_text(json.dumps({'date': date, 'products': out}, ensure_ascii=False, indent=1), encoding='utf8')
    return out, date


def build(offline=False):
    codes = [code for rows in ITEMS.values() for code, *_ in rows]
    dup = {c for c in codes if codes.count(c) > 1}
    if dup:
        raise SystemExit(f'Повторяются коды: {dup}')
    products, date = load_prices(codes, offline)
    groups = []
    for key, title, note in GROUPS:
        rows = []
        for code, qty, video, match, comment in ITEMS[key]:
            p = products[code]
            rows.append(dict(code=code, qty=qty, video=video, match=match, comment=comment, title=p['title'],
                             unit=p['unit'], price=p['price'], sum=round(p['price'] * qty, 2), url=p['url']))
        groups.append(dict(key=key, title=title, note=note, rows=rows, total=round(sum(r['sum'] for r in rows), 2)))
    data = dict(date=date, groups=groups, missing=MISSING,
                total=round(sum(g['total'] for g in groups), 2),
                count=sum(len(g['rows']) for g in groups),
                analogs=sum(r['match'] == 'analog' for g in groups for r in g['rows']))
    html = (ROOT / 'template.html').read_text(encoding='utf8')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    (ROOT / 'docs' / 'index.html').write_text(html.replace('/*DATA*/', payload), encoding='utf8')
    (ROOT / 'docs' / '.nojekyll').touch()
    return data


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true')
    d = build(ap.parse_args().offline)
    for g in d['groups']:
        print(f"{g['title']:<45} {len(g['rows']):>3} поз. {g['total']:>12,.0f} ₽")
    print(f"ИТОГО {d['count']} позиций, аналогов {d['analogs']}: {d['total']:,.0f} ₽ (цены на {d['date']})")
