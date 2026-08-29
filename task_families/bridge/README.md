# Bridge

`scripts/generate_bridge_dataset.py` 是 Bridge 数据集的专用构建入口。它一次生成：

- `final_data/bridge/datapacks/bridge_scene_pack/`
- `final_data/bridge/scene_manifest.json`
- `final_data/bridge/generated_tasks.json`

默认运行：

```powershell
python task_families/bridge/scripts/generate_bridge_dataset.py
```

可用 `--out` 指定隔离输出目录。
