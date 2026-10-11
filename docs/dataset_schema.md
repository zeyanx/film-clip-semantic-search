# 数据集规范与授权边界

数据集采用 UTF-8 JSON Lines，每行一个片段对象。加载器拒绝缺字段、重复 ID、非法时间、空权限依据、未知权限状态、非法媒体类型和非有限向量。

## 字段

| 字段 | 类型 | 要求 | 说明 |
|---|---|---|---|
| `segment_id` | string | 必填、唯一 | 片段 ID |
| `media_id` | string | 推荐必填 | 同一影片/视频共享；旧数据缺失时确定性派生 |
| `title` | string | 必填 | 作品或素材名称 |
| `media_type` | string | 推荐必填 | `anime`、`tv`、`movie`、`other`；默认 `other` |
| `dialogue` | string | 可空 | 字幕/台词；与场景描述不能同时为空 |
| `scene_description` | string | 可空 | 经核验的场景描述；不能编造 |
| `keywords` | string[] | 必填 | 非空关键词列表 |
| `start_seconds` | number | 必填 | `>= 0` |
| `end_seconds` | number | 必填 | `> start_seconds` |
| `keyframe_path` | string | 必填、可为空 | 推荐项目相对路径 |
| `source_path` | string | 推荐 | 本地媒体路径；普通结果页不显示 |
| `media_path` | string | 兼容字段 | 旧版媒体路径；新数据优先 `source_path` |
| `rights_status` | string | 必填 | `authorized`、`public_domain`、`permissive_license`、`simulated` |
| `license_source` | string | 必填、非空 | 授权或许可证依据 |
| `is_simulated` | boolean | 必填 | 必须与 `rights_status=simulated` 一致 |
| `semantic_vector` | number[] | 可选 | 预计算句向量 |
| `visual_vector` | number[] | 可选 | 预计算关键帧向量 |

## 样例

```json
{"segment_id":"authorized_000001","media_id":"authorized_short","title":"已授权短片","media_type":"movie","dialogue":"示例台词","scene_description":"经人工核验的场景描述","keywords":["关键词"],"start_seconds":12.0,"end_seconds":16.5,"keyframe_path":"assets/keyframes/example.jpg","source_path":"D:\\authorized\\clip.mp4","media_path":"D:\\authorized\\clip.mp4","rights_status":"authorized","license_source":"授权文件编号或说明","is_simulated":false}
```

## 权利规则

- 只处理用户提供且有权使用、公共领域或许可证允许处理的素材；
- `authorized` 应记录授权主体、范围或本地授权文件；
- `public_domain` 应记录判断依据与来源；
- `permissive_license` 应记录许可证名称、版本和署名/再分发条件；
- `simulated` 只能用于工程验证，不与真实实验混合；
- 系统不包含下载器、网盘、种子、抓取器或绕过访问控制的能力。
