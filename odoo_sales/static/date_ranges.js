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

  return { completedPresetRange, currentMonthRange, toLocalIso };
});
