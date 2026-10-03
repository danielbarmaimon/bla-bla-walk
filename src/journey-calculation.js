// Exact-time jobs stay on the app origin, including offline mode.
import {
  comparisonJobSchema
} from './comparison.schema.js';

const validator = new window.ajv2020({
  strict: false
});
validator.addFormat('date-time', (value) => /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)));
const isJob = validator.compile(comparisonJobSchema);

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    signal: AbortSignal.timeout(15_000)
  });
  const value = await response.json();
  if (!response.ok) throw new Error(typeof value.detail === 'string' ? value.detail : 'Journey request unavailable. Check the selected time and retry.');
  if (!isJob(value)) throw new Error('Journey response does not match its contract.');
  return value;
}

/** Discard late responses after departure/source changes; never reuse old credit. */
export function journeyCalculation(onChange) {
  let generation = 0;
  let timer;
  let job = null;
  let preferences = {
    weights: {
      shade: 0.5,
      duration: 0.4,
      water: 0.1
    },
    extra_time_limit_minutes: null
  };
  let preferenceRevision = 0;

  function cancel(value) {
    if (value?.status === 'running') void fetch(`/api/comparison/${value.id}`, {
      method: 'DELETE',
      signal: AbortSignal.timeout(15_000)
    }).catch(() => {});
  }

  function clear() {
    cancel(job);
    generation += 1;
    clearTimeout(timer);
    job = null;
    onChange(null, 'Choose a departure and calculate. Cold calculations can take around 20 minutes.');
  }

  async function rescore() {
    if (job?.status !== 'ready') return;
    const token = generation;
    const revision = ++preferenceRevision;
    try {
      const value = await request(`/api/comparison/${job.id}/rescore`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(preferences),
      });
      if (token !== generation || revision !== preferenceRevision) return;
      job = value;
      onChange(job, job.explanation);
    } catch (error) {
      if (token === generation && revision === preferenceRevision) onChange(null, error.message);
    }
  }

  async function poll(token) {
    if (token !== generation || !job) return;
    try {
      const value = await request(`/api/comparison/${job.id}`);
      if (token !== generation) return;
      job = value;
      onChange(job, job.explanation);
      if (job.status === 'running') timer = setTimeout(() => poll(token), 5000);
      else if (job.status === 'ready') await rescore();
    } catch (error) {
      if (token === generation) onChange(null, `${error.message} Start again to retry.`);
    }
  }

  return {
    clear,
    setPreferences(value) {
      preferences = value;
      void rescore();
    },
    async start(departureTime) {
      clear();
      const token = generation;
      onChange(null, 'Checking local shade preparation…');
      try {
        const value = await request('/api/comparison', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            departure_time: departureTime
          }),
        });
        if (token !== generation) {
          cancel(value);
          return;
        }
        job = value;
        onChange(job, job.explanation);
        if (job.status === 'running') timer = setTimeout(() => poll(token), 1000);
        else if (job.status === 'ready') await rescore();
      } catch (error) {
        if (token === generation) onChange(null, error.message);
      }
    },
  };
}
