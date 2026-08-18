(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DateRanges = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function toLocalIso(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function currentMonthRange(now = new Date()) {
    const from = new Date(now.getFullYear(), now.getMonth(), 1);
    return { from: toLocalIso(from), to: toLocalIso(now) };
  }

  function completedPresetRange(n, unit, now = new Date()) {
    if (!Number.isInteger(n) || n < 1) throw new RangeError('n must be a positive integer');

    let from;
    let to;
    if (unit === 'month') {
      from = new Date(now.getFullYear(), now.getMonth() - n, 1);
      to = new Date(now.getFullYear(), now.getMonth(), 0);
    } else if (unit === 'year') {
      from = new Date(now.getFullYear() - n, 0, 1);
      to = new Date(now.getFullYear() - 1, 11, 31);
    } else {
      throw new RangeError(`Unsupported preset unit: ${unit}`);
    }

    return { from: toLocalIso(from), to: toLocalIso(to) };
  }

  function parseLocalIso(value) {
    const [year, month, day] = value.split('-').map(Number);
    return new Date(year, month - 1, day);
  }

  function previousPeriodRange(from, to) {
    const start = parseLocalIso(from);
    const end = parseLocalIso(to);
    const startDay = Date.UTC(start.getFullYear(), start.getMonth(), start.getDate());
    const endDay = Date.UTC(end.getFullYear(), end.getMonth(), end.getDate());
    const days = Math.round((endDay - startDay) / 86400000) + 1;
    const prevTo = new Date(start);
    prevTo.setDate(prevTo.getDate() - 1);
    const prevFrom = new Date(prevTo);
    prevFrom.setDate(prevFrom.getDate() - (days - 1));
    return { prevFrom: toLocalIso(prevFrom), prevTo: toLocalIso(prevTo) };
  }

  function previousYearDate(date) {
    const year = date.getFullYear() - 1;
    const month = date.getMonth();
    const lastDay = new Date(year, month + 1, 0).getDate();
    return new Date(year, month, Math.min(date.getDate(), lastDay));
  }

  function samePeriodPreviousYearRange(from, to) {
    return {
      prevFrom: toLocalIso(previousYearDate(parseLocalIso(from))),
      prevTo: toLocalIso(previousYearDate(parseLocalIso(to))),
    };
  }

  return {
    completedPresetRange,
    currentMonthRange,
    previousPeriodRange,
    samePeriodPreviousYearRange,
    toLocalIso,
  };
});
