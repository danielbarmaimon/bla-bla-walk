// Cancel old endpoint requests and never let late geometry replace the current pair.
export function walkingRouting(mode, settings, receive) {
  let timer;
  let controller;
  let version = 0;

  function clear() {
    clearTimeout(timer);
    controller?.abort();
    version += 1;
  }

  async function request(start, end, token, departureTime, retry = true) {
    controller = new AbortController();
    try {
      const response = await fetch('/api/walking-routes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          start,
          end,
          mode,
          departure_time: departureTime
        }),
        signal: controller.signal,
        cache: 'no-store'
      });
      if (token !== version) return;
      if (response.status === 429 && retry) {
        timer = setTimeout(() => request(start, end, token, departureTime, false), 1100);
        return;
      }
      if (response.status === 422) {
        receive(null, 'Choose different endpoints within Basel-Stadt.');
        return;
      }
      if (!response.ok) throw new Error('Walking route unavailable');
      const layer = await response.json();
      if (token !== version) return;
      receive(layer, `${layer.features.length} street-following walking route(s) calculated. Fast and Recommended are ready.`);
    } catch (error) {
      if (error.name !== 'AbortError' && token === version) receive(null, 'Walking route unavailable. Retry, refine the endpoints or use the saved example.');
    }
  }

  function start(origin, destination, departureTime) {
    clear();
    if (mode === 'offline') {
      receive(null, 'Offline: no routing graph for new endpoints. The saved SBB → Marktplatz routes remain available.');
      return;
    }
    receive(null, 'Calculating a walking route for the selected endpoints…');
    const token = version;
    timer = setTimeout(() => request(origin, destination, token, departureTime), settings.debounce_ms);
  }
  return {
    start,
    clear
  };
}
