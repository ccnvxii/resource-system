"""
Запуск тестів зі зведеним звітом (для додавання таблиць у дипломну роботу).

Підключається в settings.py: TEST_RUNNER = 'app.tests.report_runner.ReportRunner'.
Після кожного запуску створює файли у backend/test_reports/:
    test_report.csv - таблиця (відкривається в Excel / Word / Google Sheets);
    test_report.md  - те саме у вигляді Markdown-таблиць за категоріями.

Оформлення тестів:
    * перший рядок докстрінга класу  - назва категорії (напр. «Безпека»);
    * ім'я методу test_NN_...        - порядковий номер у межах категорії;
    * перший рядок докстрінга методу - назва тесту.
"""
import csv
import inspect
import re
import time
import unittest
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.test.runner import DiscoverRunner

GROUP_RANK = {  # порядок розділів у звіті
    'test_math_models': (0, 'Математичні моделі'),
    'test_fair_comp': (0.5, 'Математичні моделі'),
    'test_functional': (1, 'Функціональне тестування'),
    'test_nonfunctional': (2, 'Нефункціональне тестування'),
}
STATUS_UA = {'ok': 'ПРОЙДЕНО', 'fail': 'ПРОВАЛЕНО', 'error': 'ПОМИЛКА', 'skip': 'ПРОПУЩЕНО'}


def _first_line(doc, fallback=''):
    if not doc:
        return fallback
    return doc.strip().splitlines()[0].strip()


class ReportResult(unittest.TextTestResult):
    records = []

    def startTest(self, test):
        self._t0 = time.perf_counter()
        super().startTest(test)

    def _add(self, test, status):
        cls = type(test)
        method = getattr(test, '_testMethodName', '')
        fn = getattr(cls, method, None)
        module = cls.__module__.split('.')[-1]
        group_rank, group = GROUP_RANK.get(module, (9, module))
        try:
            cls_line = inspect.getsourcelines(cls)[1]
        except (OSError, TypeError):
            cls_line = 0
        fn_line = getattr(getattr(fn, '__code__', None), 'co_firstlineno', 0)
        match = re.match(r'test_(\d+)', method)
        self.records.append({
            'rank': (group_rank, module, cls_line, int(match.group(1)) if match else fn_line),
            'group': group,
            'category': _first_line(cls.__doc__, cls.__name__),
            'number': int(match.group(1)) if match else None,
            'name': _first_line(getattr(fn, '__doc__', None), method),
            'status': status,
            'seconds': time.perf_counter() - getattr(self, '_t0', time.perf_counter()),
        })

    def addSuccess(self, test):
        super().addSuccess(test)
        self._add(test, 'ok')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._add(test, 'fail')

    def addError(self, test, err):
        super().addError(test, err)
        self._add(test, 'error')

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._add(test, 'skip')


class ReportRunner(DiscoverRunner):
    def get_resultclass(self):
        return ReportResult

    def run_tests(self, test_labels, **kwargs):
        ReportResult.records = []
        failures = super().run_tests(test_labels, **kwargs)
        try:
            self._write_reports(sorted(ReportResult.records, key=lambda r: r['rank']))
        except Exception as exc:  # звіт не повинен ламати запуск тестів
            print(f'[Звіт] Не вдалося сформувати файли звіту: {exc}')
        return failures

    @staticmethod
    def _write_reports(records):
        if not records:
            return
        out_dir = Path(settings.BASE_DIR) / 'test_reports'
        out_dir.mkdir(exist_ok=True)

        for rec in records:  # якщо номерів у класі немає - нумеруємо за порядком
            pass
        counters = {}
        for rec in records:
            key = (rec['group'], rec['category'])
            counters[key] = counters.get(key, 0) + 1
            if rec['number'] is None:
                rec['number'] = counters[key]

        with open(out_dir / 'test_report.csv', 'w', newline='', encoding='utf-8-sig') as fh:
            writer = csv.writer(fh, delimiter=';')
            writer.writerow(['Розділ', 'Категорія', '№', 'Назва тесту', 'Результат', 'Час, с'])
            for r in records:
                writer.writerow([r['group'], r['category'], r['number'], r['name'],
                                 STATUS_UA[r['status']], f"{r['seconds']:.3f}".replace('.', ',')])

        total = len(records)
        passed = sum(1 for r in records if r['status'] == 'ok')
        lines = [
            '# Звіт про тестування',
            '',
            f'Сформовано: {datetime.now():%d.%m.%Y %H:%M}. Усього тестів: {total}, пройдено: {passed}, '
            f'не пройдено: {total - passed}.',
            '',
        ]
        group = category = None
        for r in records:
            if r['group'] != group:
                group = r['group']
                category = None
                lines += [f'## {group}', '']
            if r['category'] != category:
                category = r['category']
                in_cat = [x for x in records if x['group'] == group and x['category'] == category]
                lines += [f'### {category} (тести 1-{len(in_cat)})', '',
                          '| № | Тест | Результат | Час, с |', '|---|---|---|---|']
            lines.append(f"| {r['number']} | {r['name']} | {STATUS_UA[r['status']]} | {r['seconds']:.2f} |")
            nxt_idx = records.index(r) + 1
            if nxt_idx >= len(records) or records[nxt_idx]['category'] != category or records[nxt_idx]['group'] != group:
                lines.append('')
        (out_dir / 'test_report.md').write_text('\n'.join(lines), encoding='utf-8')
        print(f'\n[Звіт] Таблиці збережено: {out_dir / "test_report.csv"} та test_report.md')
