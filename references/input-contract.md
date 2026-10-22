# 输入契约 v1.0.0

以[矩形办公室完整JSON](../examples/01-office/input.json)为可运行模板。脚本严格拒绝未知字段、重复JSON键和非有限数值，不默默纠正门向或猜轮廓。

|字段|要求与含义|
|---|---|
|`image`|本地PNG/JPG/JPEG；相对JSON的位置解析。不接受URL或SVG脚本。原文件只读，不改尺寸。|
|`canvas`|`[宽,高]`，必须等于底图真实像素；整数100—10000，合计≤4000万像素。|
|`outline`|3—500个按边界顺序的`[x,y]`，一个无孔、不自交多边形，图片左上为原点。不要重复闭合顶点，删除冗余共线点。|
|`north_angle`|真北在图中相对向上顺时针角度，`0≤角<360`。|
|`building_direction` / `unit_direction`|各为`{"degrees":270,"sense":"outward"}`；`sense`为`outward`或`inward`，后者自动加180°。门在何处不等于门朝向。|
|`direction_status`|`measured`实测、`approximate`粗估、`scenario`情景；未知门向不能伪填实测值。|
|`center_mode`|`main_rectangle`（默认工作流，字段仍必填）、`centroid`或`explicit`。|
|`main_rectangle`|主体模式必需，`[左,上,右,下]`，必须全在使用轮廓内；不自动取不规则轮廓外包框。|
|`center`|显式模式必需，`[x,y]`，须位于轮廓内。用于坐者头部或有依据的指定中心。|
|`center_reason`|必填文本，解释选择范围、来源和估计性质。|
|`markers`|至多500个；每个仅含`label`、`xy`和`kind`；标签唯一1—80字符，不接受换行等控制字符，位置在轮廓内。|
|`kind`|`entrance`、`window`、`head`、`drain`、`other`；标记用途不会自动变为传统合格结论。|
|`boundary_tolerance_deg`|可选，默认3°，允许0—22.5°，仅为绘图提醒。|
|`opacity`|可选，默认0.28，允许0—0.7。HTML滑块只改变显示透明度。|
|`crop`|可选`[左,上,宽,高]`，在原图内的整数像素显示范围。计算仍用完整原始坐标；底部额外120px是方向图例。|
|`title`|可选，至多120字符，显示于HTML和几何记录；图上标记建议短标签。|
|`font`|可选，本地有权使用的字体文件；相对JSON位置解析。PNG非ASCII标签必须提供；也可用命令`--font`覆盖；命令行字体相对当前工作目录解析，`spec.font`相对JSON所在目录解析。字体不复制进输出。|

图上的SVG文字由查看端字体绘制，PNG文字由Pillow绘制。示例统一用ASCII短标签，中文说明在Markdown/HTML页面，无需分发字体。自定义字体能否覆盖所需汉字由使用者核查；文件存在不等于含所有字形。缺字体会在创建输出目录前失败。

命令：

```bash
python3 scripts/render.py my-input.json --out runs/case-001
python3 scripts/render.py changed-input.json --out runs/case-002 --previous runs/case-001/result.json
```

每次必须新目录，已存在目录即使为空也拒绝覆盖。先校验、读取原图、计算和渲染，再将完整文件集写入；并发同名运行也不会合并两次结果。修订参数后新生成的`comparison.previous_conclusions_invalidated`表明旧解读不应沿用。

产物：自带底图的`overlay.svg`、带滑块的离线`overlay.html`、像素叠图`overlay.png`、可复核`result.json`、可选择文字的`geometry.md`。输出不携带输入原图的绝对路径，但会记录文件名与SHA-256。PNG图例在原图外增加120像素，不改变原图比例。裁剪边缘标记会显示内缩圆点和引线，JSON仍保留原坐标；视窗外点在JSON/HTML表中保留并提示。标记文字绘制在区号之上，避免被遮挡。很窄的裁剪可能让图例拥挤，应保留足够宽度或使用HTML/JSON查看方向。

不支持：多环/孔洞、曲线轮廓、自动识图/自动量测、经纬度测北、现场磁偏角校正、自动PDF导出。带孔平面不能用一个外环忽略孔洞；需另行可靠建模，当前工具会拒绝嵌套轮廓。图片自身已拉伸或错误标北时，工具无法替代现场核查。
