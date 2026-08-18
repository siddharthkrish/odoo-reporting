const test = require('node:test');
const assert = require('node:assert/strict');

const { completedPresetRange, currentMonthRange } = require('../odoo_sales/static/date_ranges.js');

const july13 = new Date(2026, 6, 13, 12);

test('this month runs from the first day through today', () => {
  assert.deepEqual(currentMonthRange(july13), {
    from: '2026-07-01',
    to: '2026-07-13',
  });
});

test('last month is the previous complete calendar month', () => {
  assert.deepEqual(completedPresetRange(1, 'month', july13), {
    from: '2026-06-01',
    to: '2026-06-30',
  });
});

test('multi-month presets include complete preceding months', () => {
  assert.deepEqual(completedPresetRange(3, 'month', july13), {
    from: '2026-04-01',
    to: '2026-06-30',
  });
  assert.deepEqual(completedPresetRange(6, 'month', july13), {
    from: '2026-01-01',
    to: '2026-06-30',
  });
});

test('month presets cross year boundaries', () => {
  const february = new Date(2026, 1, 18, 12);
  assert.deepEqual(completedPresetRange(3, 'month', february), {
    from: '2025-11-01',
    to: '2026-01-31',
  });
});

test('last year is the previous complete calendar year', () => {
  assert.deepEqual(completedPresetRange(1, 'year', july13), {
    from: '2025-01-01',
    to: '2025-12-31',
  });
});
