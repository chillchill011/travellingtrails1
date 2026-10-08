#!/usr/bin/env python3
"""Phase 6 deterministic generation validation, media injection and Markdown assembly."""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any

class Phase6Error(ValueError): pass

TOP_KEYS={"frontmatter","bodyMarkdown","imagePlan","reviewWarnings","missingInformation"}
FRONT_KEYS=["draft","featured","date","lastModified","title","description","author","destination","coordinates","duration","categories","travelType","rideMode","activities","tags","featuredImage","imageAlt","imageCredit","imageCreditLink","thumbnailImage","thumbnailAlt","thumbnailCredit","gallery","routeGallery","tripDetails","affiliateGallery","showTableOfContents","tocMinHeadings","layout"]

def _schema():
    text=(Path(__file__).with_name("schema.js")).read_text(encoding="utf-8")
    out={}
    for name in ["AUTHORS","CATEGORIES","TRAVEL_TYPES","RIDE_MODES","ACTIVITIES","TAGS","SEASONS","DIFFICULTY"]:
        m=re.search(rf"const {name}=(\[[^;]+\]);", text)
        if not m: raise Phase6Error(f"schema.js missing {name}")
        out[name]=json.loads(m.group(1))
    return out
SCHEMA=_schema()

def strict_json(content: str) -> dict[str,Any]:
    if not isinstance(content,str) or not content.strip(): raise Phase6Error("DeepSeek content is empty")
    if content.strip()!=content: raise Phase6Error("DeepSeek content must contain only one JSON object with no surrounding whitespace")
    if content.startswith("```") or content.endswith("```"): raise Phase6Error("Markdown fences are forbidden")
    try: value=json.loads(content)
    except Exception as exc: raise Phase6Error(f"DeepSeek content is not strict JSON: {exc}") from exc
    if not isinstance(value,dict): raise Phase6Error("DeepSeek output must be one JSON object")
    return value

def slugify(v: Any) -> str:
    import unicodedata
    s=unicodedata.normalize("NFKD",str(v or "")); s="".join(c for c in s if not unicodedata.combining(c)).lower().replace("&"," and ")
    s=re.sub(r"[^a-z0-9]+","-",s).strip("-"); return re.sub(r"-+","-",s)

def _scalar(v: Any) -> str:
    if v is None:return "null"
    if v is True:return "true"
    if v is False:return "false"
    if isinstance(v,(int,float)) and not isinstance(v,bool):return str(v)
    s=str(v); return '""' if s=="" else json.dumps(s,ensure_ascii=False,separators=(",",":"))

def _yaml_lines(obj: dict[str,Any], indent=0) -> list[str]:
    out=[]; pad=" "*indent
    for k,v in obj.items():
        if isinstance(v,list):
            if not v: out.append(f"{pad}{k}: []")
            else:
                out.append(f"{pad}{k}:")
                for item in v:
                    if isinstance(item,dict): out.append(f"{pad}  -"); out.extend(_yaml_lines(item,indent+4))
                    else: out.append(f"{pad}  - {_scalar(item)}")
        elif isinstance(v,dict):
            if not v: out.append(f"{pad}{k}: {{}}")
            else: out.append(f"{pad}{k}:"); out.extend(_yaml_lines(v,indent+2))
        else: out.append(f"{pad}{k}: {_scalar(v)}")
    return out

def serialize_markdown(frontmatter: dict[str,Any], body: str) -> str:
    return "---\n"+"\n".join(_yaml_lines(frontmatter))+"\n---\n\n"+body.strip()+"\n"

def _allowed(v, values, label, errors):
    if v not in values: errors.append(f"{label}: invalid value {v!r}")

def _paths_from_model(f):
    found=[]
    for key,role in (("featuredImage","featured"),("thumbnailImage","thumbnail")):
        if f.get(key): found.append((str(f[key]),role))
    for g in f.get("gallery") or []:
        if isinstance(g,dict) and g.get("src"): found.append((str(g["src"]),"gallery"))
    for g in f.get("routeGallery") or []:
        if isinstance(g,dict) and g.get("src"): found.append((str(g["src"]),"route"))
    return found

def validate_and_assemble(normalized: dict[str,Any], processed: dict[str,Any], generated: dict[str,Any]) -> dict[str,Any]:
    errors=[]
    if set(generated)!=TOP_KEYS: errors.append("top-level keys must exactly match Phase 1 contract")
    f=generated.get("frontmatter") if isinstance(generated.get("frontmatter"),dict) else {}
    unknown=set(f)-set(FRONT_KEYS)
    if unknown: errors.append("unknown frontmatter fields: "+", ".join(sorted(unknown)))
    trip=(normalized or {}).get("trip") or {}
    outputs=(processed or {}).get("outputs") or []
    if not isinstance(outputs,list) or not outputs: errors.append("processed image manifest is empty")
    by_role={}; path_role={}; source_roles={}
    for o in outputs:
        if not isinstance(o,dict): errors.append("invalid processed manifest entry"); continue
        p=str(o.get("publicPath") or ""); role=str(o.get("role") or ""); sid=str(o.get("sourceId") or "")
        if not p.startswith("/assets/images/") or ".." in p: errors.append(f"unsafe processed image path {p}")
        if p in path_role: errors.append(f"duplicate processed image path {p}")
        path_role[p]=role; by_role.setdefault(role,[]).append(o); source_roles.setdefault(sid,set()).add(role)
    if len(by_role.get("featured",[]))!=1: errors.append("processed manifest must contain exactly one featured derivative")
    if len(by_role.get("thumbnail",[]))!=1: errors.append("processed manifest must contain exactly one thumbnail derivative")
    for p,role in _paths_from_model(f):
        if p not in path_role: errors.append(f"unknown image path from model: {p}")
        elif path_role[p]!=role: errors.append(f"wrong image role/path from model: {p} is {path_role[p]}, not {role}")
    if f.get("draft") is not True: errors.append("draft must be true")
    if f.get("featured") is not False: errors.append("featured must be false")
    if f.get("date")!=trip.get("date"): errors.append("date must equal durable trip date")
    if f.get("author")!=trip.get("author"): errors.append("author must equal durable trip author")
    _allowed(f.get("author"),SCHEMA["AUTHORS"],"author",errors); _allowed(f.get("categories"),SCHEMA["CATEGORIES"],"categories",errors)
    for key,skey in (("travelType","TRAVEL_TYPES"),("rideMode","RIDE_MODES"),("activities","ACTIVITIES"),("tags","TAGS")):
        vals=f.get(key)
        if not isinstance(vals,list): errors.append(f"{key} must be array"); continue
        for v in vals:_allowed(v,SCHEMA[skey],key,errors)
    if not isinstance(f.get("tags"),list) or "post" not in f.get("tags",[]): errors.append("tags must include post")
    if f.get("layout")!="article.njk":errors.append("layout must be article.njk")
    if f.get("showTableOfContents") is not True:errors.append("showTableOfContents must be true")
    if f.get("tocMinHeadings")!=3:errors.append("tocMinHeadings must be 3")
    if not str(f.get("title") or "").strip():errors.append("title required")
    if not str(f.get("description") or "").strip():errors.append("description required")
    body=str(generated.get("bodyMarkdown") or "")
    if not body.strip():errors.append("bodyMarkdown required")
    if re.search(r"^---\s*$",body,re.M):errors.append("bodyMarkdown may not contain front matter delimiter")
    td=f.get("tripDetails") or {}; diff=(td.get("difficulty") or {}) if isinstance(td,dict) else {}
    if diff.get("overall") not in (None,""):_allowed(diff.get("overall"),SCHEMA["DIFFICULTY"],"difficulty.overall",errors)
    for k in ("physical","technical"):
        if k in diff and diff[k] not in (None,"") and (not isinstance(diff[k],int) or isinstance(diff[k],bool) or not 1<=diff[k]<=5):errors.append(f"difficulty.{k} must be integer 1..5")
    seasonal=(td.get("seasonal") or {}) if isinstance(td,dict) else {}; seasons=seasonal.get("bestSeason",[]) if isinstance(seasonal,dict) else []
    if not isinstance(seasons,list):errors.append("seasonal.bestSeason must be array")
    else:
        for v in seasons:_allowed(v,SCHEMA["SEASONS"],"seasonal.bestSeason",errors)
    if f.get("affiliateGallery") not in ([],None): errors.append("affiliateGallery is not allowed without explicit durable input")
    plans=generated.get("imagePlan")
    if not isinstance(plans,list):errors.append("imagePlan must be array"); plans=[]
    plan_index={}
    for p in plans:
        if not isinstance(p,dict):errors.append("imagePlan entry must be object"); continue
        sid=str(p.get("sourceId") or ""); role=str(p.get("role") or "")
        if sid not in source_roles:errors.append(f"imagePlan unknown sourceId {sid}"); continue
        if role not in {"featured","thumbnail","gallery","route","unused"}:errors.append(f"imagePlan invalid role {role}"); continue
        if role!="unused" and role not in source_roles[sid]:errors.append(f"imagePlan role {role} not available for {sid}")
        plan_index[(sid,role)]=p
    def meta(o,role,key, fallback=""):
        p=plan_index.get((str(o.get("sourceId")),role))
        if p is None:
            candidates=[v for (sid,_),v in plan_index.items() if sid==str(o.get("sourceId"))]
            p=candidates[0] if candidates else {}
        return str((p or {}).get(key) or fallback or "").strip()
    def one(role): return by_role.get(role,[{}])[0] if by_role.get(role) else {}
    feat=one("featured"); thumb=one("thumbnail")
    image_alt=meta(feat,"featured","alt",f.get("imageAlt")); thumb_alt=meta(thumb,"thumbnail","alt",f.get("thumbnailAlt"))
    if feat and not image_alt:errors.append("featured image alt text missing; image was not visually inspected")
    if thumb and not thumb_alt:errors.append("thumbnail alt text missing; image was not visually inspected")
    gallery=[]
    for o in by_role.get("gallery",[]):
        alt=meta(o,"gallery","alt")
        if not alt:errors.append(f"gallery alt missing for {o.get('publicPath')}")
        item={"src":o.get("publicPath"),"alt":alt}; cap=meta(o,"gallery","caption"); loc=meta(o,"gallery","location")
        if cap:item["caption"]=cap
        if loc:item["location"]=loc
        gallery.append(item)
    route=[]
    for o in by_role.get("route",[]):
        alt=meta(o,"route","alt")
        if not alt:errors.append(f"route alt missing for {o.get('publicPath')}")
        route.append({"src":o.get("publicPath"),"alt":alt})
    fixed={k:f.get(k) for k in FRONT_KEYS}
    fixed["featuredImage"]=feat.get("publicPath",""); fixed["thumbnailImage"]=thumb.get("publicPath","")
    fixed["imageAlt"]=image_alt; fixed["thumbnailAlt"]=thumb_alt; fixed["gallery"]=gallery; fixed["routeGallery"]=route
    for k in ("reviewWarnings","missingInformation"):
        if not isinstance(generated.get(k),list):errors.append(f"{k} must be array")
    serialized=json.dumps(generated,ensure_ascii=False,separators=(",",":"))
    if "data:image" in serialized or "contentBase64" in serialized:errors.append("generated content contains image/base64 data")
    front_serialized=json.dumps(fixed,ensure_ascii=False)
    if any(x in front_serialized for x in ("/home/","/data/","../","\\\\")):errors.append("frontmatter contains local/unsafe filesystem path")
    if errors:return {"ok":False,"errors":errors}
    title_slug=slugify(fixed["title"])
    if not title_slug:return {"ok":False,"errors":["title produces empty slug"]}
    post_path=f"src/blog/{trip['date']}-{title_slug}.md"
    markdown=serialize_markdown(fixed,body)
    return {"ok":True,"errors":[],"frontmatter":fixed,"generated":generated,"postPath":post_path,"markdown":markdown}
