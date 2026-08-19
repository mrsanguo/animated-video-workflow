---
name: animated-video-workflow
description: 编排口播视频或音频从输入检查、可选粗剪、字幕时间轴、真人主体检测、镜头级动态安全区、混合型动画分镜、图片/视频/截图素材搜集、AI 素材生成、多引擎渲染、横竖屏适配到成片质检的完整流程。用户要求把横屏或竖屏真人口播、音频、SRT 或文稿制作成动画视频、识别人脸和人物后避让包装、给视频增加动画包装、先粗剪再包装、使用 HyperFrames 或 Remotion 制作视频、自动寻找素材或同时输出 16:9 与 9:16 成片时使用。
---

# 动画视频总控

把内容判断、素材编排和引擎选择交给总控流程，把媒体检查、计划校验和交付检查交给脚本。默认生成真人口播与动画、截图、图表、图片及视频素材混合的成片。

## 工作模式

- 默认使用半自动模式，在分镜与素材方案、素材重规划、代表性试片三个节点等待确认。
- 只有用户明确要求全自动时才连续执行。关键素材缺失、低置信度事实画面、安装需要系统授权、渲染失败或质检不通过时仍暂停。
- 不默认剪辑输入视频。只有用户明确要求“先粗剪，再做动画包装”时，才调用现有 `ai-video-editing` Skill；使用它输出的粗剪视频、时间映射和重映射字幕，不重复转写。

## 流程

1. 检查输入目录和现有素材。运行 `scripts/inspect_inputs.py INPUT_DIR --output work/project-manifest.json`；按需加入 `--mode full-auto` 或显式的 `--rough-cut`。
2. 缺少字幕时，从视频提取音频并转写，或将用户文稿与音频对齐。已有 SRT 时保持其时间轴。
3. 若明确要求粗剪，先完成粗剪和字幕重映射，再锁定动画时间轴。不得先做动画后改变口播时间轴。
4. 分析主体并确定视觉身份。输入含真人、多人或主体位置未知时，先读取 [references/subject-detection.md](references/subject-detection.md)，运行 `scripts/analyze_subject.py INPUT_VIDEO --output work/subject-layout.json`；再读取 [references/layout-composition.md](references/layout-composition.md)，按镜头记录主体安全区、动画区域、字幕安全区和外侧呼吸区。优先读取项目 `DESIGN.md` 或 `visual-style.md`；没有时询问，或在全自动模式下生成待审核的 `DESIGN.md`。不得凭经验预留整条空白侧栏。
5. 生成 `storyboard.json`：逐段记录旁白、起止时间、真人或素材画面类型、核心信息、动效意图和素材引用。
6. 生成 `asset-plan.json`。先扫描用户素材，再搜索图片、视频或网页内容，然后自动截图；仍缺失时才生成图片或动画元素。
7. 把每个外部素材写入 `asset-register.json`，记录来源链接、平台、作者、获取时间、用途和 `pending-review` 版权状态。不得声称来源不明素材可商用。
8. 根据实际素材重新规划分镜。素材与设想不匹配时修改画面方案，不强行套用原计划。
9. 为每个场景生成 `render-plan.json`，读取 [references/engine-routing.md](references/engine-routing.md) 选择源视频、HyperFrames、Remotion 或 FFmpeg。
10. 先渲染开头、信息密集段、真人与动画切换段等 2 至 3 个代表性试片。检查真人锚点与动画内容的视觉重心、无效空白、贴边元素和对侧呼吸区；通过确认或自动质检后再渲染全片。
11. 分别生成 16:9 和 9:16 布局。共享内容和时间轴，按 [references/layout-composition.md](references/layout-composition.md) 分别调整人物、动画面板、字幕安全区、图表、素材构图和外侧留白；禁止简单居中裁切。
12. 使用 FFmpeg 合成和封装，按 [references/quality-gates.md](references/quality-gates.md) 质检，再运行 `scripts/verify_outputs.py PROJECT_DIR`。

在创建或修改 JSON 计划前读取 [references/schemas.md](references/schemas.md)，并运行：

```powershell
python scripts/validate_plan.py --manifest work/project-manifest.json --storyboard work/storyboard.json --asset-plan work/asset-plan.json --render-plan work/render-plan.json --subject-layout work/subject-layout.json
```

## 引擎与依赖

- 生成 HyperFrames 工程前，若当前 Agent 提供 HyperFrames 与 CLI 专用 Skill，则加载并遵守；否则只在本机已有 HyperFrames 文档和依赖时使用该引擎，缺失时改选 Remotion 或 FFmpeg。
- 生成 Remotion 工程前，若当前 Agent 提供 Remotion 最佳实践 Skill，则先加载；否则遵守现有项目规范和本地依赖，缺失时改选 HyperFrames 或 FFmpeg。不得把未安装的引擎描述为可用。
- 使用 FFmpeg 前检查媒体参数，精确裁切默认重编码；不要把流复制描述成任意帧精确。
- 先检测现有版本，再自动补齐缺失依赖并验证。需要管理员权限、登录、网络批准或可能替换不兼容环境时，先请求授权。
- 主体分析使用 `scripts/requirements-subject.txt`。把依赖安装到项目环境；不要修改系统 Python。OpenCV 必须使用 4.x 稳定版。

## 自动化边界

- 可自动：输入检查、转写判断、计划校验、素材候选搜索、截图、AI 素材生成、引擎路由、试片、渲染、双比例适配和技术质检。
- 半自动确认：分镜和素材策略、素材重规划、代表性试片。
- 用户最终负责网络素材版权审核。保留来源登记和审核清单。
- 不覆盖原始素材、已通过试片或成片。输出使用 `preview-vN`、`final-16x9-vN` 和 `final-9x16-vN`。
- 只重做失败场景；保留中间文件并报告具体失败阶段。
- 只把项目经验写入 `work/lessons.md`。只有用户明确要求时才更新本 Skill。

## 默认交付物

```text
work/project-manifest.json
work/storyboard.json
work/asset-plan.json
work/asset-register.json
work/render-plan.json
work/subject-layout.json
work/copyright-review.md
work/qc-report.json
previews/preview-v1.mp4
output/final-16x9-v1.mp4
output/final-9x16-v1.mp4
engines/hyperframes/
engines/remotion/
```
