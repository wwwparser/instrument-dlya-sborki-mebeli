# Инструмент для сборки кухонь и корпусной мебели

Сайт (обзор 1): https://wwwparser.github.io/instrument-dlya-sborki-mebeli/
Обзор 1, эконом: https://wwwparser.github.io/instrument-dlya-sborki-mebeli/econom.html
Обзор 2: https://wwwparser.github.io/instrument-dlya-sborki-mebeli/master2.html
Обзор 2, эконом: https://wwwparser.github.io/instrument-dlya-sborki-mebeli/master2-econom.html

Список инструмента и расходников опытного сборщика мебели (по видеообзору) с товарами,
ценами и ссылками на Петрович (Москва). Если модели из видео в магазине нет, подобран
ближайший аналог — на сайте он отмечен и объяснено, чем отличается.

Четыре страницы: два видеообзора, у каждого основной вариант (марки как в видео) и
эконом-вариант того же набора на недорогих марках (КМ, КМ АТОМ 18 В, P.I.T., Зубр,
Hesler, Sparta) при сопоставимых характеристиках.

- `items.py` — обзор 1, основной список: код товара Петровича, количество, что в видео (с таймкодом), аналог или нет.
- `items_econom.py` — обзор 1, эконом.
- `items_master2.py` / `items_master2_econom.py` — обзор 2 (мастер на Bosch 18 В и Milwaukee 12 В, с подсветкой кухонь).
- `build.py` — подставляет цены и собирает все четыре страницы в `docs/` (GitHub Pages).
- `prices.json` — снимок цен, чтобы пересобрать без базы: `python build.py --offline`.
