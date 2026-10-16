"""Inject city_geo.json + results_city.json into the console template -> console_city.html."""
import os, json
HERE=os.path.dirname(__file__)
tpl=open(os.path.join(HERE,"console_city_tpl.html")).read()
geo=json.load(open(os.path.join(HERE,"city_geo.json")))
res=json.load(open(os.path.join(HERE,"results_city.json")))
# trim geo: keep only fields the console uses (sites lon/lat/op/opfull/cap/muni/src/top-ish, muni geometry+name)
top=set(x["op"] for x in res["s1_single_backend"])
sites=[{"lid":s["lid"],"op":s["op"],"opfull":s["opfull"],"lon":s["lon"],"lat":s["lat"],
        "cap":s["cap"],"muni":None,"top":s["opfull"] in top} for s in geo["geo"]["sites"]]
# muni membership for each site: point-in-polygon
import shapely.geometry as sg
polys=[(m["properties"].get("nommuni"),sg.shape(m["geometry"])) for m in geo["geo"]["muni"]]
for s in sites:
    pt=sg.Point(s["lon"],s["lat"])
    s["muni"]=next((nm for nm,poly in polys if poly.contains(pt)),None)
GEO={"geo":{"sites":sites,"muni":geo["geo"]["muni"]}}
RES={"operators":res["operators"][:12],"s1_single_backend":res["s1_single_backend"],
     "s2_campaign":res["s2_campaign"],"city":res["city"]}
out=tpl.replace("/*__GEO__*/","const GEO="+json.dumps(GEO,ensure_ascii=False,separators=(",",":"))+";")
out=out.replace("/*__RES__*/","const RES="+json.dumps(RES,ensure_ascii=False,separators=(",",":"))+";")
open(os.path.join(HERE,"console_city.html"),"w").write(out)
print(f"[BUILT] console_city.html ({os.path.getsize(os.path.join(HERE,'console_city.html'))/1024:.0f} KB) · sites={len(sites)} · muni={len(GEO['geo']['muni'])}")
