const {
  Feature,
  Map,
  View
} = window.ol;
const {
  GeoJSON
} = window.ol.format;
const {
  Image: ImageLayer,
  Tile: TileLayer,
  Vector: VectorLayer
} = window.ol.layer;
const {
  fromLonLat,
  transformExtent
} = window.ol.proj;
const {
  ImageWMS,
  Vector: VectorSource,
  XYZ
} = window.ol.source;
const {
  Circle: CircleStyle,
  Fill,
  RegularShape,
  Stroke,
  Style
} = window.ol.style;

// Official 3857 matrix set uses standard XYZ coordinates.
const configResponse = await fetch('/config/basemap.json');
if (!configResponse.ok) throw new Error('Basemap configuration unavailable.');
const basemapConfig = await configResponse.json();
const offline = new URLSearchParams(location.search).get('mode') === 'offline';
const online = new URLSearchParams(location.search).get('mode') === 'online';
const BASEMAP_URL = offline ? '/tiles/{z}/{x}/{y}.png' : basemapConfig.url;
const BASEMAP_EXTENT = basemapConfig.bounds_wgs84;
const BASEL_CENTRE = [7.5886, 47.5596];
const PET_WMS_URL = 'https://wms.geo.bs.ch/';

/** Build the real basemap; fixture layers can be replaced independently. */
export function createMap(
  target,
  onSelect,
  onBasemapStatus,
  onPetStatus,
) {
  const source = new XYZ({
    url: BASEMAP_URL,
    maxZoom: basemapConfig.max_zoom,
    minZoom: basemapConfig.min_zoom,
    crossOrigin: 'anonymous',
    wrapX: false,
    attributions: '<a href="https://api.geo.bs.ch/stac/v1/collections/VSBS">Geodaten Kanton Basel-Stadt</a> · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>',
  });
  const petSource = new ImageWMS({
      url: PET_WMS_URL,
      params: {
        LAYERS: 'KL_HumanbioklimaSituation',
        STYLES: '',
        FORMAT: 'image/png',
        TRANSPARENT: true,
      },
      ratio: 1,
      attributions: '<a href="https://geo.bs.ch/stadtklima">Quelle: Geodaten Kanton Basel-Stadt</a> · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>',
    });
  petSource.on('imageloadend', () => onPetStatus('Historical PET map loaded · fixed 14:00 summer scenario.'));
  petSource.on('imageloaderror', () => onPetStatus('Historical PET map unavailable · route cells without data stay unknown.'));
  const petLayer = new ImageLayer({
    source: petSource,
    visible: online,
    opacity: 0.68,
    zIndex: 1,
  });
  let hadTileError = false;
  source.on('tileloadend', () => {
    if (!hadTileError) onBasemapStatus(offline ? 'Basel basemap loaded · downloaded offline map' : 'Basel basemap loaded · live tile service');
  });
  source.on('tileloaderror', () => {
    hadTileError = true;
    onBasemapStatus(offline ? 'Offline basemap partly unavailable: tiles not downloaded or outside saved coverage.' : 'Basemap partly unavailable. Check your connection and reload.');
  });
  const map = new Map({
    target,
    layers: [
      new TileLayer({
        source,
        extent: transformExtent(BASEMAP_EXTENT, 'EPSG:4326', 'EPSG:3857'),
      }),
      petLayer,
    ],
    view: new View({
      center: fromLonLat(BASEL_CENTRE),
      zoom: 14,
      minZoom: basemapConfig.min_zoom,
      maxZoom: basemapConfig.max_zoom,
      extent: offline ? transformExtent(BASEMAP_EXTENT, 'EPSG:4326', 'EPSG:3857') : undefined,
      constrainOnlyCenter: true,
    }),
  });
  const layers = new globalThis.Map();
  map.getControls().forEach((control) => {
    if (control instanceof window.ol.control.Attribution) {
      control.setCollapsible(false);
    }
  });
  const features = new globalThis.Map();
  map.on('singleclick', (event) => {
    map.forEachFeatureAtPixel(event.pixel, (feature) => {
      const selected = features.get(String(feature.getId()));
      if (selected) onSelect(selected);
      return true;
    });
  });

  function replaceLayers(snapshotLayers) {
    layers.forEach((layer) => map.removeLayer(layer));
    layers.clear();
    features.clear();
    const theme = getComputedStyle(document.documentElement);
    snapshotLayers.forEach((layer) => {
      const fill = new Fill({
        color: theme.getPropertyValue(`--${layer.kind}-color`).trim(),
      });
      const stroke = new Stroke({
        color: theme.getPropertyValue('--marker-outline').trim(),
        width: Number(theme.getPropertyValue('--marker-stroke')),
      });
      const radius = Number(theme.getPropertyValue('--marker-radius'));
      const image =
        layer.kind === 'observation' ?
        new RegularShape({
          points: 4,
          radius,
          angle: Math.PI / 4,
          fill,
          stroke
        }) :
        new CircleStyle({
          radius,
          fill,
          stroke
        });
      const vector = new VectorLayer({
        source: new VectorSource({
          features: layer.features.map((feature) => {
            features.set(feature.id, feature);
            const geometry = new GeoJSON().readGeometry(feature.geometry, {
              dataProjection: 'EPSG:4326',
              featureProjection: 'EPSG:3857',
            });
            const marker = new Feature({
              geometry
            });
            marker.setId(feature.id);
            return marker;
          }),
        }),
        style: (marker) => {
          const routeColor = marker.getId() === 'demo-route-b' ? '--route-b' : '--route-a';
          return new Style({
            image,
            stroke: layer.kind === 'route' ? new Stroke({
              color: theme.getPropertyValue(routeColor).trim(),
              width: Number(theme.getPropertyValue('--route-stroke-width')),
            }) : stroke,
            fill
          });
        },
      });
      layers.set(layer.id, vector);
      map.addLayer(vector);
    });
  }

  return {
    replaceLayers,
    setPetVisible: (visible) => petLayer.setVisible(visible && !offline),
    setVisible: (id, visible) => layers.get(id)?.setVisible(visible),
    focus: (feature) => {
      const geometry = new GeoJSON().readGeometry(feature.geometry, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857',
      });
      map.getView().fit(geometry, {
        maxZoom: 16,
        duration: 0,
        padding: Array(4).fill(Number(getComputedStyle(document.documentElement).getPropertyValue("--map-focus-padding")))
      });
    },
  };
}
