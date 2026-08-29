#!/usr/bin/env python3
import argparse
import json
import math
import random
import sys
from pathlib import Path

CONSTRUCT_SCENE_ROOT = Path(__file__).resolve().parents[3]
if str(CONSTRUCT_SCENE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONSTRUCT_SCENE_ROOT))

from generate_tasks import build_elevator_task, build_pressure_path_task


TIER_COUNTS = {"easy": 100, "medium": 100, "hard": 100}
SCENES_PER_DIFFICULTY = 15


def center(region):
    return [(region[0] + region[3]) / 2.0, float(region[1]), (region[2] + region[5]) / 2.0]


def distance(left, right):
    return math.hypot(float(right[0]) - float(left[0]), float(right[2]) - float(left[2]))


def target_yaw(start, target):
    return math.degrees(math.atan2(-(float(target[0]) - float(start[0])), float(target[2]) - float(start[2])))


def normalize_angle(value):
    return (value + 180.0) % 360.0 - 180.0


def rotation_toward(start, target, angle_range, rng):
    low, high = angle_range
    error = rng.uniform(low, high)
    if rng.random() < 0.5:
        error = -error
    yaw = normalize_angle(target_yaw(start, target) + error)
    return [round(yaw, 1), 0.0], round(abs(error), 1)


def cells_in_region(region, inset=0):
    return [
        (x, z)
        for x in range(int(region[0]) + inset, int(region[3]) - inset + 1)
        for z in range(int(region[2]) + inset, int(region[5]) - inset + 1)
    ]


def point(cell, y):
    return [cell[0] + 0.5, float(y), cell[1] + 0.5]


def in_region(cell, region):
    return int(region[0]) <= cell[0] <= int(region[3]) and int(region[2]) <= cell[1] <= int(region[5])


def choose_distance_point(cells, target, distance_range, y, rng, excluded=()):
    low, high = distance_range
    valid = []
    for cell in cells:
        if any(in_region(cell, region) for region in excluded):
            continue
        pos = point(cell, y)
        value = distance(pos, target)
        if low <= value <= high:
            valid.append((abs(value - (low + high) / 2.0), rng.random(), pos, value))
    if not valid:
        raise ValueError(f"No spawn point satisfies distance {distance_range} around {target}")
    valid.sort()
    _, _, pos, value = valid[0]
    return pos, round(value, 3)


def per_scene_counts(total):
    base, extra = divmod(total, SCENES_PER_DIFFICULTY)
    return [base + (1 if index < extra else 0) for index in range(SCENES_PER_DIFFICULTY)]


def decoration_cells(scene):
    return {
        (int(item["position"][0]), int(item["position"][2]))
        for item in scene.get("decorations", [])
    }


def build_elevator(scene, rng, task_id):
    constraints = scene["difficulty_constraints"]
    task = build_elevator_task(scene, rng, task_id)
    plate_target = center(scene["pressure_plate_region"])
    door_target = center(scene["door_region"])
    ox, oy, oz = scene["origin"]
    width, _, _ = scene["room_size"]
    divider_z = int(scene["door_region"][2])
    occupied = decoration_cells(scene)
    cells = [
        (x, z)
        for x in range(ox + 2, ox + width - 2)
        for z in range(oz + 2, divider_z)
        if (x, z) not in occupied
    ]
    a_start, a_distance = choose_distance_point(cells, plate_target, constraints["a_distance"], plate_target[1], rng, [scene["pressure_plate_region"]])
    b_cells = [cell for cell in cells if distance(point(cell, door_target[1]), a_start) >= 2.0]
    b_start, b_distance = choose_distance_point(b_cells, door_target, constraints["b_distance"], door_target[1], rng, [scene["pressure_plate_region"]])
    a_rotation, a_error = rotation_toward(a_start, door_target, constraints["a_angle"], rng)
    b_rotation, b_error = rotation_toward(b_start, door_target, constraints["b_angle"], rng)
    task["players"]["player_a"]["start_pos"] = a_start
    task["players"]["player_a"]["start_rotation"] = a_rotation
    task["players"]["player_a"]["goal"]["target_pos"] = plate_target
    task["players"]["player_b"]["start_pos"] = b_start
    task["players"]["player_b"]["start_rotation"] = b_rotation
    task["players"]["player_b"]["goal"]["target_pos"] = door_target
    metrics = {
        "player_a_target": "elevator_door_center",
        "player_a_distance": a_distance,
        "player_a_yaw_error_degrees": a_error,
        "pressure_plate_to_door_nominal_distance": scene["plate_offset"],
        "player_b_target": "elevator_door_center",
        "player_b_distance": b_distance,
        "player_b_yaw_error_degrees": b_error,
    }
    return task, metrics


def build_path(scene, rng, task_id):
    constraints = scene["difficulty_constraints"]
    task = build_pressure_path_task(scene, rng, task_id)
    plate_target = center(scene["pressure_plate_region"])
    path_region = scene["reveal_path_region"]
    solid = scene["solid_end_a_region"]
    walk_y = int(scene["pressure_plate_region"][1])
    occupied = decoration_cells(scene)
    cells = [cell for cell in cells_in_region(solid, inset=1) if cell not in occupied]
    a_start, a_distance = choose_distance_point(cells, plate_target, constraints["a_distance"], walk_y, rng, [scene["pressure_plate_region"]])
    near_edge_z = int(path_region[2]) - 1
    path_x0, path_x1 = int(path_region[0]), int(path_region[3])
    edge_max = int(constraints["path_b_edge_max"])
    b_candidates = [
        (x, z)
        for x in range(path_x0, path_x1 + 1)
        for z in range(near_edge_z - edge_max + 1, near_edge_z + 1)
        if (x, z) in cells and not in_region((x, z), scene["pressure_plate_region"])
    ]
    if not b_candidates:
        raise ValueError(f"{scene['scene_id']}: no B spawn near the path edge")
    b_cell = rng.choice(b_candidates)
    b_start = point(b_cell, walk_y)
    path_entry = [(path_region[0] + path_region[3]) / 2.0, float(walk_y), float(path_region[2])]
    b_edge_distance = int(path_region[2]) - b_cell[1]
    a_rotation, a_error = rotation_toward(a_start, plate_target, constraints["a_angle"], rng)
    b_rotation, b_error = rotation_toward(b_start, path_entry, [0.0, 20.0], rng)
    task["players"]["player_a"]["start_pos"] = a_start
    task["players"]["player_a"]["start_rotation"] = a_rotation
    task["players"]["player_a"]["goal"]["target_pos"] = plate_target
    task["players"]["player_b"]["start_pos"] = b_start
    task["players"]["player_b"]["start_rotation"] = b_rotation
    metrics = {
        "player_a_target": "pressure_plate_center",
        "player_a_distance": a_distance,
        "player_a_yaw_error_degrees": a_error,
        "player_b_target": "near_bank_path_edge",
        "player_b_bank_edge_distance": b_edge_distance,
        "player_b_yaw_error_degrees": b_error,
    }
    return task, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="generated_time_lock_difficulty/scene_manifest.json")
    parser.add_argument("--out", default="generated_time_lock_difficulty/generated_tasks.json")
    parser.add_argument("--seed", type=int, default=710)
    parser.add_argument("--task-type", choices=("all", "elevator", "path"), default="all")
    parser.add_argument("--dataset-name")
    args = parser.parse_args()
    base = CONSTRUCT_SCENE_ROOT
    manifest_path = base / args.manifest
    output_path = base / args.out
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    tasks = []
    task_id = 0
    template_options = {
        "all": ("elevator_hold_door", "pressure_path_reveal"),
        "elevator": ("elevator_hold_door",),
        "path": ("pressure_path_reveal",),
    }
    for template in template_options[args.task_type]:
        for difficulty in ("easy", "medium", "hard"):
            scenes = [scene for scene in manifest["scenes"] if scene["task_template"] == template and scene["difficulty"] == difficulty]
            if len(scenes) != SCENES_PER_DIFFICULTY:
                raise ValueError(
                    f"Expected {SCENES_PER_DIFFICULTY} scenes for {template}/{difficulty}, got {len(scenes)}"
                )
            for scene, count in zip(scenes, per_scene_counts(TIER_COUNTS[difficulty])):
                for _ in range(count):
                    builder = build_elevator if template == "elevator_hold_door" else build_path
                    task, metrics = builder(scene, rng, task_id)
                    task["difficulty"] = difficulty
                    task["difficulty_zh"] = scene["difficulty_zh"]
                    task["difficulty_constraints"] = scene["difficulty_constraints"]
                    task["spawn_metrics"] = metrics
                    tasks.append(task)
                    task_id += 1
    payload = {
        "dataset_name": args.dataset_name or f"时空互锁_{args.task_type}_难度梯队",
        "manifest_path": str(manifest_path.relative_to(base)),
        "namespace": manifest["namespace"],
        "task_count": len(tasks),
        "scene_count": len(manifest["scenes"]),
        "seed": args.seed,
        "tasks": tasks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(tasks)} tasks into {output_path}")


if __name__ == "__main__":
    main()
