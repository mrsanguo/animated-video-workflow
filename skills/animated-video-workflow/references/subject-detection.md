# 主体检测与镜头级动态安全区

## 运行分析

当输入包含真人、多人、产品演示者或主体位置未知时，在排版前运行：

```powershell
python scripts/analyze_subject.py INPUT_VIDEO --output work/subject-layout.json
```

脚本依赖 `scripts/requirements-subject.txt`。先检查当前 Python 能否导入 `cv2`；缺失时按项目依赖策略安装 OpenCV，并确保运行脚本的 Python 能读取该依赖目录。

默认每 0.75 秒采样一次，每 3 个采样点运行一次全身检测。需要更精细时降低 `--sample-interval`；处理长视频时可以提高该值。不要把采样分析描述为逐帧跟踪。

## 使用输出

读取 `work/subject-layout.json`：

- `layout_type`：区分圆窗、横屏真人、竖屏真人、全屏真人和多人画面。
- `primary_motion_envelope`：主讲人在当前镜头内的活动范围。
- `subject_safe_region`：加入手势与构图边距后的不可遮挡区域。
- `animation_regions`：当前镜头可优先使用的动画区域。
- `review_required`：低置信度、多人或没有稳定动画区域时必须预览确认。

坐标均为 `0..1` 的归一化值。渲染时按目标画布换算像素；横竖屏分别重新分析或重排，不直接复用像素坐标。

## 布局路由

- `picture-in-picture`：只保护圆窗或画中画实际活动范围，把动画面板靠近保护区边缘。
- `landscape-presenter`：优先把信息放到人物视线或身体相反一侧。
- `portrait-presenter`：保护头部、手势和底部字幕区；使用上中下分区，不强塞左右双栏。
- `full-frame-presenter`：只使用明确安全的局部区域；区域不足时改用轻量标签、人物身后弱动效或切换全屏素材。
- `multi-person` 或 `unknown`：半自动模式必须确认；全自动模式优先保守布局或全屏素材，不覆盖检测不到的人物区域。

## 防止动画跳动

把同一镜头内的采样框合并为活动范围，镜头内部固定动画区域。只在镜头边界或主体跨越布局阈值时切换位置，不让动画跟随每个检测框左右抖动。

若检测结果与代表帧明显不符，保留 JSON 和预览作为诊断材料，调整采样间隔或改为人工标注保护区；不要静默忽略低置信度。
