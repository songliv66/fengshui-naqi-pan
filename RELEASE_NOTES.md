# v1.0.0

首次独立开源发布：在用户原始PNG/JPEG上确定性计算红蓝八分区，生成SVG、PNG、离线HTML、JSON及Markdown几何记录。支持进出方向换算、主体矩形/面积重心/显式中心、坐者头部复核、边界提醒、裁剪与变更重算指纹。

含三套完全合成的源平面图、六组真实计算输出、完整模拟核查和解释、离线Demo页面、输入契约及17个行为测试。独立编写的代码、文档和图形采用MIT；不含私有历史、客户资料、视频截图、全文转写或分发权不明的旧实现。

传统区号不是科学验证的健康、财富或经营预测。门向未知时只做条件情景；本版不识图、不现场测量、不支持带孔轮廓及自动PDF导出。GitHub CI示例需维护者手动启用，本机通过不等于远端CI通过。

下载Release源代码包后，安装requirements.txt，运行：

```bash
python3 scripts/make_demos.py --out runs/first-demo
```

可在浏览器离线打开`docs/index.html`或新生成的`overlay.html`。联系：puddingvoid。
