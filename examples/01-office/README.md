# 01 矩形办公室

可复制提示词：

> 请用 $fengshui-naqi-pan 读取 examples/01-office/input.json 和 source.png。建筑门向外朝西，进入办公室时朝北；先核对进出方向、主体矩形和窗口跨度，再实际生成整体盘与HEAD-A头部复核。把传统解释与图上观察分开，不假设已有现场测量，不承诺经营或财运。

原始资料：[PNG](source.png)、[SVG](source.svg)、[整体参数](input.json)、[头部参数](head-a.json)。全部合成。原图900×660，使用轮廓为(80,80)—(820,580)矩形，中心(450,330)。

预写核查示范：

- 助手：“‘进入朝北’是行走进入室内的方向，对应向外朝南180°；是否如此？WIN-L与WIN-R是否为同一可开启窗口的两个端点？”
- 合成用户：“是，作为演示情景；两点是可开部分端点，未实测。DRAIN才是水槽排水点。”

实际计算：建筑270°、单元向内0°换为向外180°，旋转−90°；整体HEAD-A归蓝1且距边界1.943955°，WIN-R距边界0.698591°，均提示复核。ENTRY蓝2，DRAIN蓝2。头部盘中心改为(330,285)，保持−90°旋转；WIN-L红8，WIN-R蓝3，窗口两端跨红蓝，不能把整扇窗笼统判红。

预写解释与行动：

1. 本套传统规则：整体入口蓝2，需要先核对主门方向与真实位置再讨论偏好；图色不证明业务好坏。
2. 本套传统规则：A位整体蓝1不能直接宣布不合格，已另做头部复核。可开窗两端跨区；下一步确认实际常开扇和头部坐姿，再比较移动座椅的小方案。
3. 图上观察：右下角DRAIN是实际排水点，蓝2符合本方法水位偏好。是否漏水、通风和通行要现场查，不由盘区代替。

执行：

```bash
python3 scripts/render.py examples/01-office/input.json --out runs/office-001
python3 scripts/render.py examples/01-office/head-a.json --out runs/office-head-001
```

实际输出：[整体HTML](../../docs/generated/01-office/overall/overlay.html)、[PNG](../../docs/generated/01-office/overall/overlay.png)、[JSON](../../docs/generated/01-office/overall/result.json)、[头部HTML](../../docs/generated/01-office/head-a/overlay.html)。工具只生成几何记录；上面的沟通与解释由作者预写，使用模型时仍须重新核读资料。
