# 02 L形住宅与取心对照

可复制提示词：

> 请用 $fengshui-naqi-pan 分析 examples/02-home/source.png 和 input.json，先显示本次选择的左侧主体矩形，不取整套外包框。再按我明确另选的centroid.json重算面积重心，对比PILLOW-B和入口的变化；把两口径分开，床头移盘仅作为住宅应用扩展，不推断健康和财运。

原始资料：[PNG](source.png)、[SVG](source.svg)、[主体矩形参数](input.json)、[面积重心参数](centroid.json)。轮廓六点完整记录L形凹口，无真实住宅或住户信息。

预写核查示范：

- 助手：“本次主体是左侧420×500完整矩形，右上外伸计入实际轮廓但不计入主体矩形；这只是声明的一种选择。你是否要求另算整个实际面积重心作对照？两个枕位是否分别标记？”
- 合成用户：“是，明确对照两种取心。右下凹口不属于房屋，不能补齐。两个枕位分开标，但没有现场开窗/噪声数据。”

实际计算：两门向外均90°，旋转0°。主体中心(290,330)，面积重心(400.654206,297.102804)，不是顶点平均或图片中心。主体盘PILLOW-B为蓝1；重心盘PILLOW-B为红6，入口蓝2在重心盘距边界1.519792°，需复核。重心结果的`comparison`会标旧结论失效。蓝红颜色只裁剪到实际L形，右下凹口保持原样。

预写解释与行动：

1. 本套传统规则：同一枕位在两口径出现不同归区，先选定取心依据，不能挑颜色有利的结果拼接结论。默认工作流继续使用已确认主体矩形。
2. 图上观察：窗口两端在主体盘跨红蓝；不把整间卧室概括为同一颜色。若要判断卧床者门窗关系，需分别以两个枕位另出显式中心盘；本案例只交付整体中心敏感性对照，没有冒称已完成枕位复核。
3. 待现场确认：可开窗范围、噪声、夜间光和实际排风尚未知；先收集住户体验，不据图建议拆改管道或购买化煞物。

执行：

```bash
python3 scripts/render.py examples/02-home/input.json --out runs/home-main-001
python3 scripts/render.py examples/02-home/centroid.json --out runs/home-centroid-001 --previous runs/home-main-001/result.json
```

实际输出：[主体HTML](../../docs/generated/02-home/overall/overlay.html)、[重心HTML](../../docs/generated/02-home/area-centroid/overlay.html)、[重心JSON](../../docs/generated/02-home/area-centroid/result.json)。解释和模拟对话为预写演示；几何文件真实生成。
