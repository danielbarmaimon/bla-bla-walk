export const badgeActive = selector => document.querySelector(selector)?.getAttribute('aria-pressed') === 'true';

export function installLayerBadges(onChange) {
  document.querySelectorAll('.layer-badge').forEach(button => {
    button.addEventListener('click', () => {
      button.setAttribute('aria-pressed', String(button.getAttribute('aria-pressed') !== 'true'));
      onChange();
    });
  });
}

export function visibleRouteIds(routes, winner, fast, recommended) {
  const fastest = [...routes].sort((a, b) => a.route.duration_s - b.route.duration_s)[0];
  return [...new Set([fast ? fastest?.id : null, recommended ? winner : null].filter(Boolean))];
}
