const NUMBER = new Intl.NumberFormat('en-GB', {
  maximumFractionDigits: 0
});

function textElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  return element;
}

function metres(value) {
  return Number.isFinite(value) ? `${NUMBER.format(value)} m` : 'Unknown';
}

function percentage(value) {
  return Number.isFinite(value) ? `${NUMBER.format(value)}%` : 'Unknown';
}

function routeMetrics(route, metrics) {
  const summary = document.createElement('dl');
  summary.className = 'comparison-metrics';
  const entries = [
    ['Walking estimate', `${metres(route.route?.distance_m)} · ${Number.isFinite(route.route?.duration_s) ? `${NUMBER.format(route.route.duration_s / 60)} min` : 'time unknown'}`],
    ['Trip duration', metrics ? `${NUMBER.format(metrics.duration_minutes)} min · ${NUMBER.format(metrics.walking_minutes)} walking + ${NUMBER.format(metrics.stop_minutes)} stop` : 'Unknown · comparison pending'],
    ['Shade / exposed', metrics ? `${metres(metrics.shaded_metres)} shaded (${percentage(metrics.shade_percentage)}) · ${metres(metrics.unshaded_metres)} exposed (${percentage(metrics.unshaded_percentage)})` : 'Unknown · shade not calculated'],
    ['Unknown coverage', metrics ? `${metres(metrics.unknown_metres)} (${percentage(metrics.unknown_percentage)})` : 'Unknown · calculation unavailable'],
    ['Water evidence', metrics?.water_complete ? metrics.water_state?.replaceAll('_', ' ') : 'Unknown · operation, access or freshness unverified']
  ];
  entries.forEach(([label, value]) => {
    summary.append(textElement('dt', '', label), textElement('dd', '', value));
  });
  return summary;
}

/** Render T5 comparison evidence without promoting missing evidence to a claim. */
export function renderTripComparison(container, {
  routes,
  comparison = null,
  evidence = [],
  preference = 'fastest_overall',
  selectedRouteId,
  onChoose = () => {},
  onShow = () => {}
}) {
  const focused = container.contains(document.activeElement) ? document.activeElement.dataset : null;
  const focusedRoute = focused?.routeId;
  const focusedAction = focused?.action;
  container.replaceChildren();
  const view = comparison?.[preference];
  const status = textElement(
    'p',
    'comparison-status',
    view ? view.explanation : 'No calculated comparison for this departure. Eligibility and recommendations remain unknown. Transit unavailable.'
  );
  status.setAttribute('role', 'status');
  container.append(status);

  routes.forEach((route) => {
    const card = document.createElement('article');
    card.className = 'comparison-card';
    if (route.id === selectedRouteId) card.classList.add('is-selected');
    const heading = document.createElement('div');
    heading.className = 'comparison-card-heading';
    heading.append(textElement('h3', '', route.label));
    const routeStatus = view?.route_statuses?.[route.id] ?? 'comparison pending';
    heading.append(textElement('span', 'route-eligibility', `${view?.winner === route.id ? 'Recommended · ' : ''}${routeStatus.replaceAll('_', ' ')}`));
    card.append(heading);
    card.append(routeMetrics(route, view?.metrics?.[route.id]));
    const routeEvidence = evidence.find((item) => item.id === route.id);
    if (routeEvidence?.samples.length) {
      const samples = routeEvidence.samples;
      const times = samples.map((sample) => sample.metadata?.effective_time).filter(Boolean);
      card.append(textElement('p', 'comparison-historical',
        `Locally calculated traversal samples · requested ${samples[0].requested_time} to ${samples.at(-1).requested_time} · effective ${times[0] ?? 'unavailable'} to ${times.at(-1) ?? 'unavailable'}. Night intervals: ${samples.filter((sample) => sample.state === 3).length}; night earns no shade credit.`));
      const details = document.createElement('details');
      details.append(textElement('summary', '', 'Shade model and source evidence'));
      details.append(textElement('p', '', samples[0].explanation));
      details.append(textElement('p', '', `Model: ${samples[0].model} · geometry: ${samples[0].metadata?.geometry_version ?? 'unavailable'}. Route source retrieved: ${routeEvidence.provenance?.retrieved_at ?? 'unknown'}.`));
      card.append(details);
    }

    if (route.pet) {
      card.append(textElement(
        'p',
        'comparison-historical',
        `Historical PET · ${metres(route.pet.known_distance_m)} classified · ${metres(route.pet.unknown_distance_m)} unknown · ${route.pet.availability}`
      ));
    }
    const reasons = view?.reasons?.[route.id] ?? [];
    if (reasons.length) card.append(textElement('p', 'comparison-reasons', `Cannot recommend: ${reasons.join(', ').replaceAll('_', ' ')}.`));

    const actions = document.createElement('div');
    actions.className = 'comparison-actions';
    const show = document.createElement('button');
    show.type = 'button';
    show.className = 'comparison-secondary';
    show.dataset.routeId = route.id;
    show.dataset.action = 'show';
    show.textContent = 'Show on map';
    show.addEventListener('click', () => onShow(route));
    const choose = document.createElement('button');
    choose.type = 'button';
    choose.className = 'comparison-primary';
    choose.dataset.routeId = route.id;
    choose.dataset.action = 'choose';
    choose.textContent = route.id === selectedRouteId ? (view?.manual_choices?.includes(route.id) ? 'Chosen route' : 'Shown route') : 'Choose route';
    choose.setAttribute('aria-pressed', String(route.id === selectedRouteId));
    const eligible = view?.manual_choices?.includes(route.id) ?? false;
    choose.disabled = !eligible;
    choose.addEventListener('click', () => onChoose(route));
    actions.append(show, choose);
    card.append(actions);
    container.append(card);
  });
  if (focusedRoute && focusedAction) container.querySelector(`[data-route-id="${CSS.escape(focusedRoute)}"][data-action="${CSS.escape(focusedAction)}"]`)?.focus({
    preventScroll: true
  });
}
