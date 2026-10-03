import {
  snapshotSchema
} from './snapshot.schema.js';
import {
  journeySchema
} from './journey.schema.js';

const ajv = new window.ajv2020({
  strict: false
});
// Wire datetimes require an explicit timezone, as the Python model does.
ajv.addFormat('date-time', (value) =>
  /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)),
);
const isSnapshot = ajv.compile(snapshotSchema);
const isJourney = ajv.compile(journeySchema);

/** Validate exact-time comparison evidence at the browser boundary. */
export async function loadComparison(request) {
  const response = await fetch('/api/comparison', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(request),
    signal: AbortSignal.timeout(10000)
  });
  if (!response.ok) throw new Error('Comparison unavailable: local inputs missing, calculation failed or another departure is busy. Retry after checking inputs.');
  const value = await response.json();
  if (!isJourney(value)) throw new Error('Comparison API returned invalid evidence.');
  return value;
}

/** Validate the API boundary using the schema generated from Python models.
 * @returns {import('./interfaces').MapSnapshot}
 */
export function parseSnapshot(value) {
  if (!isSnapshot(value)) {
    throw new Error('The map API returned data that does not match its contract.');
  }
  return {
    ...value,
    mode: value.mode ?? 'fixture'
  };
}

/** Fetch one snapshot with bounded waiting; callers show a visible failure. */
export async function loadSnapshot() {
  const mode = new URLSearchParams(location.search).get('mode') ?? 'fixture';
  const response = await fetch(`/api/map?mode=${encodeURIComponent(mode)}`, {
    signal: AbortSignal.timeout(mode === 'online' ? 90_000 : 10_000),
  });
  if (!response.ok) throw new Error('The map API is unavailable.');
  return parseSnapshot(await response.json());
}
