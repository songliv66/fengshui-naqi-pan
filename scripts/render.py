#!/usr/bin/env python3
"""Deterministic red/blue sector overlay. Original public implementation, MIT."""
import argparse
import base64
import hashlib
import html
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import shutil

VERSION = "1.0.0"
SECTORS = [(1, "blue"), (8, "red"), (3, "blue"), (4, "blue"),
           (9, "red"), (2, "blue"), (7, "red"), (6, "red")]
COLORS = {"red": "#df5965", "blue": "#4a87cf"}
EPS = 1e-8


def number(v, name):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f"{name} must be a finite number")
    return float(v)


def point(v, name):
    if not isinstance(v, list) or len(v) != 2:
        raise ValueError(f"{name} must be [x,y]")
    return [number(v[0], name), number(v[1], name)]


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def on_segment(p, a, b):
    return abs(cross(a, b, p)) < EPS and min(a[0], b[0])-EPS <= p[0] <= max(a[0], b[0])+EPS and min(a[1], b[1])-EPS <= p[1] <= max(a[1], b[1])+EPS


def intersects(a, b, c, d):
    u, v, w, z = cross(a,b,c), cross(a,b,d), cross(c,d,a), cross(c,d,b)
    if ((u > EPS and v < -EPS) or (u < -EPS and v > EPS)) and ((w > EPS and z < -EPS) or (w < -EPS and z > EPS)):
        return True
    return any((abs(k) < EPS and on_segment(p, x, y)) for k,p,x,y in [(u,c,a,b),(v,d,a,b),(w,a,c,d),(z,b,c,d)])


def contains(p, poly):
    inside = False
    for a,b in zip(poly, poly[1:]+poly[:1]):
        if on_segment(p,a,b):
            return True
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if p[0] < x:
                inside = not inside
    return inside


def centroid(poly):
    terms = [a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])]
    area2 = sum(terms)
    if abs(area2) < EPS:
        raise ValueError("outline has zero area")
    x = sum((a[0]+b[0])*v for a,b,v in zip(poly,poly[1:]+poly[:1],terms))/(3*area2)
    y = sum((a[1]+b[1])*v for a,b,v in zip(poly,poly[1:]+poly[:1],terms))/(3*area2)
    return [x,y], abs(area2)/2


def outward(direction, name):
    if not isinstance(direction, dict) or set(direction) != {"degrees", "sense"}:
        raise ValueError(f"{name} requires degrees and sense")
    a = number(direction["degrees"], name)
    if not 0 <= a < 360:
        raise ValueError(f"{name} degrees must be in [0,360)")
    if direction["sense"] not in ("inward", "outward"):
        raise ValueError(f"{name} sense must be inward or outward")
    return (a+(180 if direction["sense"] == "inward" else 0)) % 360


def classify(p, center, rotation, north, tolerance):
    dx,dy = p[0]-center[0],p[1]-center[1]
    if math.hypot(dx,dy) < EPS:
        return {"sector":None,"color":None,"status":"at_center","boundary_distance_deg":None}
    bearing = (math.degrees(math.atan2(dx,-dy))-north) % 360
    local = (bearing-rotation) % 360
    index = int(math.floor((local+22.5)/45)) % 8
    distance = abs(((local+22.5) % 45)-22.5)
    boundary = 22.5-distance
    return {"sector":SECTORS[index][0],"color":SECTORS[index][1],
            "status":"boundary_review" if boundary <= tolerance+EPS else "classified",
            "true_bearing_deg":round(bearing,6),"boundary_distance_deg":round(boundary,6)}


def no_duplicates(pairs):
    result={}
    for k,v in pairs:
        if k in result:
            raise ValueError(f"duplicate JSON key: {k}")
        result[k]=v
    return result


def read_spec(path):
    if path.stat().st_size > 2_000_000:
        raise ValueError("input JSON exceeds 2 MB")
    return json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=no_duplicates)


def validate(spec):
    if not isinstance(spec,dict):
        raise ValueError("input must be a JSON object")
    allowed={"title","image","canvas","outline","north_angle","building_direction","unit_direction","direction_status","center_mode","main_rectangle","center","center_reason","markers","boundary_tolerance_deg","opacity","crop","font"}
    if set(spec)-allowed:
        raise ValueError("unknown input keys: "+", ".join(sorted(set(spec)-allowed)))
    required={"image","canvas","outline","north_angle","building_direction","unit_direction","direction_status","center_mode","center_reason"}
    if required-set(spec):
        raise ValueError("missing input keys: "+", ".join(sorted(required-set(spec))))
    w,h=point(spec["canvas"],"canvas")
    if w != int(w) or h != int(h) or min(w,h)<100 or max(w,h)>10000 or w*h>40_000_000:
        raise ValueError("canvas must contain integer dimensions: 100..10000, at most 40M pixels")
    if not isinstance(spec["image"],str) or not spec["image"]:
        raise ValueError("image must be a raster file path")
    poly=spec["outline"]
    if not isinstance(poly,list) or not 3 <= len(poly) <= 500:
        raise ValueError("outline needs 3..500 vertices; holes/multiple rings are unsupported")
    poly=[point(p,"outline vertex") for p in poly]
    if len({tuple(p) for p in poly}) != len(poly):
        raise ValueError("outline repeats a vertex; do not repeat the closing vertex")
    if any(not (0<=x<=w and 0<=y<=h) for x,y in poly):
        raise ValueError("outline vertex outside canvas")
    n=len(poly)
    for i in range(n):
        a,b=poly[i],poly[(i+1)%n]
        if abs(cross(poly[i-1],a,b)) < EPS:
            raise ValueError("remove redundant collinear outline vertices")
        for j in range(i+1,n):
            if j == i+1 or (i==0 and j==n-1):
                continue
            if intersects(a,b,poly[j],poly[(j+1)%n]):
                raise ValueError("outline self-intersects")
    geometric_center,area=centroid(poly)
    north=number(spec["north_angle"],"north_angle")
    if not 0<=north<360:
        raise ValueError("north_angle must be in [0,360)")
    building=outward(spec["building_direction"],"building_direction")
    unit=outward(spec["unit_direction"],"unit_direction")
    rotation=(unit-building+180)%360-180
    if spec["direction_status"] not in ("measured","approximate","scenario"):
        raise ValueError("direction_status must be measured, approximate or scenario; unknown angles cannot produce a pan")
    if not isinstance(spec["center_reason"],str) or not spec["center_reason"].strip():
        raise ValueError("center_reason is required")
    mode=spec["center_mode"]
    rect=None
    if mode=="main_rectangle":
        v=spec.get("main_rectangle")
        if not isinstance(v,list) or len(v)!=4:
            raise ValueError("main_rectangle requires [left,top,right,bottom]")
        l,t,r,b=[number(x,"main_rectangle") for x in v]
        if not l<r or not t<b:
            raise ValueError("main_rectangle has invalid bounds")
        rect=[[l,t],[r,t],[r,b],[l,b]]
        # Every rectangle edge is partitioned at polygon vertices; midpoints must stay inside.
        for a,z in zip(rect,rect[1:]+rect[:1]):
            cuts=[0.0,1.0]
            rx,ry=z[0]-a[0],z[1]-a[1]
            for p,q in zip(poly,poly[1:]+poly[:1]):
                sx,sy=q[0]-p[0],q[1]-p[1]
                denominator=rx*sy-ry*sx
                qx,qy=p[0]-a[0],p[1]-a[1]
                if abs(denominator)>EPS:
                    tcut=(qx*sy-qy*sx)/denominator
                    ucut=(qx*ry-qy*rx)/denominator
                    if -EPS<=tcut<=1+EPS and -EPS<=ucut<=1+EPS:
                        cuts.append(max(0.0,min(1.0,tcut)))
                elif abs(qx*ry-qy*rx)<EPS:
                    for endpoint in (p,q):
                        tcut=((endpoint[0]-a[0])*rx+(endpoint[1]-a[1])*ry)/(rx*rx+ry*ry)
                        if 0<=tcut<=1: cuts.append(tcut)
            cuts=sorted(set(cuts))
            samples=cuts+[(u+v)/2 for u,v in zip(cuts,cuts[1:])]
            if any(not contains([a[0]+s*(z[0]-a[0]),a[1]+s*(z[1]-a[1])],poly) for s in samples):
                raise ValueError("main_rectangle must lie within outline; do not use an outer bounding box for a concave plan")
        center=[(l+r)/2,(t+b)/2]
    elif mode=="centroid":
        center=geometric_center
    elif mode=="explicit":
        center=point(spec.get("center"),"center")
        if not contains(center,poly):
            raise ValueError("explicit center must lie within outline")
    else:
        raise ValueError("center_mode must be main_rectangle, centroid or explicit")
    tol=number(spec.get("boundary_tolerance_deg",3),"boundary tolerance")
    opacity=number(spec.get("opacity",0.28),"opacity")
    if not 0<=tol<=22.5 or not 0<=opacity<=0.7:
        raise ValueError("tolerance must be 0..22.5; opacity must be 0..0.7")
    markers=spec.get("markers",[])
    if not isinstance(markers,list) or len(markers)>500:
        raise ValueError("markers must be a list of at most 500 items")
    labels=set(); output=[]
    for marker in markers:
        if not isinstance(marker,dict) or set(marker)!={"label","xy","kind"}:
            raise ValueError("each marker requires label, xy and kind")
        label=marker["label"]
        if not isinstance(label,str) or not 1<=len(label)<=80 or label in labels or any(ord(c)<32 or ord(c)==127 for c in label):
            raise ValueError("marker labels must be unique strings of 1..80 characters without control characters")
        labels.add(label)
        if marker["kind"] not in ("entrance","window","head","drain","other"):
            raise ValueError("invalid marker kind")
        p=point(marker["xy"],"marker.xy")
        if not contains(p,poly):
            raise ValueError(f"marker outside outline: {label}")
        output.append({"label":label,"xy":p,"kind":marker["kind"],**classify(p,center,rotation,north,tol)})
    crop=spec.get("crop",[0,0,w,h])
    if not isinstance(crop,list) or len(crop)!=4:
        raise ValueError("crop requires [x,y,width,height]")
    crop=[number(v,"crop") for v in crop]
    x,y,cw,ch=crop
    if min(x,y)<0 or min(cw,ch)<=0 or x+cw>w or y+ch>h or any(v!=int(v) for v in crop):
        raise ValueError("crop must be positive integer bounds within canvas")
    title=spec.get("title","Naqi plan")
    if not isinstance(title,str) or len(title)>120:
        raise ValueError("title must be a string up to 120 characters")
    warnings=[]
    if spec["direction_status"]!="measured":
        warnings.append("Directions are scenarios/approximate; this is not a field measurement.")
    if not contains(center,poly):
        warnings.append("Area centroid lies outside the concave outline; review the chosen center convention.")
    if any(m["status"]=="boundary_review" for m in output):
        warnings.append("At least one marker is near a sector boundary. Check direction and coordinates.")
    for m in output:
        mx,my=m["xy"]
        m["visible_in_crop"]=(x<=mx<=x+cw and y<=my<=y+ch)
        if m["visible_in_crop"] and min(mx-x,x+cw-mx,my-y,y+ch-my)<8:
            warnings.append(f'Crop boundary annotation inset with leader; geometry unchanged: {m["label"]}')
        elif not m["visible_in_crop"]:
            warnings.append(f'Marker outside display crop; retained in JSON/HTML table: {m["label"]}')
    return {"canvas":[int(w),int(h)],"outline":poly,"center":center,"area_px2":area,"rectangle":rect,"rotation_deg":rotation,"north_angle":north,"building_outward_deg":building,"unit_outward_deg":unit,"markers":output,"boundary_tolerance_deg":tol,"opacity":opacity,"crop":[int(v) for v in crop],"warnings":warnings}


def wedge(center, angle, radius):
    values=[angle-22.5+i*45/90 for i in range(91)]
    return [center]+[[center[0]+radius*math.sin(math.radians(a)),center[1]-radius*math.cos(math.radians(a))] for a in values]


def points(poly):
    return " ".join(f"{x:.5f},{y:.5f}" for x,y in poly)


def marker_layout(marker,crop,width):
    """Keep the annotation inside a display crop; source coordinates never move."""
    x,y=marker["xy"];left,top,w,h=crop;right,bottom=left+w,top+h
    if not left<=x<=right or not top<=y<=bottom:
        return None
    dot_x=max(left+7,min(x,right-7));dot_y=max(top+7,min(y,bottom-7))
    tx=dot_x+9
    if tx+width>right-8: tx=dot_x-9-width
    tx=max(left+8,min(tx,right-width-8))
    ty=max(top+8,min(dot_y-25,bottom-24))
    return dot_x,dot_y,tx,ty


def svg_document(spec,result,png_bytes):
    w,h=result["canvas"]; cx,cy=result["center"]; north=result["north_angle"]
    view=" ".join(str(v) for v in result["crop"][:3]+[result["crop"][3]+120])
    crop_w,crop_h=result["crop"][2:]
    image=base64.b64encode(png_bytes).decode()
    r=math.hypot(w,h)*2
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{crop_w}" height="{crop_h+120}" viewBox="{view}" role="img" aria-label="{html.escape(spec.get("title","Naqi plan"),quote=True)}">',f'<defs><clipPath id="floor"><polygon points="{points(result["outline"])}"/></clipPath></defs>',f'<image width="{w}" height="{h}" xlink:href="data:image/png;base64,{image}"/>',f'<g id="sectors" clip-path="url(#floor)" opacity="{result["opacity"]}">']
    for i,(num,color) in enumerate(SECTORS):
        angle=i*45+result["rotation_deg"]+north
        parts.append(f'<polygon points="{points(wedge([cx,cy],angle,r))}" fill="{COLORS[color]}"/>')
    parts.append('</g><g font-family="sans-serif" font-size="16" stroke-linejoin="round">')
    for i in range(8):
        a=math.radians(i*45+22.5+result["rotation_deg"]+north)
        parts.append(f'<path d="M{cx},{cy} L{cx+r*math.sin(a)},{cy-r*math.cos(a)}" stroke="#344054" stroke-width="1" stroke-dasharray="5 6" clip-path="url(#floor)" opacity="0.6"/>')
    if result["rectangle"]:
        parts.append(f'<polygon points="{points(result["rectangle"])}" fill="none" stroke="#087f6e" stroke-width="3" stroke-dasharray="8 6"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="white" stroke="#111827" stroke-width="2"/><text x="{cx+10}" y="{cy-10}" fill="#111827" stroke="white" stroke-width="4" paint-order="stroke">C</text>')
    ring=min(w,h)*0.19
    for i,(num,color) in enumerate(SECTORS):
        a=math.radians(i*45+result["rotation_deg"]+north)
        x,y=cx+ring*math.sin(a),cy-ring*math.cos(a)
        if contains([x,y],result["outline"]):
            parts.append(f'<circle cx="{x}" cy="{y}" r="13" fill="white" fill-opacity="0.9"/><text x="{x}" y="{y+5}" text-anchor="middle" fill="{COLORS[color]}" font-weight="bold">{num}</text>')
    # User labels are painted after sector circles so numbers cannot obscure them.
    for m in result["markers"]:
        width=sum(10 if ord(c)<128 else 18 for c in m["label"])
        layout=marker_layout(m,result["crop"],width)
        if layout is None: continue
        x,y=m["xy"];dx,dy,tx,ty=layout
        fill="#f59e0b" if m["status"]=="boundary_review" else "#111827"
        parts.append(f'<path d="M{x} {y} L{dx} {dy}" stroke="#111827" stroke-width="1"/><circle cx="{dx}" cy="{dy}" r="5" fill="{fill}" stroke="white" stroke-width="2"/><text x="{tx}" y="{ty+16}" fill="#111827" stroke="white" stroke-width="4" paint-order="stroke">{html.escape(m["label"])}</text>')
    panel_x,panel_y=result["crop"][0],result["crop"][1]+crop_h
    parts.append(f'<rect x="{panel_x}" y="{panel_y}" width="{crop_w}" height="120" fill="white"/>')
    for index,(name,angle) in enumerate([("True N",north),("Building OUT",result["building_outward_deg"]+north),("Unit OUT",result["unit_outward_deg"]+north)]):
        x,y=panel_x+crop_w*(index+0.5)/3,panel_y+43
        a=math.radians(angle);ex,ey=x+24*math.sin(a),y-24*math.cos(a)
        parts.append(f'<circle cx="{x}" cy="{y}" r="28" fill="none" stroke="#d0d5dd"/><path d="M{x} {y} L{ex} {ey}" stroke="#182230" stroke-width="3"/>')
        tip=[[ex,ey],[ex-10*math.sin(a-0.5),ey+10*math.cos(a-0.5)],[ex-10*math.sin(a+0.5),ey+10*math.cos(a+0.5)]]
        parts.append(f'<polygon points="{points(tip)}" fill="#182230"/><text x="{x}" y="{panel_y+91}" text-anchor="middle" font-size="14">{name} / {(angle-north)%360:g} deg</text>')
    parts.append(f'<text x="{panel_x+crop_w/2}" y="{panel_y+113}" text-anchor="middle" font-size="12">Direction key only; arrow positions are not surveyed door coordinates.</text>')
    return "\n".join(parts+["</g></svg>"])


def render_png(spec,result,background,font_path):
    from PIL import Image,ImageDraw,ImageFont,ImageChops
    base=background.convert("RGBA"); w,h=base.size
    font=ImageFont.truetype(str(font_path),16) if font_path else ImageFont.load_default(size=16)
    labels=[m["label"] for m in result["markers"]]
    if not font_path and any(any(ord(c)>127 for c in v) for v in labels):
        raise ValueError("PNG labels outside ASCII require --font or spec.font with a licensed font file")
    layer=Image.new("RGBA",base.size); draw=ImageDraw.Draw(layer)
    for i,(_,color) in enumerate(SECTORS):
        draw.polygon([tuple(p) for p in wedge(result["center"],i*45+result["rotation_deg"]+result["north_angle"],math.hypot(w,h)*2)],fill=COLORS[color])
    mask=Image.new("L",base.size); ImageDraw.Draw(mask).polygon([tuple(p) for p in result["outline"]],fill=round(255*result["opacity"]))
    layer.putalpha(mask); base=Image.alpha_composite(base,layer); draw=ImageDraw.Draw(base)
    cx,cy=result["center"]
    for i in range(8):
        a=math.radians(i*45+22.5+result["rotation_deg"]+result["north_angle"])
        line=Image.new("RGBA",base.size); ld=ImageDraw.Draw(line)
        ld.line([(cx,cy),(cx+math.hypot(w,h)*2*math.sin(a),cy-math.hypot(w,h)*2*math.cos(a))],fill="#536273",width=1)
        line.putalpha(ImageChops.multiply(line.getchannel("A"),mask.point(lambda v: 255 if v else 0)))
        base=Image.alpha_composite(base,line)
    draw=ImageDraw.Draw(base)
    if result["rectangle"]:
        draw.line([tuple(p) for p in result["rectangle"]+result["rectangle"][:1]],fill="#087f6e",width=3)
    draw.ellipse((cx-7,cy-7,cx+7,cy+7),fill="white",outline="#111827",width=2)
    draw.text((cx+10,cy-27),"C",font=font,fill="#111827",stroke_width=2,stroke_fill="white")
    ring=min(w,h)*0.19
    for i,(num,color) in enumerate(SECTORS):
        a=math.radians(i*45+result["rotation_deg"]+result["north_angle"])
        x,y=cx+ring*math.sin(a),cy-ring*math.cos(a)
        if contains([x,y],result["outline"]):
            draw.ellipse((x-13,y-13,x+13,y+13),fill="white")
            draw.text((x,y),str(num),anchor="mm",font=font,fill=COLORS[color])
    # Last paint stage keeps marker text above the numbered sector circles.
    for m in result["markers"]:
        bbox=font.getbbox(m["label"]);width=bbox[2]-bbox[0]
        layout=marker_layout(m,result["crop"],width)
        if layout is None: continue
        x,y=m["xy"];dx,dy,tx,ty=layout
        fill="#f59e0b" if m["status"]=="boundary_review" else "#111827"
        draw.line([(x,y),(dx,dy)],fill="#111827",width=1)
        draw.ellipse((dx-5,dy-5,dx+5,dy+5),fill=fill,outline="white",width=2)
        draw.text((tx,ty),m["label"],font=font,fill="#111827",stroke_width=2,stroke_fill="white")
    x,y,cw,ch=result["crop"]
    cropped=base.crop((x,y,x+cw,y+ch)).convert("RGB")
    output=Image.new("RGB",(cw,ch+120),"white");output.paste(cropped,(0,0))
    pd=ImageDraw.Draw(output);panel_font=ImageFont.load_default(size=14);tiny=ImageFont.load_default(size=12)
    for index,(name,angle) in enumerate([("True N",result["north_angle"]),("Building OUT",result["building_outward_deg"]+result["north_angle"]),("Unit OUT",result["unit_outward_deg"]+result["north_angle"])]):
        px,py=cw*(index+0.5)/3,ch+43;a=math.radians(angle)
        ex,ey=px+24*math.sin(a),py-24*math.cos(a)
        pd.ellipse((px-28,py-28,px+28,py+28),outline="#d0d5dd",width=1)
        pd.line([(px,py),(ex,ey)],fill="#182230",width=3)
        pd.polygon([(ex,ey),(ex-10*math.sin(a-0.5),ey+10*math.cos(a-0.5)),(ex-10*math.sin(a+0.5),ey+10*math.cos(a+0.5))],fill="#182230")
        pd.text((px,ch+81),f'{name} / {(angle-result["north_angle"])%360:g} deg',anchor="mt",font=panel_font,fill="#182230")
    pd.text((cw/2,ch+103),"Direction key only; arrows are not surveyed door coordinates.",anchor="mt",font=tiny,fill="#475467")
    return output


def generate(spec_path,out,previous=None,font_override=None):
    if out.exists():
        raise ValueError("output directory already exists; choose a new directory")
    spec=read_spec(spec_path); result=validate(spec)
    from PIL import Image
    image_path=Path(spec["image"])
    if not image_path.is_absolute(): image_path=spec_path.parent/image_path
    if image_path.suffix.lower() not in (".png",".jpg",".jpeg"):
        raise ValueError("input raster must be PNG/JPG/JPEG; export SVG/PDF to raster first")
    if image_path.stat().st_size>80_000_000: raise ValueError("input raster exceeds 80 MB")
    try:
        with Image.open(image_path) as original:
            if original.size!=tuple(result["canvas"]): raise ValueError("canvas does not match the original raster dimensions")
            original.load(); background=original.convert("RGB")
    except Image.DecompressionBombError as e:
        raise ValueError("raster dimensions exceed safe limit; use at most 40M pixels") from e
    buf=io.BytesIO(); background.save(buf,format="PNG"); data=buf.getvalue()
    font_path=font_override or spec.get("font")
    if font_path:
        font_path=Path(font_path)
        if not font_path.is_absolute():
            font_path=(Path.cwd() if font_override else spec_path.parent)/font_path
        if not font_path.is_file(): raise ValueError("configured font file is missing")
    png=render_png(spec,result,background,font_path)
    safe_spec={k:v for k,v in spec.items() if k not in ("image","font")}
    source_hash=hashlib.sha256(image_path.read_bytes()).hexdigest()
    fingerprint=hashlib.sha256(json.dumps(safe_spec,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()+source_hash.encode()).hexdigest()
    result.update({"tool_version":VERSION,"input_fingerprint":fingerprint,"source_image_sha256":source_hash,"source_image_name":image_path.name,"center_mode":spec["center_mode"],"center_reason":spec["center_reason"],"direction_status":spec["direction_status"],"parameters":safe_spec,"scope":"Geometric classification only; red/blue meaning is a traditional convention, not a validated prediction."})
    if previous:
        old=json.loads(previous.read_text())
        changed=[k for k in sorted(set(old.get("parameters",{}))|set(safe_spec)) if old.get("parameters",{}).get(k)!=safe_spec.get(k)]
        if old.get("source_image_sha256")!=source_hash: changed.append("source_image_sha256")
        result["comparison"]={"previous_fingerprint":old.get("input_fingerprint"),"previous_conclusions_invalidated":old.get("input_fingerprint")!=fingerprint,"changed_inputs":changed}
    svg=svg_document(spec,result,data)
    rows="".join(f'<tr><td>{html.escape(m["label"])}</td><td>{m["sector"] or "center"}</td><td>{m["status"]}</td><td>{m["boundary_distance_deg"]}</td></tr>' for m in result["markers"])
    webpage=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{html.escape(spec.get("title","Naqi plan"))}</title><style>body{{font:16px system-ui;max-width:1100px;margin:24px auto;padding:0 20px;background:#f7f8fa;color:#182230}}svg{{width:100%;height:auto;background:white;border-radius:12px}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}.note{{line-height:1.7}}</style><h1>{html.escape(spec.get("title","Naqi plan"))}</h1><p class="note">Red: traditional naqi sectors 6/7/8/9. Blue: traditional water sectors 1/2/3/4. C: selected center. Amber dots: boundary review. Numbers are rotated sector IDs, not true compass directions.</p><label>Overlay opacity <input type="range" id="opacity" min="0" max="0.7" step="0.01" value="{result["opacity"]}"></label>{svg}<p class="note">Rotation: {result["rotation_deg"]} degrees. Center: {result["center"]}. Direction status: {result["direction_status"]}. Cropping changes the display only.</p><table><thead><tr><th>Marker</th><th>Sector</th><th>Status</th><th>Degrees to boundary</th></tr></thead><tbody>{rows}</tbody></table><p class="note">Every change to direction, outline, head position or center requires a new calculation. The previous interpretation is not transferable. Traditional sectors do not establish health, wealth or business outcomes.</p><p>Fingerprint: <code>{fingerprint}</code></p><script>document.getElementById('opacity').addEventListener('input',e=>document.getElementById('sectors').setAttribute('opacity',e.target.value));</script></html>'''
    report=f'# {spec.get("title","Naqi plan")}\n\nTool-generated geometry record; interpretive demo commentary is separately labelled.\n\n- Center convention: {spec["center_mode"]}; C = {result["center"]}\n- Center basis: {spec["center_reason"]}\n- Outward directions: building {result["building_outward_deg"]}°, unit {result["unit_outward_deg"]}°\n- Rotation: {result["rotation_deg"]}°; north in image: {result["north_angle"]}°\n- Input status: {spec["direction_status"]}\n- Fingerprint: {fingerprint}\n\n|Marker|Kind|Sector|Color|Status|Boundary distance°|\n|---|---|---|---|---|---|\n'
    for m in result["markers"]:
        label=m["label"].replace("|","\\|").replace("\n"," ")
        report+=f'|{label}|{m["kind"]}|{m["sector"]}|{m["color"]}|{m["status"]}|{m["boundary_distance_deg"]}|\n'
    report+='\n'+''.join(f'- Review: {v}\n' for v in result["warnings"])
    report+='\nRed/blue is a traditional convention; these are not validated predictions. A seat in a red sector is only an overall candidate. A head-centered window/door check is a separate calculation. Real drains are marked individually. Recalculate after any input change; old conclusions expire.\n'
    out.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.naqi-',dir=out.parent))
    try:
        (temp/'overlay.svg').write_text(svg,encoding='utf-8')
        (temp/'overlay.html').write_text(webpage,encoding='utf-8')
        (temp/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (temp/'geometry.md').write_text(report,encoding='utf-8')
        png.save(temp/'overlay.png',format='PNG')
        # Exclusive mkdir protects against concurrent duplicate runs. All outputs were computed first.
        out.mkdir(exist_ok=False)
        try:
            for p in temp.iterdir(): shutil.move(str(p),out/p.name)
        except Exception:
            shutil.rmtree(out)
            raise
    finally:
        shutil.rmtree(temp,ignore_errors=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec',type=Path); parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--previous',type=Path,help='previous result.json; compare assumptions and invalidate old conclusions')
    parser.add_argument('--font',help='licensed font path for PNG labels outside ASCII')
    args=parser.parse_args()
    try:
        r=generate(args.spec,args.out,args.previous,args.font)
    except (ValueError,OSError,KeyError,TypeError,ImportError) as e:
        print(f'ERROR: {e}',file=sys.stderr)
        if isinstance(e,ImportError): print('Install dependencies: python3 -m pip install -r requirements.txt',file=sys.stderr)
        return 2
    print(f'Created {args.out}: SVG, PNG, HTML, JSON, Markdown; rotation={r["rotation_deg"]}°, fingerprint={r["input_fingerprint"][:12]}')
    return 0

if __name__=='__main__':
    sys.exit(main())
