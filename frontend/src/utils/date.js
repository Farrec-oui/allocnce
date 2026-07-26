const MONTHS = {
  JAN:0, FEB:1, MAR:2, APR:3, MAY:4, JUN:5,
  JUL:6, AUG:7, SEP:8, OCT:9, NOV:10, DEC:11,
};

const MONTH_NAMES = Object.keys(MONTHS);

/** '2026-07-25' (input type=date) → '25JUL26' (format stocké en base). */
export function isoToAllocDate(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  const month = MONTH_NAMES[parseInt(m, 10) - 1];
  if (!month) return "";
  return `${d}${month}${y.slice(2)}`;
}

export function parseAllocDate(dateStr) {
  if (!dateStr) return null;
  const day   = parseInt(dateStr.slice(0, 2), 10);
  const month = MONTHS[dateStr.slice(2, 5).toUpperCase()];
  const year  = 2000 + parseInt(dateStr.slice(5, 7), 10);
  if (month === undefined || isNaN(day) || isNaN(year)) return null;
  return new Date(year, month, day);
}
