# 03 门向歧义、分界及修改重算

可复制提示词：

> 请用 $fengshui-naqi-pan 读取 examples/03-ambiguous/source.png。门向没有实测，先按input.json的单元向外0°情景计算，再按direction-6.json的6°情景重算，明确未知条件、边界提醒及旧结论失效。不要把两个情景中的一个宣布为测量结果。

原始资料：[PNG](source.png)、[SVG](source.svg)、[0°情景](input.json)、[6°情景](direction-6.json)。同一主体矩形中心(450,330)，所有点位不变，只有单元门向与标题改动。EDGE-WIN坐标由22.5°边界精确构造，是人工几何示例，非现场照片。

预写核查示范：

- 助手：“门向数值是从图上估的还是实测？0°和6°可能改变区号，需标成条件情景；中心是否仍用同一个主体？”
- 合成用户：“未实测，中心不变；请展示两个情景，暂不选唯一结论。”

实际计算：情景A旋转0°，EDGE-WIN距边界0°，仅按半开区间形式归蓝1但标待复核；HEAD为红7。情景B旋转6°，EDGE-WIN距边界6°、仍蓝1；HEAD变蓝2且距边界1.150124°。参数指纹变化，`comparison.previous_conclusions_invalidated=true`；即使某点区号未变，也不得把旧整体解释原样继承。

预写解释与行动：

1. 先测量单元门向和图纸北向，确认是出门还是进门方向。当前只可给条件分析，不能给“已经定盘”的结论。
2. HEAD对6°变化敏感，红7变蓝2；因此现有材料不足以建议搬桌。保留两张情景图，取得可靠方向后再新建目录重算。
3. EDGE-WIN处在分界附近，不把单个精确数字当稳健判断。3°只是默认绘图提示，粗估的方向误差可以更大。

执行：

```bash
python3 scripts/render.py examples/03-ambiguous/input.json --out runs/scenario-a-001
python3 scripts/render.py examples/03-ambiguous/direction-6.json --out runs/scenario-b-001 --previous runs/scenario-a-001/result.json
```

实际输出：[A HTML](../../docs/generated/03-ambiguous/overall/overlay.html)、[B HTML](../../docs/generated/03-ambiguous/direction-6/overlay.html)、[重算JSON](../../docs/generated/03-ambiguous/direction-6/result.json)。没有真实客户数据；模拟问答和解释预写，工具输出实际执行。
