# 项目说明给未来的 Claude

把 OBJ 文件目录批量渲染成 PNG。脚本是 Blender 2.7x 时代写的,本仓库已 patch 到 Blender 4.0.2 (macOS arm64) 可跑。

## Working command(已验证)

```bash
PYTHONPATH=$PWD /Applications/Blender.app/Contents/MacOS/Blender --background \
  blend/render_normalization_square_hit_ground.blend \
  --python obj_render_background_blend.py -- \
  -in <obj_dir> -m NULL
```

要点:
- `PYTHONPATH=$PWD` 必加——脚本 line 24 `sys.path.append('..')` 加的是 CWD 的父目录,从仓库根目录跑找不到 `util/`(且 `util/` 是后建的 shim,`__init__.py` + 一个 symlink 到 `argparse4blender.py`)
- `--` 分隔符必须有,后面才是脚本自己的参数
- macOS 上 Blender 没在 PATH,必须用绝对路径 `/Applications/Blender.app/Contents/MacOS/Blender`

测试样例:`/tmp/chair_test/chair.obj` → `chair.png`(从 `blend/render_normalization_square_output__rotate_video.blend` 里的 `analyze_objfunc_skiprank_19` mesh export 出来的椅子)

## .blend 清单(每个都 dump 过)

| 文件 | 内置 mesh | 用途 | 能否给 batch render 脚本用 |
|---|---|---|---|
| `render_normalization_square_hit_ground.blend` | `analyze_objfunc_skiprank_1397.006`(狗,dim 1.04×2.0×1.69) | **batch render 主场景**,4 摄像机 + plane + courtyard.exr HDRI | ✅ 默认用这个 |
| `render_normalization_template.blend` | 只有 Plane | 空模板 | 只剩骨架 |
| `render_normalization_square_output_template.blend` | 只有 Plane(超大,scale=15960) | 输出空模板 | 同上 |
| `render_normalization_square_output__rotate_video.blend` | `analyze_objfunc_skiprank_19`(凳/椅,dim 1.95×1.06×1.25) | 视频渲染场景,有 BezierCircle + CameraR + Light4A | ❌ render 输出格式是动画;且额外对象会被脚本 cleanup 误删 |

## 场景关键设置(`hit_ground.blend`)

- 引擎:CYCLES,128 samples,480×480
- `film_transparent=True`(在 .blend 里就开了,不依赖 `--transparent_background`)
- World:`courtyard.exr` 作 environment HDRI(Background strength=1.0)
- Light:SPOT,energy=1383,位于 (0.13, -9.33, 0.02),色温偏紫
- Plane:位于 (0, 1, 0),scale=1138,作地面用
- 摄像机 4 个:Camera/Camera.001/.002/.003,均 50mm,sensor 36×24,clip [0.1, 1000]

## 脚本依赖的硬编码场景对象名

```python
KEEP = {'Camera', 'Light', 'Camera.001', 'Camera.002', 'Camera.003', 'Plane'}
```

Cleanup 阶段不在 KEEP 里的 mesh 都会被 `bpy.data.objects.remove()` 删掉。换其它 .blend 时如有额外对象(BezierCircle / 多盏灯 / track-to empty),要么改 KEEP,要么换回 hit_ground。

## 已应用的 4.0 API 兼容 patch(vs git HEAD)

| 行 | 旧 API | 新 API | 原因 |
|---|---|---|---|
| 92-105 | `bpy.ops.object.delete()` ×3 | `bpy.data.objects.remove(obj, do_unlink=True)` | headless 模式下 ops.delete 需要 context override,data.remove 不需要 |
| 119 | `bpy.ops.import_scene.obj()` | `bpy.ops.wm.obj_import()` | Blender 4.0 移除了 legacy Python 版,改用 C++ |
| 131, 133 | `bpy.ops.object.editmode_toggle()` | `bpy.ops.object.mode_set(mode='EDIT'/'OBJECT')` | 需要明确 mode |
| 161 | `obj_basename[0]` | `obj_basename`(typo fix) | 原来会取首字符,multiview 输出文件名截断 |
| 176 | `bpy.ops.object.delete()` | `bpy.data.objects.remove(...)` | 同 92-105 |

新增 `util/__init__.py` + `util/argparse4blender.py` symlink,让 `from util.argparse4blender import` 能解析。

## 运行环境

- Blender 4.0.2 (`/Applications/Blender.app/Contents/MacOS/Blender`)
- macOS 15.6 Sequoia, arm64
- 没装 blender-mcp(社区那个 MCP server),目前都靠 `--background --python` headless

## 排错

| 现象 | 原因 | 修复 |
|---|---|---|
| `ModuleNotFoundError: util` | `PYTHONPATH` 没设或 `util/` 没建 | `PYTHONPATH=$PWD` + 确认 `util/__init__.py` 存在 |
| `Operator bpy.ops.object.delete.poll() failed` | 用了未 patch 的版本 | 看上表确认 patch 都打了 |
| `import_scene.obj has no attribute` | 同上 | 同上 |
| `Cannot write a single file with an animation format selected` | 用了 `_rotate_video.blend`,它的 render output 是视频格式 | 换 `hit_ground.blend`,或在脚本里加 `bpy.context.scene.render.image_settings.file_format = 'PNG'` |
| 渲染出来啥都看不见(画面空) | 输入 mesh 太小/对称(如 default cube)被 modifier 链(Decimate 0.6 + Smooth 2.0 ×2)磨成一个点 | 用真实 mesh,如本仓库 .blend 内置的 chair |

## 下一步(如果用户要求)

- 装 `ahujasid/blender-mcp` 让 Claude 能交互式查 Blender 场景(socket port 9876)
- 把 4 处 patch 提个 commit "Blender 4.x compatibility"
- 加 multiview 测试(`--multiview` 应渲 4 张 `_view001/002/003.png` + `_view0.png`,line 161 fix 后才正确)
