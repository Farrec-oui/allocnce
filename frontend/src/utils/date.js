const MONTHS = {
  JAN:0, FEB:1, MAR:2, APR:3, MAY:4, JUN:5,
  JUL:6, AUG:7, SEP:8, OCT:9, NOV:10, DEC:11,
};

export function parseAllocDate(dateStr) {
  if (!dateStr) return null;
  const day   = parseInt(dateStr.slice(0, 2), 10);
  const month = MONTHS[dateStr.slice(2, 5).toUpperCase()];
  const year  = 2000 + parseInt(dateStr.slice(5, 7), 10);
  if (month === undefined || isNaN(day) || isNaN(year)) return null;
  return new Date(year, month, day);
}
