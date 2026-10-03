import {
  routeGeometry,
  coordinateAtFraction
} from './route-planner-data.js';
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
  const theme = getComputedStyle(document.documentElement);
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
  const shadeSamples = new VectorSource();
  const shadeLayer = new VectorLayer({
    source: shadeSamples,
    zIndex: 3,
    style: (feature) => new Style({
      image: new CircleStyle({
        radius: 5,
        fill: new Fill({
          color: theme.getPropertyValue(
            feature.get('state') === 2 ? '--shade' : feature.get('state') === 1 ? '--exposed' : '--text-muted'
          ).trim()
        }),
        stroke: new Stroke({
          color: theme.getPropertyValue('--marker-outline').trim(),
          width: 1
        })
      })
    })
  });
  map.addLayer(shadeLayer);
  const pinFeatures = new VectorSource();
  const pinLayer = new VectorLayer({
    source: pinFeatures,
    style: (marker) => new Style({
      image: new CircleStyle({
        radius: 10,
        fill: new Fill({
          color: theme.getPropertyValue(marker.get('pinKind') === 'origin' ? '--poc-origin' : '--poc-destination').trim(),
        }),
        stroke: new Stroke({
          color: theme.getPropertyValue('--marker-outline').trim(),
          width: 3
        }),
      }),
    }),
  });
  map.addLayer(pinLayer);
  const contextFeatures = new VectorSource();
  const contextLayer = new VectorLayer({
    source: contextFeatures,
    style: (marker) => new Style({
      image: new CircleStyle({
        radius: marker.get('kind') === 'rest' || marker.get('kind') === 'pause' ? 8 : 6,
        fill: new Fill({
          color: theme.getPropertyValue('--poc-teal').trim()
        }),
        stroke: new Stroke({
          color: theme.getPropertyValue('--marker-outline').trim(),
          width: 2
        }),
      }),
      text: new window.ol.style.Text({
        text: marker.get('label'),
        offsetY: -17,
        font: '700 12px sans-serif',
        fill: new Fill({
          color: theme.getPropertyValue('--text-primary').trim()
        }),
        backgroundFill: new Fill({
          color: '#ffffff'
        }),
        padding: [2, 4, 2, 4],
      }),
    }),
  });
  map.addLayer(contextLayer);
  let picking = null;
  map.on('singleclick', (event) => {
    if (picking) {
      const [longitude, latitude] = window.ol.proj.toLonLat(event.coordinate);
      const kind = picking.kind;
      const callback = picking.callback;
      picking = null;
      callback(kind, {
        lon: longitude,
        lat: latitude
      });
      return;
    }
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
    setShadeVisible: (visible) => shadeLayer.setVisible(visible),
    setShadeSamples: (routes, evidence) => {
      shadeSamples.clear();
      [...features.keys()].filter((id) => id.startsWith('sample-')).forEach((id) => features.delete(id));
      evidence.forEach((result) => {
        const route = routes.find((item) => item.id === result.id);
        if (!route) return;
        const line = routeGeometry(route.geometry.coordinates);
        result.samples.forEach((sample, index) => {
          const coordinates = coordinateAtFraction(line, (sample.start_metres + sample.end_metres) / 2 / result.distance_metres);
          const id = `sample-${route.id}-${index}`;
          const stateLabel = ['Unknown', 'Sunlit approximation', 'Shaded approximation', 'Night · no shade credit'][sample.state];
          const value = {
            id,
            label: `${route.label} · ${stateLabel}`,
            kind: 'shade',
            geometry: {
              type: 'Point',
              coordinates
            },
            availability: sample.state === 0 ? 'unknown' : 'current',
            value: null,
            unit: null,
            provenance: route.provenance,
            shade: sample.metadata,
            explanation: `Traversal midpoint sample, not area coverage or observed cooling. ${sample.explanation}`
          };
          features.set(id, value);
          const marker = new Feature({
            geometry: new window.ol.geom.Point(fromLonLat(coordinates))
          });
          marker.setId(id);
          marker.set('state', sample.state);
          shadeSamples.addFeature(marker);
        });
      });
    },
    updateSize: () => map.updateSize(),
    setPetVisible: (visible) => petLayer.setVisible(visible && !offline),
    setVisible: (id, visible) => layers.get(id)?.setVisible(visible),
    setPins: (origin, destination) => {
      pinFeatures.clear();
      [origin, destination].filter(Boolean).forEach((place, index) => {
        const marker = new Feature({
          geometry: new window.ol.geom.Point(fromLonLat([place.lon, place.lat])),
        });
        marker.set('pinKind', index === 0 ? 'origin' : 'destination');
        pinFeatures.addFeature(marker);
      });
    },
    setContextMarkers: (markers) => {
      contextFeatures.clear();
      markers.forEach((item) => {
        const marker = new Feature({
          geometry: new window.ol.geom.Point(fromLonLat(item.coordinates)),
        });
        marker.set('kind', item.kind);
        marker.set('label', item.label);
        contextFeatures.addFeature(marker);
      });
    },
    setPicking: (kind, callback) => {
      picking = kind ? {
        kind,
        callback
      } : null;
    },
    focusCoordinates: (coordinates) => {
      if (!coordinates?.length) return;
      const projected = coordinates.map((coordinate) => fromLonLat(coordinate));
      map.getView().fit(window.ol.extent.boundingExtent(projected), {
        maxZoom: 16,
        duration: 250,
        padding: [75, 75, 75, 75],
      });
    },
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
