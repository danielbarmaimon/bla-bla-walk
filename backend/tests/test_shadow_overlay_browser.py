"""T24 isolated OpenLayers display checks using actual pinned shade inputs."""

import base64
import importlib.util
import json
import shutil
from datetime import datetime

import pytest
from fastapi import Response
from rasterio.warp import transform

from bla_bla_walk import main
from bla_bla_walk.interfaces import ShadeRequest
from bla_bla_walk.shade_service import ROOT, ShadeService

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def real_cells(tmp_path_factory):
    """Install checksummed inputs separately; never replace existing local tiles."""
    root = tmp_path_factory.mktemp("t24-snapshot")
    spec = importlib.util.spec_from_file_location(
        "snapshot_installer", ROOT / "scripts/install_shade_snapshot.py"
    )
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    metadata = json.loads((ROOT / installer.SNAPSHOT).read_text())
    paths = [
        installer.SNAPSHOT,
        "data/prepared/" + metadata["archive"],
        *metadata["inputs"],
        "config/shade-service.json",
        "config/shade.json",
    ]
    for name in paths:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    assert installer.install(root) == len(metadata["files"])
    x, y = transform("EPSG:4326", "EPSG:2056", [7.588405], [47.556772])
    bounds = (x[0] - 15, y[0] - 15, x[0] + 15, y[0] + 15)
    service = ShadeService(root)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(main, "shade_service", service)

        def reject_network(*args, **kwargs):
            raise AssertionError("Shade endpoint must not contact providers")

        patch.setattr("httpx.HTTPTransport.handle_request", reject_network)
        replies = []
        for hour in (8, 14, 0):
            request = ShadeRequest(
                bounds=bounds,
                requested_time=datetime.fromisoformat(
                    f"2026-06-21T{hour:02}:00:00+02:00"
                ),
            )
            reply = main.shade_snapshot(request, Response()).model_dump(mode="json")
            assert reply["shade"]["requested_time"] == reply["shade"]["effective_time"]
            replies.append(reply)
    # Independent GDAL projection for every cell vertex of this bounded viewport.
    west, south, east, north = replies[0]["bounds"]
    vertices = [
        (x, y)
        for x in range(int(west), int(east) + 1)
        for y in range(int(south), int(north) + 1)
    ]
    xs, ys = transform(
        "EPSG:2056", "EPSG:3857", [p[0] for p in vertices], [p[1] for p in vertices]
    )
    projected = {
        f"{x},{y}": [px, py] for (x, y), px, py in zip(vertices, xs, ys, strict=True)
    }
    return replies, projected


def initialize(page, projected):
    page.goto(page.base_url)
    page.wait_for_function("Boolean(window.ol)")
    page.evaluate(
        """async points => {
      window.shadowModule = await import('/src/shadow-overlay.js');
      document.body.replaceChildren();
      const target = document.createElement('div'); target.style.height = '500px';
      const status = document.createElement('p'); status.id = 'shadow-status';
      document.body.append(target,status);
      window.shadowMap = new ol.Map({target,layers:[],view:new ol.View({
        center:ol.proj.fromLonLat([7.588405,47.556772]),zoom:20})});
      window.overlay = shadowModule.mountShadowOverlay(shadowMap, {
        visible:true, projectCoordinate:point => points[point.join(',')],
        onStatus:value => status.textContent = value.explanation});
    }""",
        projected,
    )


def test_actual_endpoint_cells_alignment_and_time_replacement(browser_page, real_cells):
    page = browser_page
    replies, projected = real_cells
    initialize(page, projected)
    assert replies[0]["counts"]["shaded"] > 0
    assert replies[1]["counts"]["shaded"] > 0
    assert replies[0]["states"] != replies[1]["states"]
    for response in replies[:2]:
        status = page.evaluate("reply => overlay.update(reply)", response)
        assert status["shade"] == response["shade"]
        assert status["model"] == response["model"]
        assert status["counts"] == response["counts"]
        features = page.evaluate("""overlay.layer.getSource().getFeatures().map(f => ({
          state:f.get('shadeState'),row:f.get('row'),column:f.get('column'),
          time:f.get('effectiveTime'),ring:f.getGeometry().getCoordinates()[0],
          pixels:f.getGeometry().getCoordinates()[0].map(
            p => shadowMap.getPixelFromCoordinate(p))
        }))""")
        features.sort(key=lambda feature: (feature["row"], feature["column"]))
        states = base64.b64decode(response["states"])
        assert len(features) == len(states)
        west, _, _, north = response["bounds"]
        size = response["shade"]["resolution_m"]
        for i, feature in enumerate(features):
            row, column = divmod(i, response["width"])
            assert (feature["row"], feature["column"]) == (row, column)
            assert feature["state"] == states[i]
            assert feature["time"] == response["shade"]["effective_time"]
            x, y = west + column * size, north - row * size
            ring = [(x, y), (x + size, y), (x + size, y - size), (x, y - size), (x, y)]
            for actual, vertex in zip(feature["ring"], ring, strict=True):
                assert actual == pytest.approx(
                    projected[f"{int(vertex[0])},{int(vertex[1])}"]
                )
            assert all(pixel is not None for pixel in feature["pixels"])
    screenshot = ROOT / ".hack/t24-overlay.png"
    screenshot.parent.mkdir(exist_ok=True)
    page.screenshot(path=str(screenshot))
    page.evaluate("overlay.dispose()")
    assert page.evaluate("shadowMap.getLayers().getLength()") == 0


def test_actual_night_unknown_and_visibility(browser_page, real_cells):
    page = browser_page
    replies, projected = real_cells
    initialize(page, projected)
    night = replies[2]
    assert night["counts"]["night"] > 0
    assert night["counts"]["unknown"] > 0
    assert night["counts"]["shaded"] == 0
    page.evaluate("reply => overlay.update(reply)", night)
    styles = page.evaluate("""() => {
      const f = overlay.layer.getSource().getFeatures();
      return [0,3].map(code => {
        const feature = f.find(v => v.get('shadeState') === code);
        const style = overlay.layer.getStyleFunction()(feature);
        return {label:feature.get('shadeLabel'),
          dash:style.getStroke().getLineDash()};
      });
    }""")
    assert styles[0]["dash"] != styles[1]["dash"]
    assert "Unknown" in styles[0]["label"]
    assert "Night" in styles[1]["label"]
    page.evaluate("overlay.setVisible(false)")
    assert not page.evaluate("overlay.layer.getVisible()")
    page.evaluate("overlay.setVisible(true)")
    assert page.evaluate("overlay.layer.getSource().getFeatures().length") == 961
    page.evaluate("overlay.update(null)")
    assert page.evaluate("overlay.layer.getSource().getFeatures().length") == 0
    assert "unavailable" in page.locator("#shadow-status").inner_text()


@pytest.mark.parametrize(
    "mutation",
    [
        "r.states = 'AQ=='",
        "r.states = '!!!!'",
        "r.crs = 'EPSG:4326'",
        "r.width = 100000",
        "r.bounds[0] += 1",
        "r.counts.shaded += 1",
        "r.availability = 'unsupported'",
        "r.shade.effective_time = 'bad'",
    ],
)
def test_invalid_input_clears_without_fallback(browser_page, real_cells, mutation):
    page = browser_page
    replies, projected = real_cells
    initialize(page, projected)
    result = page.evaluate(
        """({reply,mutation}) => {
      overlay.update(reply);
      const r = structuredClone(reply); eval(mutation);
      const status = overlay.update(r);
      return {status,count:overlay.layer.getSource().getFeatures().length};
    }""",
        {"reply": replies[0], "mutation": mutation},
    )
    assert result["status"]["availability"] == "unsupported"
    assert result["count"] == 0


def test_missing_projection_and_dispose(browser_page, real_cells):
    page = browser_page
    replies, projected = real_cells
    initialize(page, projected)
    result = page.evaluate(
        """reply => {
      overlay.dispose(); overlay.dispose();
      const missing = shadowModule.mountShadowOverlay(shadowMap);
      const status = missing.update(reply);
      const count = missing.layer.getSource().getFeatures().length;
      missing.dispose();
      return {status,count,layers:shadowMap.getLayers().getLength()};
    }""",
        replies[0],
    )
    assert result["status"]["availability"] == "unsupported"
    assert "projection transform" in result["status"]["explanation"]
    assert result["count"] == result["layers"] == 0


def test_unknown_cells_and_projection_failure_clear_shadows(browser_page, real_cells):
    """Explicit all-unknown response is display evidence, never replacement shade."""
    page = browser_page
    replies, projected = real_cells
    initialize(page, projected)
    unknown = json.loads(json.dumps(replies[0]))
    count = unknown["width"] * unknown["height"]
    unknown["states"] = base64.b64encode(bytes(count)).decode()
    unknown["counts"] = {"unknown": count, "sunlit": 0, "shaded": 0, "night": 0}
    unknown["availability"] = "unknown"
    unknown["explanation"] = "Test-only missing-input response; all cells unknown."
    result = page.evaluate(
        """reply => {
      overlay.update(reply);
      const states = overlay.layer.getSource().getFeatures().map(
        f => f.get('shadeState'));
      overlay.dispose();
      const invalid = shadowModule.mountShadowOverlay(shadowMap, {
        projectCoordinate:() => [NaN,NaN]});
      const status = invalid.update(reply);
      const count = invalid.layer.getSource().getFeatures().length;
      invalid.dispose();
      return {states,status,count};
    }""",
        unknown,
    )
    assert result["states"] == [0] * count
    assert result["status"]["availability"] == "unsupported"
    assert result["count"] == 0


def test_native_lv95_view_has_exact_bounds(browser_page, real_cells):
    page = browser_page
    replies, projected = real_cells
    initialize(page, projected)
    result = page.evaluate(
        """reply => {
      overlay.dispose();
      const projection = new ol.proj.Projection({code:'EPSG:2056',units:'m'});
      shadowMap.setView(new ol.View({projection,center:[2611273,1267350],zoom:20}));
      const native = shadowModule.mountShadowOverlay(shadowMap);
      const status = native.update(reply);
      const extent = native.layer.getSource().getExtent();
      native.dispose();
      return {status,extent};
    }""",
        replies[0],
    )
    assert result["status"]["availability"] == replies[0]["availability"]
    assert result["extent"] == replies[0]["bounds"]
