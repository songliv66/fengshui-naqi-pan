# 三组可复算的合成演示

图形、家具、坐标和问答均为虚构。各案例README中的解释是预写教学演示，不是模型评测成绩。`docs/generated/`是工具真实执行的SVG、PNG、HTML、JSON和Markdown记录。

安装依赖后，在仓库根一条命令跑全部6个计算视角，输出目录必须不存在：

```bash
python3 scripts/make_demos.py --out runs/my-demo-001
```

1. [矩形办公室](01-office/README.md)：进/出方向换算，整体盘与头部复核。
2. [L形住宅](02-home/README.md)：明确主体矩形，对比用户另选面积重心。
3. [方向歧义及分界](03-ambiguous/README.md)：0°/6°两情景，自动标旧结论失效。

原始SVG和PNG是一对由同一虚构场景命令绘制的源图，供查看与复算；工具使用PNG底图，不用生成模型猜几何。`scripts/make_demos.py --create-sources --out NEW_DIRECTORY`可重新绘制原始资料，须指定新目录。各示例中的相对命令均从仓库根执行。
