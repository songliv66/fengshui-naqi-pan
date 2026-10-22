#!/usr/bin/env python3
"""Build a static offline gallery from actual generated demo artifacts."""
from pathlib import Path
import html
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
CASES=[('01-office','矩形办公室','先换算进出方向，再做整体与头部复核。','overall','head-a'),('02-home','L形住宅','主体矩形与用户另选的面积重心分开比较。','overall','area-centroid'),('03-ambiguous','门向歧义与分界','同一平面0°/6°情景重算，旧结论不能继承。','overall','direction-6')]

def main():
    DOCS.mkdir(exist_ok=True)
    originals=DOCS/'originals';originals.mkdir(exist_ok=True)
    sections=[]
    for case,title,summary,first,second in CASES:
        for ext in ('png','svg'):
            shutil.copyfile(ROOT/f'examples/{case}/source.{ext}',originals/f'{case}.{ext}')
        spec=json.loads((ROOT/f'examples/{case}/input.json').read_text())
        results=[]
        for view in (first,second):
            p=f'generated/{case}/{view}'
            r=json.loads((DOCS/p/'result.json').read_text())
            table=''.join(f'<tr><td>{html.escape(m["label"])}</td><td>{m["sector"]}</td><td>{m["color"]}</td><td>{m["status"]}</td><td>{m["boundary_distance_deg"]}</td></tr>' for m in r['markers'])
            results.append(f'<article><h3>{html.escape(view)}</h3><a href="{p}/overlay.html"><img src="{p}/overlay.png" alt="{title} {view} 实际生成叠图" loading="lazy"></a><p>中心 {r["center"]}；旋转 {r["rotation_deg"]}°；方向状态 {r["direction_status"]}。</p><p><a href="{p}/overlay.html">打开离线透明度滑块</a> · <a href="{p}/overlay.svg">SVG</a> · <a href="{p}/overlay.png">PNG</a> · <a href="{p}/result.json">JSON</a> · <a href="{p}/geometry.md">Markdown</a></p><details><summary>逐标记核对结果</summary><div class="scroll"><table><tr><th>标记</th><th>区号</th><th>颜色</th><th>状态</th><th>距分界°</th></tr>{table}</table></div></details></article>')
        scenario_comment={
          '01-office':'预写解释：HEAD-A整体蓝1且近边界，不能直接判工位合格与否。头部盘中WIN-L为红8、WIN-R为蓝3，实际可开窗跨区，先核对常开扇和坐姿。DRAIN蓝2只表示本套排水偏好，不代替现场漏水、通风检查。',
          '02-home':'预写解释：主体中心(290,330)与面积重心约(400.65,297.10)不同，PILLOW-B从蓝1变红6。应先选口径，不能挑有利结果拼接。本例展示整体取心敏感性，尚未完成逐枕位门窗复核。',
          '03-ambiguous':'预写解释：情景A的EDGE-WIN距分界0°；情景B的HEAD从红7变蓝2且距分界约1.15°。未实测方向只能给条件判断；先核对真北与出门方向，再重新生成，旧结论失效。'
        }[case]
        prompt=(ROOT/f'examples/{case}/README.md').read_text().split('> ',1)[1].split('\n\n',1)[0]
        check={
          '01-office':'预写核查：助手确认进入朝北是否意味着向外朝南、两个窗口点是否为可开端点；合成用户答是，且未现场实测。',
          '02-home':'预写核查：助手说明左侧主体与凹口范围，询问是否明确另选面积重心；合成用户答是，两个枕位分别标记。',
          '03-ambiguous':'预写核查：助手询问门向是否实测、中心是否不变；合成用户答未实测，保留0°与6°两个情景，不选唯一结论。'
        }[case]
        sections.append(f'<section id="{case}"><p class="eyebrow">{case}</p><h2>{title}</h2><p>{summary}</p><div class="raw"><a href="originals/{case}.svg"><img src="originals/{case}.png" alt="{title} 自行绘制的原始合成平面图" loading="lazy"></a><div><h3>合成原始输入</h3><p>无真实公司、住户、地址或账号。PNG和SVG由同一原创场景命令绘制。</p><a href="originals/{case}.svg">原始SVG</a><details><summary>完整参数</summary><pre>{html.escape(json.dumps(spec,ensure_ascii=False,indent=2))}</pre></details><h3>可复制提示词</h3><pre>{html.escape(prompt)}</pre><p>{check}</p></div></div><div class="grid">{"".join(results)}</div><p class="interpretation">{scenario_comment}</p></section>')
    page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>风水纳气盘 · 三组可复算演示</title><style>:root{color-scheme:light}*{box-sizing:border-box}body{font:16px/1.75 system-ui,sans-serif;margin:0;background:#f4f1e9;color:#23323e}header,main,footer{max-width:1260px;margin:auto;padding:36px 32px}header{padding-top:64px}h1{font-size:clamp(32px,5vw,60px);line-height:1.2;letter-spacing:-.04em;margin:12px 0 24px}h2{font-size:32px;line-height:1.4}h3{font-size:19px}.eyebrow{color:#087f6e;letter-spacing:.1em;font-size:13px;font-weight:700}a{color:#0a6372;text-underline-offset:4px}nav{display:flex;gap:22px;flex-wrap:wrap}section{background:#fff;border:1px solid #d7ddd9;border-radius:16px;padding:28px;margin-bottom:38px;scroll-margin-top:20px}.grid,.raw{display:grid;grid-template-columns:1fr 1fr;gap:24px}.raw{margin:20px 0 30px}.grid article{min-width:0;border-top:2px solid #c9d4d0}img{display:block;width:100%;height:auto;border:1px solid #d9dedc;background:#fafafa}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 ui-monospace,monospace;background:#f3f6f5;padding:14px;border-radius:8px}details{margin:14px 0}summary{cursor:pointer;font-weight:600}.interpretation,.notice{padding:18px;background:#eef5f2;border-left:4px solid #087f6e}.notice{max-width:940px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:8px;border-bottom:1px solid #ddd;text-align:left}.scroll{overflow:auto}footer{border-top:1px solid #cad4d0;font-size:14px}@media(max-width:760px){header,main,footer{padding:24px 16px}.grid,.raw{grid-template-columns:1fr}section{padding:18px}h2{font-size:27px}}</style></head><body><header><p class="eyebrow">FENGSHUI NAQI PAN / OPEN SOURCE 1.0.0</p><h1>图形能复算，<br>解释有条件。</h1><p>在自行绘制的平面图上，核对门向、取心与红蓝分区。三套原始输入，六组真实工具输出，全部可离线复现。</p><nav><a href="https://github.com/songliv66/fengshui-naqi-pan">公开仓库与安装</a><a href="https://github.com/songliv66/fengshui-naqi-pan/releases/tag/v1.0.0">版本下载</a><a href="#01-office">矩形办公室</a><a href="#02-home">L形住宅</a><a href="#03-ambiguous">歧义重算</a></nav><p class="notice">红6/7/8/9按本套传统约定为纳气区，蓝1/2/3/4为水位区。数字为旋转后的盘区编号；不代表科学验证的健康、财富或经营预测。本站无上传表单、跟踪器或模型调用。</p><h2>一条命令，六组计算</h2><pre>python3 -m pip install -r requirements.txt\npython3 scripts/make_demos.py --out runs/demo-001</pre><p>需Python 3.10+及Pillow。输出目录必须是新目录。安装后计算和页面离线运行；直接下载本仓库，也可在浏览器打开docs/index.html。原始图、模拟问答和解释是预写教学示范；叠图、JSON与几何记录是工具实际生成，没有伪装的模型评测结果。</p></header><main>'''+''.join(sections)+'''</main><footer><p>公开版独立编写；MIT只覆盖有权授权的代码、原创文档与合成图。方法讲述来源及本次访问限制见仓库references/method.md，未分发博主视频/截图或客户资料。默认主体矩形；面积重心需明确另选。住宅枕位移盘属于本Skill应用扩展。</p><p>联系：puddingvoid（不推定平台）。修改门向、中心、轮廓或头部位置后须重新计算；旧结论不继承。</p></footer></body></html>'''
    (DOCS/'index.html').write_text(page,encoding='utf-8')
    (DOCS/'.nojekyll').touch()
    print('Built docs/index.html from actual generated outputs')

if __name__=='__main__':main()
