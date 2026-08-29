#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


FUNCTION_DIR_NAMES = ("function", "functions")
OBJECTIVE = "spawn_inspect"
TAG = "spawn_inspector"


def write_function(pack_root, namespace, relative_path, lines):
    content = "\n".join(lines) + "\n"
    for directory in FUNCTION_DIR_NAMES:
        path = pack_root / "data" / namespace / directory / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def coord(value):
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number)


def default_steps(tasks):
    steps = []
    for task in tasks:
        for player_key, label in (("player_a", "A"), ("player_b", "B")):
            player = task["players"][player_key]
            steps.append(build_step(task, player, label))
    return steps


def difficulty_role_steps(tasks):
    steps = []
    difficulty_order = ("easy", "medium", "hard")
    role_order = (("player_b", "B"), ("player_a", "A"))
    for difficulty in difficulty_order:
        tier_tasks = [task for task in tasks if task.get("difficulty") == difficulty]
        for player_key, label in role_order:
            for task in tier_tasks:
                steps.append(build_step(task, task["players"][player_key], label))
    return steps


def build_step(task, player, label):
    return {
        "task_id": task["id"],
        "scene_id": task["scene_id"],
        "difficulty": task.get("difficulty"),
        "label": label,
        "position": player["start_pos"],
        "rotation": player["start_rotation"],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate a timed A/B spawn-position inspection function.")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--pack-root", required=True)
    parser.add_argument("--namespace", default="multiagent_scene")
    parser.add_argument("--interval", default="10t")
    parser.add_argument("--silent", action="store_true")
    parser.add_argument(
        "--order",
        choices=("task", "difficulty-role"),
        default="task",
        help="TP order: task keeps A/B per task; difficulty-role groups B then A for easy, medium, hard.",
    )
    args = parser.parse_args()

    task_path = Path(args.tasks).resolve()
    pack_root = Path(args.pack_root).resolve()
    payload = json.loads(task_path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks", [])
    steps = difficulty_role_steps(tasks) if args.order == "difficulty-role" else default_steps(tasks)

    start_lines = [
        f"scoreboard objectives add {OBJECTIVE} dummy",
        f"schedule clear {args.namespace}:inspect_spawns/tick",
        f"tag @a remove {TAG}",
        f"tag @s add {TAG}",
        f"scoreboard players set @s {OBJECTIVE} 0",
        f"function {args.namespace}:inspect_spawns/tick",
    ]
    if not args.silent:
        start_lines.insert(-1, f'tellraw @s {{"text":"Starting spawn inspection: {len(steps)} positions, interval {args.interval}.","color":"green"}}')

    tick_lines = []
    for index, step in enumerate(steps):
        x, y, z = (coord(value) for value in step["position"])
        yaw, pitch = (coord(value) for value in step["rotation"])
        selector = f"@a[tag={TAG},scores={{{OBJECTIVE}={index}}}]"
        tick_lines.append(f"tp {selector} {x} {y} {z} {yaw} {pitch}")
        if not args.silent:
            message = f"[{index + 1}/{len(steps)}] difficulty={step.get('difficulty')} task={step['task_id']} scene={step['scene_id']} Agent {step['label']} pos=({x}, {y}, {z})"
            tick_lines.append(f'tellraw {selector} {{"text":"{message}","color":"yellow"}}')
    tick_lines.extend(
        [
            f"scoreboard players add @a[tag={TAG}] {OBJECTIVE} 1",
            f"execute if entity @a[tag={TAG},scores={{{OBJECTIVE}=..{len(steps) - 1}}}] run schedule function {args.namespace}:inspect_spawns/tick {args.interval} replace",
            f"execute if entity @a[tag={TAG},scores={{{OBJECTIVE}={len(steps)}..}}] run function {args.namespace}:inspect_spawns/finish",
        ]
    )

    finish_lines = [f"tag @a[tag={TAG}] remove {TAG}"]
    if not args.silent:
        finish_lines.insert(0, f'tellraw @a[tag={TAG}] {{"text":"Spawn inspection complete: {len(steps)} positions checked.","color":"green"}}')
    stop_lines = [f"schedule clear {args.namespace}:inspect_spawns/tick", f"tag @a[tag={TAG}] remove {TAG}"]
    if not args.silent:
        stop_lines.insert(1, f'tellraw @a[tag={TAG}] {{"text":"Spawn inspection stopped.","color":"red"}}')

    write_function(pack_root, args.namespace, Path("inspect_spawns/start.mcfunction"), start_lines)
    write_function(pack_root, args.namespace, Path("inspect_spawns/tick.mcfunction"), tick_lines)
    write_function(pack_root, args.namespace, Path("inspect_spawns/finish.mcfunction"), finish_lines)
    write_function(pack_root, args.namespace, Path("inspect_spawns/stop.mcfunction"), stop_lines)
    print(f"Generated spawn inspection for {len(steps)} positions in {pack_root}")


if __name__ == "__main__":
    main()
