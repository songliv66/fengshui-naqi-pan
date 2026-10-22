"""Behavior tests for actual layout risks; run with unittest, no network."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render import classify,centroid,validate,generate,read_spec,outward
BASE=json.loads((ROOT/'examples/01-office/input.json').read_text())


class GeometryTests(unittest.TestCase):
    def test_known_rotation_and_inward_conversion(self):
        r=validate(BASE)
        self.assertEqual((r['building_outward_deg'],r['unit_outward_deg'],r['rotation_deg']),(270,180,-90))
        # Hand-checked north clockwise sequence after a -90-degree rotation.
        expected=[3,4,9,2,7,6,1,8]
        for heading,sector in zip(range(0,360,45),expected):
            a=math.radians(heading)
            p=[450+100*math.sin(a),330-100*math.cos(a)]
            self.assertEqual(classify(p,[450,330],-90,0,3)['sector'],sector)
        self.assertEqual(outward({'degrees':180,'sense':'inward'},'door'),0)

    def test_rotation_of_image_preserves_true_classification(self):
        # Point [100,50] (east) becomes [50,100] when the image rotates 90 clockwise.
        original=classify([100,50],[50,50],-90,0,3)
        rotated=classify([50,100],[50,50],-90,90,3)
        self.assertEqual(original['sector'],rotated['sector'])
        self.assertEqual(original['true_bearing_deg'],rotated['true_bearing_deg'])

    def test_centroid_not_vertex_average_and_winding_invariant(self):
        p=[[0,0],[4,0],[4,1],[1,1],[1,4],[0,4]]
        c,area=centroid(p);rc,ra=centroid(list(reversed(p)))
        self.assertAlmostEqual(area,7);self.assertAlmostEqual(c[0],19/14);self.assertAlmostEqual(c[1],19/14)
        self.assertEqual(c,rc);self.assertEqual(area,ra)
        self.assertNotAlmostEqual(c[0],sum(x for x,y in p)/len(p))

    def test_center_and_boundary_are_explicit(self):
        self.assertEqual(classify([0,0],[0,0],0,0,3)['status'],'at_center')
        a=math.radians(22.5)
        edge=classify([100*math.sin(a),-100*math.cos(a)],[0,0],0,0,3)
        self.assertEqual(edge['status'],'boundary_review');self.assertAlmostEqual(edge['boundary_distance_deg'],0)
        self.assertEqual(classify([0,-100],[0,0],0,0,3)['status'],'classified')

    def test_outer_box_of_l_shape_rejected(self):
        spec=json.loads((ROOT/'examples/02-home/input.json').read_text())
        spec['main_rectangle']=[80,80,820,580]
        with self.assertRaisesRegex(ValueError,'within outline'):validate(spec)

    def test_sloping_narrow_notch_rejects_rectangle_crossing(self):
        spec=copy.deepcopy(BASE);spec['outline']=[[0,0],[100,0],[100,100],[70,100],[70,51],[55,48],[50,51],[50,100],[0,100]]
        spec['main_rectangle']=[10,10,90,50];spec['markers']=[]
        with self.assertRaisesRegex(ValueError,'within outline'):validate(spec)
        spec['main_rectangle']=[10,10,90,40]
        self.assertEqual(validate(spec)['center'],[50,25])

    def test_invalid_geometry_and_marker_inputs_fail(self):
        edits=[('outline',[[80,80],[820,580],[80,580],[820,80]]),('outline',[[80,80],[80,80],[80,580]]),('north_angle',float('nan')),('outline',[[0,0],[900,0],[900,700],[0,700]]),('center_mode','guess'),('direction_status','unknown'),('markers',[{'label':'OUT','xy':[0,0],'kind':'head'}]),('markers',[BASE['markers'][0],BASE['markers'][0]])]
        for k,v in edits:
            with self.subTest(key=k,value=v):
                s=copy.deepcopy(BASE);s[k]=v
                with self.assertRaises(ValueError):validate(s)
        s=copy.deepcopy(BASE);del s['unit_direction']
        with self.assertRaisesRegex(ValueError,'missing'):validate(s)
        s=copy.deepcopy(BASE);s['outline']=[s['outline']]
        with self.assertRaises(ValueError):validate(s)

    def test_crop_does_not_change_geometry(self):
        r=validate(BASE);s=copy.deepcopy(BASE);s['crop']=[80,80,740,500];c=validate(s)
        self.assertEqual(r['center'],c['center']);self.assertEqual(r['markers'],c['markers'])
        s['crop']=[80,80,900,500]
        with self.assertRaises(ValueError):validate(s)


class OutputTests(unittest.TestCase):
    def test_actual_exports_clip_and_keep_original(self):
        source=ROOT/'examples/02-home/source.png'
        before=source.read_bytes()
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'render';generate(ROOT/'examples/02-home/input.json',out)
            self.assertEqual({p.name for p in out.iterdir()},{'overlay.png','overlay.svg','overlay.html','result.json','geometry.md'})
            with Image.open(source) as raw,Image.open(out/'overlay.png') as made:
                self.assertEqual(made.size,(900,780))
                self.assertEqual(raw.getpixel((750,500)),made.getpixel((750,500))) # Outside L shape.
                self.assertNotEqual(raw.getpixel((400,400)),made.getpixel((400,400))) # Inside overlay.
            self.assertIn('data:image/png;base64,',(out/'overlay.svg').read_text())
            self.assertIn('Direction key only',(out/'overlay.html').read_text())
        self.assertEqual(source.read_bytes(),before)

    def test_existing_output_and_duplicate_runs_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'result';out.mkdir();(out/'keep.txt').write_text('retain')
            with self.assertRaisesRegex(ValueError,'already exists'):generate(ROOT/'examples/01-office/input.json',out)
            self.assertEqual((out/'keep.txt').read_text(),'retain')
            other=Path(td)/'fresh';generate(ROOT/'examples/01-office/input.json',other)
            data=(other/'result.json').read_bytes()
            with self.assertRaises(ValueError):generate(ROOT/'examples/01-office/input.json',other)
            self.assertEqual(data,(other/'result.json').read_bytes())

    def test_parameter_change_invalidates_previous(self):
        with tempfile.TemporaryDirectory() as td:
            first=Path(td)/'first';second=Path(td)/'second'
            a=generate(ROOT/'examples/03-ambiguous/input.json',first)
            b=generate(ROOT/'examples/03-ambiguous/direction-6.json',second,first/'result.json')
            self.assertNotEqual(a['input_fingerprint'],b['input_fingerprint'])
            self.assertTrue(b['comparison']['previous_conclusions_invalidated'])
            self.assertIn('unit_direction',b['comparison']['changed_inputs'])
            self.assertEqual(a['markers'][2]['sector'],7);self.assertEqual(b['markers'][2]['sector'],2)

    def test_duplicate_json_keys_and_wrong_image_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'input.json';p.write_text('{"image":"x","image":"y"}')
            with self.assertRaisesRegex(ValueError,'duplicate'):read_spec(p)
            s=copy.deepcopy(BASE);s['image']=str(ROOT/'examples/01-office/source.png');s['canvas']=[901,660]
            p.write_text(json.dumps(s));out=Path(td)/'result'
            with self.assertRaisesRegex(ValueError,'dimensions'):generate(p,out)
            self.assertFalse(out.exists())

    def test_missing_font_unicode_without_font_fail_before_output(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'input.json';s=copy.deepcopy(BASE);s['image']=str(ROOT/'examples/01-office/source.png');s['font']='missing.ttf';p.write_text(json.dumps(s))
            out=Path(td)/'out'
            with self.assertRaisesRegex(ValueError,'font file is missing'):generate(p,out)
            self.assertFalse(out.exists())
            s.pop('font');s['markers'][0]['label']='入口';p.write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError,'outside ASCII'):generate(p,out)
            self.assertFalse(out.exists())

    def test_missing_dependency_has_actionable_failure(self):
        with tempfile.TemporaryDirectory() as td:
            result=subprocess.run([sys.executable,'-S',str(ROOT/'scripts/render.py'),str(ROOT/'examples/01-office/input.json'),'--out',str(Path(td)/'out')],capture_output=True,text=True)
            self.assertEqual(result.returncode,2);self.assertIn('PIL',result.stderr)
            self.assertFalse((Path(td)/'out').exists())

    def test_crop_annotation_inside_export_and_source_coordinate_kept(self):
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory() as td:
            spec=copy.deepcopy(BASE);spec['image']=str(ROOT/'examples/01-office/source.png')
            spec['crop']=[80,80,740,500]
            spec['markers']=[{'label':'RIGHT-ENTRY','xy':[820,200],'kind':'entrance'}]
            p=Path(td)/'input.json';p.write_text(json.dumps(spec));out=Path(td)/'out'
            result=generate(p,out)
            self.assertEqual(result['markers'][0]['xy'],[820,200])
            self.assertTrue(any('annotation inset' in v for v in result['warnings']))
            root=ET.fromstring((out/'overlay.svg').read_text())
            label=next(e for e in root.iter() if e.tag.endswith('text') and e.text=='RIGHT-ENTRY')
            # Exported label's conservative width stays inside the actual original-coordinate crop.
            self.assertGreaterEqual(float(label.attrib['x']),88)
            self.assertLessEqual(float(label.attrib['x'])+len('RIGHT-ENTRY')*10,812)

    def test_marker_labels_paint_above_sector_numbers(self):
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out';generate(ROOT/'examples/01-office/input.json',out)
            root=ET.fromstring((out/'overlay.svg').read_text())
            texts=[e.text for e in root.iter() if e.tag.endswith('text')]
            last_number=max(i for i,t in enumerate(texts) if t in {'1','2','3','4','6','7','8','9'})
            for marker in BASE['markers']:
                self.assertGreater(texts.index(marker['label']),last_number)

    def test_html_is_offline_and_contains_no_external_execution(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out';generate(ROOT/'examples/01-office/input.json',out)
            content=(out/'overlay.html').read_text()
            self.assertNotIn('<script src=',content);self.assertNotIn('fetch(',content);self.assertNotIn('https://',content)
            self.assertIn('id="opacity"',content);self.assertIn('id="sectors"',content)

if __name__=='__main__':unittest.main(verbosity=2)
