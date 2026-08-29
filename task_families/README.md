# Task Families

任务相关内容按协作机制归档。每个任务族尽量使用相同结构：

- `task_specs/`：任务语义、角色、机制和成功条件。
- `scene_specs/`：可直接交给 `generate_scenes.py` 的场景参数。
- `scripts/`：该任务族专用的 spec 或 task 生成脚本。

## time_lock

包含 `elevator_hold_door` 与 `pressure_path_reveal`。它们共享压力板持续触发的时序机制，因此联合配置和难度生成器保留在同一任务族中。

生成难度配置：

```powershell
python task_families/time_lock/scripts/generate_time_lock_difficulty_specs.py
```

生成场景：

```powershell
python generate_scenes.py --spec task_families/time_lock/scene_specs/time_lock_elevator_difficulty_30_scenes.json --out final_data/elevator --namespace elevator --pack-name elevator_scene_pack
```

## information_complementarity

包含 `high_platform_gold_guidance`、`maze_command_guidance` 与 `truck_driver`。各任务都由一名 Agent 掌握目标信息，另一名 Agent 执行动作。

专项脚本分别生成 maze、picture 和 truck 的场景配置与任务数据。例如：

```powershell
python task_families/information_complementarity/scripts/generate_maze_specs.py
python task_families/information_complementarity/scripts/generate_maze_tasks.py
```

## lift_time_dependency

目前只有场景配置，场景和任务构建逻辑由顶层通用的 `generate_scenes.py` 与 `generate_tasks.py` 提供。

## bridge

Bridge 暂时使用一个族内专用脚本，同时生成 30 个场景、datapack、manifest 和 100 条任务：

```powershell
python task_families/bridge/scripts/generate_bridge_dataset.py
```
