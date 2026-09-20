"""Сборка сайта: списки позиций + цены Петровича → docs/.

    python build.py            # цены из базы парсера (../idea-parser-petrovich/data/petrovich.sqlite3)
    python build.py --offline  # цены из prices.json

Четыре страницы, по два варианта на каждый видеообзор: index.html и econom.html —
первый сборщик, master2.html и master2-econom.html — второй.
"""
import argparse
import io
import json
import sqlite3
import sys
from pathlib import Path

import items
import items_econom
import items_master2
import items_master2_econom

ROOT = Path(__file__).resolve().parent
DB = ROOT.parent / 'idea-parser-petrovich' / 'data' / 'petrovich.sqlite3'
PRICES = ROOT / 'prices.json'

PAGES = [
    dict(key='main', file='index.html', mod=items, kind='main', pair='econom',
         label='Обзор 1 · основной', tab='Обзор 1',
         missing_note='Мебельной фурнитуры и шаблонов в Петровиче нет. Их покупают в магазинах мебельной фурнитуры, в сумму они не входят.',
         title='Инструмент для сборки кухонь и корпусной мебели',
         lead='Список инструмента опытного сборщика из видеообзора: пылесос, пила, шуруповёрты, перфоратор, '
              'ручной инструмент и расходники. Каждая позиция подобрана в каталоге Петровича, со ссылкой и ценой. '
              'Если точной модели из видео в магазине нет, взят ближайший аналог и указано, чем он отличается.'),
    dict(key='econom', file='econom.html', mod=items_econom, kind='econom', pair='main',
         label='Обзор 1 · эконом', tab='Обзор 1',
         missing_note='Мебельной фурнитуры и шаблонов в Петровиче нет. Их покупают в магазинах мебельной фурнитуры, в сумму они не входят.',
         title='Эконом-вариант: тот же набор недорогими марками',
         lead='Тот же список из видео, но собранный на недорогих марках Петровича — КМ, КМ АТОМ, P.I.T., Зубр, '
              'Hesler, Sparta. Аккумуляторный инструмент на одной платформе КМ АТОМ 18 В, степлер электрический, '
              'как в видео, характеристики держатся на уровне оригинала: диск 165 мм, перфоратор 2,6 Дж, '
              'зелёный лазер со штативом.'),
    dict(key='m2', file='master2.html', mod=items_master2, kind='main', pair='m2econom',
         label='Обзор 2 · основной', tab='Обзор 2',
         missing_note='Профессиональные бренды (Milwaukee, Festool), направляющие шины с погружными пилами, кондукторы Рона и мебельная фурнитура в Петровиче не продаются. В сумму они не входят: их берут у дилеров инструмента и в магазинах мебельной фурнитуры.',
         title='Инструмент второго сборщика: Bosch, Milwaukee и подсветка',
         lead='Второй обзор — мастер из Севастополя: пила по шине, шуруповёрт Bosch 18 В, компактная линейка '
              'Milwaukee 12 В, кейсы Festool и отдельный кейс электрики под подсветку кухонь. Milwaukee, Festool, '
              'шин и погружных пил в Петровиче нет — для них подобраны аналоги, остальное вынесено в список внизу.'),
    dict(key='m2econom', file='master2-econom.html', mod=items_master2_econom, kind='econom', pair='m2',
         label='Обзор 2 · эконом', tab='Обзор 2',
         missing_note='Профессиональные бренды (Milwaukee, Festool), направляющие шины с погружными пилами, кондукторы Рона и мебельная фурнитура в Петровиче не продаются. В сумму они не входят: их берут у дилеров инструмента и в магазинах мебельной фурнитуры.',
         title='Второй сборщик, эконом-вариант',
         lead='Тот же набор второго обзора на недорогих марках: аккумуляторная часть на одной платформе '
              'КМ АТОМ 18 В, сетевые лобзик, перфоратор и реноватор, тот же лазер Ada Cube Mini Green '
              'в базовой версии, подсветка на ленте Apeyron 12 В.'),
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
        data = dict(built[page['key']], variant=page['kind'], page=page['key'], h1=page['title'], lead=page['lead'], missing_note=page['missing_note'],
                    other=round(built[page['pair']]['total'], 2),
                    pages=[dict(file=p['file'], label=p['label'], current=p['key'] == page['key']) for p in PAGES])
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
    for a, b in (('main', 'econom'), ('m2', 'm2econom')):
        diff = built[a]['total'] - built[b]['total']
        print(f"\n{a}: эконом дешевле основного на {diff:,.0f} ₽ ({diff / built[a]['total'] * 100:.0f} %)")
