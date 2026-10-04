/** Bounded display of existing ShadeResponse cells; no fetching or fallback scene. */
export const SHADOW_STATES = Object.freeze([{
  code: 0,
  label: 'Unknown — unsupported receiver or missing geometry',
  dashed: true
}, {
  code: 1,
  label: 'Sunlit — calculated direct sun',
  dashed: false
}, {
  code: 2,
  label: 'Shaded — calculated building shadow',
  dashed: false
}, {
  code: 3,
  label: 'Night — not daytime shade',
  dashed: true
}, ]);

const MAX_CELLS = 65536;

function decode(response) {
  const {
    bounds,
    width,
    height,
    shade
  } = response;
  if (response.crs !== 'EPSG:2056' ||
    response.encoding !== 'base64-uint8-row-major-north-first' ||
    !['approximate', 'unknown', 'unsupported'].includes(response.availability) ||
    !['building-shadow-approximation', 'survey-raytrace'].includes(response.model) ||
    !Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 ||
    width * height > MAX_CELLS || !Array.isArray(bounds) || bounds.length !== 4 ||
    !bounds.every(Number.isFinite) || !shade || !Number.isFinite(shade.resolution_m) ||
    shade.resolution_m <= 0 || typeof shade.geometry_version !== 'string' ||
    !Number.isFinite(Date.parse(shade.requested_time)) ||
    !Number.isFinite(Date.parse(shade.effective_time))) throw new Error('Invalid shade grid metadata.');
  const [west, south, east, north] = bounds;
  if (Math.abs(east - west - width * shade.resolution_m) > 1e-6 ||
    Math.abs(north - south - height * shade.resolution_m) > 1e-6) {
    throw new Error('Shade grid bounds do not match its resolution.');
  }
  const bytes = atob(response.states);
  if (bytes.length !== width * height) throw new Error('Invalid shade cell count.');
  const counts = [0, 0, 0, 0];
  for (let i = 0; i < bytes.length; i++) {
    const code = bytes.charCodeAt(i);
    if (code > 3) throw new Error('Invalid shade cell state.');
    counts[code]++;
  }
  if (['unknown', 'sunlit', 'shaded', 'night'].some((name, i) => response.counts?.[name] !== counts[i]) ||
    (response.availability !== 'approximate' && counts[0] !== bytes.length)) {
    throw new Error('Shade availability/counts contradict the cells.');
  }
  return bytes;
}

/** Mount on D's map. For non-LV95 views provide a verified LV95→view transform.
 * projectCoordinate([easting,northing], viewProjectionCode) must return metres
 * in that view CRS. No approximate Swiss conversion or identity fallback is used.
 */
export function mountShadowOverlay(map, {
  projectCoordinate,
  visible = false,
  zIndex = 2,
  onStatus = () => {},
} = {}) {
  const ol = window.ol;
  const source = new ol.source.Vector({
    wrapX: false
  });
  const theme = getComputedStyle(document.documentElement);
  const colour = (name, fallback) => theme.getPropertyValue(name).trim() || fallback;
  const styles = [
    new ol.style.Style({
      stroke: new ol.style.Stroke({
        color: colour('--unknown', '#5b6470'),
        width: 1,
        lineDash: [2, 3]
      })
    }),
    null, // Sunlit cells remain transparent, not a temperature overlay.
    new ol.style.Style({
      fill: new ol.style.Fill({
        color: colour('--shade', '#446856')
      })
    }),
    new ol.style.Style({
      stroke: new ol.style.Stroke({
        color: colour('--ink', '#172b3a'),
        width: 2,
        lineDash: [7, 3]
      })
    }),
  ];
  const layer = new ol.layer.Vector({
    source,
    visible,
    zIndex,
    opacity: 0.45,
    style: feature => styles[feature.get('shadeState')] ?? []
  });
  map.addLayer(layer);
  let disposed = false;
  let status = {
    availability: 'missing',
    explanation: 'Shadow areas unavailable.',
    legend: SHADOW_STATES
  };

  function update(response) {
    if (disposed) throw new Error('Shadow overlay is disposed.');
    source.clear(); // Failed or superseded input must never retain previous shadows.
    status = {
      availability: 'missing',
      explanation: 'Shadow areas unavailable.',
      legend: SHADOW_STATES
    };
    if (response) {
      try {
        const bytes = decode(response);
        const projection = map.getView().getProjection().getCode();
        if (projection !== 'EPSG:2056' && typeof projectCoordinate !== 'function') {
          throw new Error('A verified LV95 map projection transform is required.');
        }
        const project = point => {
          const result = projection === 'EPSG:2056' ? point : projectCoordinate(point, projection);
          if (!Array.isArray(result) || result.length !== 2 || !result.every(Number.isFinite)) {
            throw new Error('Invalid projected shade coordinate.');
          }
          return result;
        };
        const features = [];
        const [west, , , north] = response.bounds;
        const size = response.shade.resolution_m;
        for (let row = 0; row < response.height; row++) {
          for (let column = 0; column < response.width; column++) {
            const code = bytes.charCodeAt(row * response.width + column);
            const x = west + column * size;
            const y = north - row * size;
            const ring = [
              [x, y],
              [x + size, y],
              [x + size, y - size],
              [x, y - size],
              [x, y]
            ];
            features.push(new ol.Feature({
              geometry: new ol.geom.Polygon([ring.map(project)]),
              shadeState: code,
              shadeLabel: SHADOW_STATES[code].label,
              row,
              column,
              effectiveTime: response.shade.effective_time
            }));
          }
        }
        source.addFeatures(features);
        status = {
          availability: response.availability,
          explanation: response.explanation,
          model: response.model,
          shade: {
            ...response.shade
          },
          bounds: [...response.bounds],
          counts: {
            ...response.counts
          },
          legend: SHADOW_STATES
        };
      } catch (error) {
        source.clear();
        status = {
          availability: 'unsupported',
          explanation: `Shadow areas unavailable: ${error.message}`,
          legend: SHADOW_STATES
        };
      }
    }
    layer.set('shadowStatus', status);
    onStatus(status);
    return status;
  }

  update(null);
  return {
    layer,
    update,
    setVisible(value) {
      if (!disposed) layer.setVisible(Boolean(value));
    },
    dispose() {
      if (disposed) return;
      source.clear();
      map.removeLayer(layer);
      disposed = true;
    },
  };
}
