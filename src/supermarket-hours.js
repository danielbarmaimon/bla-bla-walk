const DAYS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

// Conservative weekly subset: unsupported schedules never establish opening.
export function scheduledOpen(hours, instant, holidays) {
  if (!hours || !Number.isFinite(instant.getTime())) return false;
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Zurich',
    weekday: 'short',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23'
  }).formatToParts(instant).map(part => [part.type, part.value]));
  const date = `${parts.year}-${parts.month}-${parts.day}`;
  if (!holidays[parts.year] || holidays[parts.year].includes(date)) return false;
  if (hours === '24/7') return true;
  const day = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].indexOf(parts.weekday);
  const minute = Number(parts.hour) * 60 + Number(parts.minute);
  let open = false;
  for (const rule of hours.split(';').map(value => value.trim())) {
    if (/^PH (off|closed)$/.test(rule)) continue;
    const match = rule.match(/^([A-Za-z,-]+) (off|closed|[0-9:, -]+)$/);
    if (!match) return false;
    const selected = [];
    for (const range of match[1].split(',')) {
      const [start, end = start] = range.split('-').map(value => DAYS.indexOf(value));
      if (start < 0 || end < start) return false;
      for (let index = start; index <= end; index++) selected.push(index);
    }
    if (['off', 'closed'].includes(match[2])) {
      if (selected.includes(day)) open = false;
      continue;
    }
    let ruleOpen = false;
    for (const window of match[2].split(',')) {
      const time = window.trim().match(/^(\d{2}):(\d{2})-(\d{2}):(\d{2})$/);
      if (!time) return false;
      const [a, b, c, d] = time.slice(1).map(Number);
      const start = a * 60 + b,
        end = c * 60 + d;
      if (a > 23 || b > 59 || c > 24 || d > 59 || (c === 24 && d !== 0) || end <= start) return false;
      if (selected.includes(day) && minute >= start && minute < end) ruleOpen = true;
    }
    if (selected.includes(day)) open = ruleOpen;
  }
  return open;
}
