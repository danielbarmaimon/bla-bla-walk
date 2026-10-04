"""Icon markers retain members and regroup as map scale changes."""

import pytest

pytestmark = pytest.mark.browser


def test_stop_icons_clusters_and_inspection(browser_page):
    page = browser_page
    page.goto(page.base_url + "/?mode=fixture")
    result = page.evaluate("""async()=>{
      const NativeMap=ol.Map;
      let actual;
      ol.Map=class extends NativeMap{constructor(...args){super(...args);actual=this;}};
      const target=document.createElement('div');
      target.style.cssText='width:800px;height:600px'; document.body.append(target);
      const {createMap}=await import('/src/map.js?marker-test');
      let selected=null;
      const api=createMap(target,feature=>selected=feature.id,()=>{},()=>{},()=>{});
      api.setContextMarkers([
        {kind:'water',label:'Fountain one',coordinates:[7.5886,47.5596],
          sourceFeature:{id:'one'}},
        {kind:'water',label:'Fountain two',coordinates:[7.5892,47.5596],
          sourceFeature:{id:'two'}},
        {kind:'bench',label:'BENCH',coordinates:[7.59,47.56]},
        {kind:'rest',label:'REST 15m',coordinates:[7.591,47.56]},
      ]);
      actual.renderSync();
      const layers=actual.getLayers().getArray()
        .filter(l=>l.getSource() instanceof ol.source.Cluster);
      const water=layers[0];
      const cluster=water.getSource().getFeatures()[0];
      const anchor=ol.proj.toLonLat(cluster.getGeometry().getCoordinates());
      const icons=layers.map(l=>l.getStyle()(l.getSource().getFeatures()[0])[1]
        .getImage().getSrc());
      const before=water.getSource().getFeatures().length;
      const point=cluster.getGeometry().getCoordinates();
      actual.dispatchEvent({type:'singleclick',coordinate:point,
        pixel:actual.getPixelFromCoordinate(point)});
      const choices=target.querySelector('.map-stop-menu').textContent;
      [...target.querySelectorAll('.map-stop-menu button')]
        .find(b=>b.textContent==='Fountain two').click();
      actual.getView().setZoom(17); actual.renderSync();
      const after=water.getSource().getFeatures().length;
      api.setContextMarkers([]);actual.renderSync();
      return {before,after,anchor,icons,choices,selected,
        empty:water.getSource().getFeatures().length};
    }""")
    assert result["before"] == 1 and result["after"] == 2
    assert result["anchor"] == pytest.approx([7.5886, 47.5596])
    assert result["icons"] == [
        "/src/icons/droplets.svg",
        "/src/icons/rocking-chair.svg",
        "/src/icons/clock-fading.svg",
    ]
    assert "Fountain one" in result["choices"] and "Fountain two" in result["choices"]
    assert result["selected"] == "two" and result["empty"] == 0
