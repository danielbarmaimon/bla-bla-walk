import {
  routeGeometry,
  coordinateAtFraction
} from './route-planner-data.js';
import { MAX_VISIBLE_ROUTE_POINTS } from './route-node-details.js';
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
  Cluster,
  Vector: VectorSource,
  XYZ
} = window.ol.source;
const {
  Icon,
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
  onTemperatureSelect,
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
    visible: false,
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
  let shownRouteIds = null;
  map.getControls().forEach((control) => {
    if (control instanceof window.ol.control.Attribution) {
      control.setCollapsible(false);
    }
  });
  const features = new globalThis.Map();
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
    zIndex: 8,
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
  const stopSources = new globalThis.Map();
  const stopStyles = new globalThis.Map();
  const stopIcons = {
    water: 'droplets',
    bench: 'rocking-chair',
    rest: 'clock-fading'
  };
  for (const [kind, icon] of Object.entries(stopIcons)) {
    const members = new VectorSource();
    stopSources.set(kind, members);
    const clusters = new Cluster({
      distance: 38,
      source: members,
      // Anchor to a real member, preserving its position on the route.
      createCluster: (_point, grouped) => new Feature({
        geometry: grouped[0].getGeometry().clone(),
        features: grouped,
        stopKind: kind,
      }),
    });
    map.addLayer(new VectorLayer({
      source: clusters,
      zIndex: 8,
      style: cluster => {
        const count = cluster.get('features').length;
        const key = `${kind}:${count}`;
        if (!stopStyles.has(key)) stopStyles.set(key, [
          new Style({
            image: new CircleStyle({
              radius: 15,
              fill: new Fill({
                color: '#ffffff'
              }),
              stroke: new Stroke({
                color: theme.getPropertyValue('--poc-teal').trim(),
                width: 2
              }),
            })
          }),
          new Style({
            image: new Icon({
              src: `/src/icons/${icon}.svg`,
              width: 20,
              height: 20
            })
          }),
          ...(count > 1 ? [new Style({
            text: new window.ol.style.Text({
              text: String(count),
              offsetX: 13,
              offsetY: -13,
              font: '700 12px sans-serif',
              fill: new Fill({
                color: '#ffffff'
              }),
              backgroundFill: new Fill({
                color: theme.getPropertyValue('--poc-teal').trim()
              }),
              padding: [2, 4, 2, 4],
            })
          })] : []),
        ]);
        return stopStyles.get(key);
      },
    }));
  }
  const stopMenu = document.createElement('div');
  stopMenu.className = 'map-stop-menu';
  stopMenu.setAttribute('role', 'group');
  stopMenu.setAttribute('aria-label', 'Stops at this location');
  const stopPopup = new window.ol.Overlay({
    element: stopMenu,
    positioning: 'bottom-center',
    offset: [0, -20],
    stopEvent: true
  });
  map.addOverlay(stopPopup);

  function inspectStops(grouped, coordinate) {
    stopMenu.replaceChildren();
    const close = document.createElement('button');
    close.textContent = 'Close';
    close.onclick = () => stopPopup.setPosition(undefined);
    stopMenu.append(close);
    for (const member of grouped) {
      const button = document.createElement('button');
      button.textContent = member.get('label');
      const original = member.get('sourceFeature');
      button.onclick = () => {
        if (original) onSelect(original);
        stopPopup.setPosition(undefined);
      };
      stopMenu.append(button);
    }
    stopPopup.setPosition(coordinate);
  }
  const shadeFeatures = new VectorSource();
  const shadeLayer = new VectorLayer({
    source: shadeFeatures,
    zIndex: 5,
    style: (feature) => {
      const state = feature.get('shadeState');
      return new Style({
        stroke: new Stroke({
          color: theme.getPropertyValue(state === 2 ? '--shade' : state === 1 ? '--exposed' : '--unknown').trim(),
          width: 7,
          lineDash: state === 2 ? undefined : state === 1 ? [12, 6] : [2, 6],
        })
      });
    },
  });
  map.addLayer(shadeLayer);
  const temperatureFeatures = new VectorSource();
  const temperatureLayer = new VectorLayer({
    source: temperatureFeatures,
    zIndex: 6,
    style: feature => new Style({
      stroke: new Stroke({
        color: feature.get('temperatureColour'),
        width: 8,
        lineDash: feature.get('temperatureSample') ? undefined : [2, 6]
      })
    })
  });
  map.addLayer(temperatureLayer);
  const coverageFeatures = new VectorSource();
  map.addLayer(new VectorLayer({
    source: coverageFeatures,
    zIndex: 2,
    style: new Style({
      stroke: new Stroke({
        color: theme.getPropertyValue('--unknown').trim(),
        width: 2,
        lineDash: [10, 6],
      })
    }),
  }));
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
      const grouped = feature.get('features');
      if (grouped) {
        if (grouped.length > 1 || !grouped[0].get('sourceFeature')) inspectStops(grouped, feature.getGeometry().getCoordinates());
        else onSelect(grouped[0].get('sourceFeature'));
        return true;
      }
      stopPopup.setPosition(undefined);
      if (feature.get('temperatureSample')) {
        onTemperatureSelect?.(feature.get('temperatureSample'));
        return true;
      }
      const selected = feature.get('sourceFeature') ?? features.get(String(feature.getId()));
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
          if (layer.kind === 'route' && shownRouteIds && !shownRouteIds.has(String(marker.getId()))) return undefined;
          const routeColor = marker.getId() === layer.features[1]?.id ? '--route-b' : '--route-a';
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
    setCoverage: (polygons) => {
      coverageFeatures.clear();
      polygons.forEach((polygon) => coverageFeatures.addFeature(new Feature({
        geometry: new GeoJSON().readGeometry(polygon, {
          dataProjection: 'EPSG:4326',
          featureProjection: 'EPSG:3857'
        }),
      })));
    },
    setShadeSamples: (routes, evidence) => {
      shadeFeatures.clear();
      evidence.forEach((item) => {
        const route = routes.find((route) => route.id === item.id);
        if (!route) return;
        const line = routeGeometry(route.geometry.coordinates);
        item.samples.forEach((sample) => {
          const start = sample.start_metres / item.distance_metres;
          const end = sample.end_metres / item.distance_metres;
          const middle = line.coordinates.filter((_, index) => line.cumulative[index] / line.length > start && line.cumulative[index] / line.length < end);
          const coordinates = [coordinateAtFraction(line, start), ...middle, coordinateAtFraction(line, end)];
          const feature = new Feature({
            geometry: new window.ol.geom.LineString(coordinates.map((point) => fromLonLat(point)))
          });
          feature.set('shadeState', sample.state);
          shadeFeatures.addFeature(feature);
        });
      });
    },
    updateSize: () => map.updateSize(),
    setPetVisible: (visible) => petLayer.setVisible(visible && !offline),
    setVisible: (id, visible) => layers.get(id)?.setVisible(visible),
    setRouteVisibility: ids => {
      shownRouteIds = new Set(ids);
      layers.forEach(layer => layer.changed());
    },
    setPins: (origin, destination) => {
      pinFeatures.clear();
      [
        [origin, 'origin'],
        [destination, 'destination']
      ].forEach(([place, kind]) => {
        if (!place) return;
        const marker = new Feature({
          geometry: new window.ol.geom.Point(fromLonLat([place.lon, place.lat])),
        });
        marker.set('pinKind', kind);
        pinFeatures.addFeature(marker);
      });
    },
    setContextMarkers: (markers) => {
      contextFeatures.clear();
      stopSources.forEach(source => source.clear());
      stopPopup.setPosition(undefined);
      markers.forEach((item) => {
        const marker = new Feature({
          geometry: new window.ol.geom.Point(fromLonLat(item.coordinates)),
        });
        marker.set('kind', item.kind);
        marker.set('label', item.label);
        marker.set('sourceFeature', item.sourceFeature);
        const stopKind = ['park', 'pause', 'rest'].includes(item.kind) ? 'rest' : item.kind;
        (stopSources.get(stopKind) ?? contextFeatures).addFeature(marker);
      });
    },
    setTemperatureProfile: (route, profile, colours, visible) => {
      temperatureFeatures.clear();
      temperatureLayer.setVisible(visible);
      if (!route || !visible) return;
      profile.segments.forEach((sample, index) => {
        const middle = route.coordinates.filter((_, vertex) => route.cumulative[vertex] / route.length > sample.start && route.cumulative[vertex] / route.length < sample.end);
        const coordinates = [coordinateAtFraction(route, sample.start), ...middle, coordinateAtFraction(route, sample.end)];
        const feature = new Feature({
          geometry: new window.ol.geom.LineString(coordinates.map(point => fromLonLat(point)))
        });
        feature.set('temperatureColour', colours[index]);
        feature.set('temperatureSample', sample.estimate);
        temperatureFeatures.addFeature(feature);
      });
    },
    setRoutePointDetails: (route, profile) => {
      if (!route || !profile?.segments?.length) return [];
      const step = Math.max(1, Math.ceil(profile.segments.length / MAX_VISIBLE_ROUTE_POINTS));
      return profile.segments.flatMap((sample, index) =>
        index % step === Math.floor(step / 2) % step || index === profile.segments.length - 1 ?
          [(sample.start + sample.end) / 2] : []
      );
    },
    getRoutePointPixel: (route, fraction) => {
      if (!route) return null;
      const point = coordinateAtFraction(route, fraction);
      return map.getPixelFromCoordinate(fromLonLat(point));
    },
    onViewChange: (callback) => {
      map.on(['moveend', 'change:size'], callback);
      return () => map.un(['moveend', 'change:size'], callback);
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
