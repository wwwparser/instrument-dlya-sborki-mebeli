"""Сборка сайта: items.py + items_econom.py + цены Петровича → docs/.

    python build.py            # цены из базы парсера (../idea-parser-petrovich/data/petrovich.sqlite3)
    python build.py --offline  # цены из prices.json

Страницы: docs/index.html — основной список, docs/econom.html — эконом-вариант.
"""
import argparse
import io
import json
import sqlite3
import sys
from pathlib import Path

import items
import items_econom

ROOT = Path(__file__).resolve().parent
DB = ROOT.parent / 'idea-parser-petrovich' / 'data' / 'petrovich.sqlite3'
PRICES = ROOT / 'prices.json'

PAGES = [
    dict(key='main', file='index.html', mod=items, title='Инструмент для сборки кухонь и корпусной мебели',
         lead='Список инструмента опытного сборщика из видеообзора: пылесос, пила, шуруповёрты, перфоратор, '
              'ручной инструмент и расходники. Каждая позиция подобрана в каталоге Петровича, со ссылкой и ценой. '
              'Если точной модели из видео в магазине нет, взят ближайший аналог и указано, чем он отличается.'),
    dict(key='econom', file='econom.html', mod=items_econom, title='Эконом-вариант: тот же набор недорогими марками',
         lead='Тот же список из видео, но собранный на недорогих марках Петровича — КМ, КМ АТОМ, P.I.T., Зубр, '
              'Hesler, Sparta. Аккумуляторный инструмент на одной платформе КМ АТОМ 18 В, степлер электрический, '
              'как в видео, характеристики держатся на уровне оригинала: диск 165 мм, перфоратор 2,6 Дж, '
              'зелёный лазер со штативом.'),
]


def load_prices(codes, offline):
    if offline:
        snap = json.loads(PRICES.read_text(encoding='utf8'))
        products = {int(k): v for k, v in snap['products'].items()}
        missing = set(codes) - set(products)
        if missing:
            raise SystemExit(f'Нет в снимке цен: {sorted(missing)} — пересоберите без --offline')
        return products, snap['date']
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


def page_data(mod, products, date):
    groups = []
    for key, title, note in mod.GROUPS:
        rows = []
        for code, qty, video, match, comment in mod.ITEMS[key]:
            p = products[code]
            rows.append(dict(code=code, qty=qty, video=video, match=match, comment=comment, title=p['title'],
                             unit=p['unit'], price=p['price'], sum=round(p['price'] * qty, 2), url=p['url']))
        groups.append(dict(key=key, title=title, note=note, rows=rows, total=round(sum(r['sum'] for r in rows), 2)))
    return dict(date=date, groups=groups, missing=mod.MISSING,
                total=round(sum(g['total'] for g in groups), 2),
                count=sum(len(g['rows']) for g in groups),
                analogs=sum(r['match'] == 'analog' for g in groups for r in g['rows']))


def build(offline=False):
    codes = []
    for page in PAGES:
        page_codes = [code for rows in page['mod'].ITEMS.values() for code, *_ in rows]
        dup = {c for c in page_codes if page_codes.count(c) > 1}
        if dup:
            raise SystemExit(f"Повторяются коды на странице {page['file']}: {dup}")
        codes += page_codes
    products, date = load_prices(sorted(set(codes)), offline)

    html = (ROOT / 'template.html').read_text(encoding='utf8')
    built = {}
    for page in PAGES:
        built[page['key']] = page_data(page['mod'], products, date)
    for page in PAGES:
        data = dict(built[page['key']], variant=page['key'], h1=page['title'], lead=page['lead'],
                    other=round(built['econom' if page['key'] == 'main' else 'main']['total'], 2))
        payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
        (ROOT / 'docs' / page['file']).write_text(html.replace('/*DATA*/', payload), encoding='utf8')
    (ROOT / 'docs' / '.nojekyll').touch()
    return built


if __name__ == '__main__':
    if hasattr(sys.stdout, 'buffer'):  # ₽ не влезает в cp1251-консоль Windows
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true')
    built = build(ap.parse_args().offline)
    for page in PAGES:
        d = built[page['key']]
        print(f"\n=== {page['file']} ===")
        for g in d['groups']:
            print(f"{g['title']:<45} {len(g['rows']):>3} поз. {g['total']:>12,.0f} ₽")
        print(f"ИТОГО {d['count']} позиций, аналогов {d['analogs']}: {d['total']:,.0f} ₽ (цены на {d['date']})")
    diff = built['main']['total'] - built['econom']['total']
    print(f"\nЭконом дешевле основного на {diff:,.0f} ₽ "
          f"({diff / built['main']['total'] * 100:.0f} %)")
