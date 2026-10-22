#!/usr/bin/env python3
"""Draw original synthetic plans and run all deterministic examples."""
import argparse
import html
import json
from pathlib import Path
import shutil
import sys
from PIL import Image,ImageDraw,ImageFont
from render import generate

ROOT=Path(__file__).resolve().parents[1]


def draw_plan(path,shape,title,lines,objects):
    w,h=900,660
    image=Image.new('RGB',(w,h),'#f4f1e9'); d=ImageDraw.Draw(image)
    font=ImageFont.load_default(size=18)
    small=ImageFont.load_default(size=15)
    p=' '.join(f'{x},{y}' for x,y in shape)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="900" height="660" fill="#f4f1e9"/><g font-family="sans-serif" fill="#26333d">',f'<polygon points="{p}" fill="white" stroke="#26333d" stroke-width="6"/>']
    d.polygon(shape,fill='white',outline='#26333d',width=6)
    def text(x,y,value,size=18):
        d.text((x,y),value,font=font if size==18 else small,fill='#26333d')
        svg.append(f'<text x="{x}" y="{y+size}" font-size="{size}">{html.escape(value)}</text>')
    text(40,20,title)
    text(40,620,'SYNTHETIC / NOT TO SCALE / NO REAL ADDRESS',15)
    # True north arrow in all source plans points up; rotated-image tests rotate north separately.
    d.line((860,120,860,70),fill='#26333d',width=3);d.polygon([(860,60),(852,76),(868,76)],fill='#26333d');text(853,36,'N',15)
    svg.append('<path d="M860 120V70 M860 60L852 76H868Z" stroke="#26333d" fill="#26333d"/>')
    for a,b in lines:
        d.line([a,b],fill='#73808b',width=3);svg.append(f'<path d="M{a[0]} {a[1]} L{b[0]} {b[1]}" stroke="#73808b" stroke-width="3"/>')
    for x,y,ow,oh,label,color in objects:
        d.rounded_rectangle((x,y,x+ow,y+oh),radius=5,fill=color,outline='#7c8793',width=2)
        svg.append(f'<rect x="{x}" y="{y}" width="{ow}" height="{oh}" rx="5" fill="{color}" stroke="#7c8793" stroke-width="2"/>')
        text(x+8,y+9,label,15)
    svg.append('</g></svg>')
    path.with_suffix('.svg').write_text('\n'.join(svg),encoding='utf-8')
    image.save(path.with_suffix('.png'))


def marker(label,xy,kind): return {'label':label,'xy':xy,'kind':kind}


def write_specs(root):
    office=root/'01-office'; home=root/'02-home'; ambiguous=root/'03-ambiguous'
    for p in (office,home,ambiguous):p.mkdir(parents=True)
    rect=[[80,80],[820,80],[820,580],[80,580]]
    draw_plan(office/'source',rect,'01 / RECTANGULAR OFFICE', [((520,80),(520,250)),((520,440),(520,580))],[(165,180,205,75,'Desk A','#eef2f8'),(580,350,180,75,'Desk B','#eef2f8'),(705,480,95,55,'Sink','#e6f1ef'),(390,480,170,60,'Meeting','#f9eedb')])
    common={'image':'source.png','canvas':[900,660],'outline':rect,'north_angle':0,'building_direction':{'degrees':270,'sense':'outward'},'unit_direction':{'degrees':0,'sense':'inward'},'direction_status':'scenario','center_mode':'main_rectangle','main_rectangle':[80,80,820,580],'center_reason':'The complete rectangular office is the selected main rectangle. Synthetic coordinates, not site measurements.','markers':[marker('ENTRY',[740,580],'entrance'),marker('WIN-L',[180,80],'window'),marker('WIN-R',[350,80],'window'),marker('HEAD-A',[330,285],'head'),marker('HEAD-B',[630,450],'head'),marker('DRAIN',[800,530],'drain')]}
    common['title']='Rectangular office / overall pan';(office/'input.json').write_text(json.dumps(common,indent=2)+'\n')
    head={**common,'center_mode':'explicit','center':[330,285],'center_reason':'Head A position; same rotation as the overall pan. Window endpoints and entry are checked separately.','title':'Office / head A verification'}
    head.pop('main_rectangle');head['markers']=[v for v in common['markers'] if v['kind'] in ('entrance','window')];(office/'head-a.json').write_text(json.dumps(head,indent=2)+'\n')
    shape=[[80,80],[820,80],[820,360],[500,360],[500,580],[80,580]]
    draw_plan(home/'source',shape,'02 / SYNTHETIC L-SHAPED HOME',[((500,80),(500,360)),((80,360),(500,360)),((300,360),(300,580))],[(150,150,200,100,'Bed','#f5eadf'),(160,420,100,80,'Sofa','#eef2f8'),(590,140,170,70,'Kitchen','#e6f1ef'),(610,260,150,50,'Sink','#e6f1ef')])
    home_spec={**common,'title':'L-shaped home / selected main rectangle','outline':shape,'main_rectangle':[80,80,500,580],'building_direction':{'degrees':90,'sense':'outward'},'unit_direction':{'degrees':90,'sense':'outward'},'center_reason':'The complete left 420x500 rectangle is selected; the top-right extension is outside that rectangle. This is a declared convention, not a uniquely inferred rule.','markers':[marker('ENTRY',[80,440],'entrance'),marker('PILLOW-A',[205,170],'head'),marker('PILLOW-B',[290,170],'head'),marker('WIN-L',[130,80],'window'),marker('WIN-R',[350,80],'window'),marker('DRAIN',[760,280],'drain')]}
    (home/'input.json').write_text(json.dumps(home_spec,indent=2)+'\n')
    alternative={**home_spec,'title':'L-shaped home / explicit area-centroid alternative','center_mode':'centroid','center_reason':'User-selected whole-polygon area centroid. Kept separate from the main-rectangle method; conclusions must be recomputed.'};alternative.pop('main_rectangle');(home/'centroid.json').write_text(json.dumps(alternative,indent=2)+'\n')
    draw_plan(ambiguous/'source',rect,'03 / BOUNDARY AND DIRECTION SCENARIOS',[],[(150,400,170,90,'Desk','#eef2f8'),(580,160,170,100,'Open area','#f9eedb')])
    scenario={**common,'title':'Boundary / scenario A: unit outward 0 deg','building_direction':{'degrees':0,'sense':'outward'},'unit_direction':{'degrees':0,'sense':'outward'},'center_reason':'Same complete rectangle in both scenarios. Unit direction is unresolved; scenario values are not field measurements.','markers':[marker('ENTRY',[740,580],'entrance'),marker('EDGE-WIN',[532.84271247,130],'window'),marker('HEAD',[230,400],'head')]}
    (ambiguous/'input.json').write_text(json.dumps(scenario,indent=2)+'\n')
    changed={**scenario,'title':'Boundary / scenario B: unit outward 6 deg','unit_direction':{'degrees':6,'sense':'outward'}};(ambiguous/'direction-6.json').write_text(json.dumps(changed,indent=2)+'\n')


def run_all(example_root,out):
    if out.exists():raise ValueError('Demo output exists; choose a new directory')
    # All computations happen in an isolated staging directory before the complete suite is published.
    import tempfile
    out.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.naqi-demos-',dir=out.parent))
    try:
        for case in ('01-office','02-home','03-ambiguous'):
            source=example_root/case
            generate(source/'input.json',temp/case/'overall')
        generate(example_root/'01-office/head-a.json',temp/'01-office/head-a')
        generate(example_root/'02-home/centroid.json',temp/'02-home/area-centroid',temp/'02-home/overall/result.json')
        generate(example_root/'03-ambiguous/direction-6.json',temp/'03-ambiguous/direction-6',temp/'03-ambiguous/overall/result.json')
        out.mkdir(exist_ok=False)
        try:
            for p in temp.iterdir():shutil.move(str(p),out/p.name)
        except Exception:
            shutil.rmtree(out);raise
    finally:shutil.rmtree(temp,ignore_errors=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--create-sources',action='store_true',help='maintainer only: create original synthetic source plans into a new directory')
    args=p.parse_args()
    try:
        if args.create_sources:write_specs(args.out)
        else:run_all(ROOT/'examples',args.out)
    except (ValueError,OSError,ImportError) as e:print(f'ERROR: {e}',file=sys.stderr);return 2
    print(f'Created {args.out}');return 0
if __name__=='__main__':sys.exit(main())
