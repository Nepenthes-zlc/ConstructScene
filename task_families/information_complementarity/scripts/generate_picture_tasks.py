#!/usr/bin/env python3
import argparse
import json
import math
import random
from pathlib import Path


TIER_COUNTS = {"easy": 100, "medium": 100, "hard": 100}
SCENES_PER_DIFFICULTY = 15


def per_scene_counts(total):
    base, extra = divmod(total, SCENES_PER_DIFFICULTY)
    return [base + (1 if index < extra else 0) for index in range(SCENES_PER_DIFFICULTY)]


def yaw_toward(start, target):
    return round(math.degrees(math.atan2(-(target[0] - start[0]), target[2] - start[2])), 1)


def center(region):
    return [(region[0] + region[3]) / 2.0, float(region[1]), (region[2] + region[5]) / 2.0]


def choose_agent_a_spawn(scene, target_center, rng, used_positions):
    platform = scene["platform_region"]
    low, high = scene["difficulty_constraints"]["a_distance"]
    occupied = {
        (int(item["position"][0]), int(item["position"][2]))
        for item in scene.get("decorations", [])
    }
    candidates = []
    for x in range(int(platform[0]), int(platform[3]) + 1):
        for z in range(int(platform[2]), int(platform[5]) + 1):
            if (x, z) in occupied:
                continue
            position = [x + 0.5, float(scene["platform_walk_y"]), z + 0.5]
            distance = math.hypot(position[0] - target_center[0], position[2] - target_center[2])
            if low <= distance <= high:
                angle = math.degrees(math.atan2(position[2] - target_center[2], position[0] - target_center[0])) % 360.0
                candidates.append((position, distance, angle))
    if not candidates:
        raise ValueError(f"{scene['scene_id']}: no high-platform spawn satisfies distance {low}-{high}.")
    unused = [candidate for candidate in candidates if tuple(candidate[0]) not in used_positions]
    selected = rng.choice(unused or candidates)
    used_positions.add(tuple(selected[0]))
    return selected


def build_task(scene, task_id, rng, used_positions):
    target_region = scene["target_region"]
    target_center = center(target_region)
    agent_a, distance, spawn_angle = choose_agent_a_spawn(scene, target_center, rng, used_positions)
    agent_b = [float(value) for value in scene["agent_b_start_pos"]]
    return {
        "id": task_id,
        "scene_id": scene["scene_id"],
        "task_template": "high_platform_gold_guidance",
        "scene_setup_function": scene["setup_function"],
        "scene_clear_function": scene["clear_function"],
        "task_description": "Agent A stands on the high platform and cannot see the colored region below. Agent B can see all information and must guide Agent A directly above the colored region.",
        "success_condition_logic": "all",
        "failure_condition_logic": "any",
        "players": {
            "player_a": {
                "role": "elevated_picture_placer",
                "start_pos": agent_a,
                "start_rotation": [yaw_toward(agent_a, target_center), 0.0],
                "visibility_constraint": "colored_region_below_platform_hidden",
                "goal": {
                    "type": "reach_region",
                    "target_pos": target_center,
                    "target_region": target_region,
                    "description": "Follow Agent B's guidance and stand directly above the colored region.",
                },
            },
            "player_b": {
                "role": "full_information_guide",
                "start_pos": agent_b,
                "start_rotation": [float(value) for value in scene["agent_b_start_rotation"]],
                "goal": {
                    "type": "guide_agent",
                    "target_agent": "player_a",
                    "target_pos": target_center,
                    "target_region": target_region,
                    "description": "Observe all scene information and guide Agent A directly above the colored region.",
                },
            },
        },
        "success_conditions": [
            {
                "type": "player_in_region",
                "player": "player_a",
                "target_region": target_region,
                "description": "Agent A is directly above the full colored region footprint.",
            }
        ],
        "failure_conditions": [
            {
                "type": "player_below_y",
                "player": "player_a",
                "y_below": scene["platform_walk_y"],
                "comparison": "less_than",
                "description": "Agent A has fallen below the high-platform walking level.",
            }
        ],
        "difficulty": scene["difficulty"],
        "difficulty_zh": scene["difficulty_zh"],
        "difficulty_constraints": scene["difficulty_constraints"],
        "spawn_metrics": {
            "player_a_target": "colored_region_center_above_platform",
            "player_a_distance": distance,
            "player_a_yaw_error_degrees": 0.0,
            "player_a_spawn_angle_degrees": round(spawn_angle, 3),
            "player_b_position_mode": "fixed_relative_central_observer",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="final_data/picture/scene_manifest.json")
    parser.add_argument("--out", default="final_data/picture/generated_tasks.json")
    args = parser.parse_args()
    base = Path(__file__).resolve().parents[3]
    manifest_path = base / args.manifest
    output_path = base / args.out
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rng = random.Random(715)
    tasks = []
    task_id = 0
    for difficulty in ("easy", "medium", "hard"):
        scenes = [scene for scene in manifest["scenes"] if scene["difficulty"] == difficulty]
        if len(scenes) != SCENES_PER_DIFFICULTY:
            raise ValueError(f"Expected {SCENES_PER_DIFFICULTY} picture scenes for {difficulty}, got {len(scenes)}")
        for scene, count in zip(scenes, per_scene_counts(TIER_COUNTS[difficulty])):
            used_positions = set()
            for _ in range(count):
                tasks.append(build_task(scene, task_id, rng, used_positions))
                task_id += 1
    payload = {
        "dataset_name": "picture",
        "manifest_path": str(manifest_path.relative_to(base)),
        "namespace": manifest["namespace"],
        "task_count": len(tasks),
        "scene_count": len(manifest["scenes"]),
        "tasks": tasks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(tasks)} picture tasks into {output_path}")


if __name__ == "__main__":
    main()
