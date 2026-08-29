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


def normalize_yaw(value):
    return (value + 180.0) % 360.0 - 180.0


def spawn_pair(scene, rng, geometry_mode):
    center = [float(value) for value in scene["target_center"]]
    low, high = scene["difficulty_constraints"]["a_distance"]
    distance = rng.uniform(float(low), float(high))
    angle_degrees = float(scene["spawn_angle_degrees"]) + rng.uniform(-8.0, 8.0)
    angle_radians = math.radians(angle_degrees)
    offset = [distance * math.sin(angle_radians), 0.0, distance * math.cos(angle_radians)]
    agent_a = [center[0] - offset[0], center[1], center[2] - offset[2]]
    if geometry_mode == "collinear":
        agent_b = [center[0] + offset[0], center[1], center[2] + offset[2]]
    else:
        triangle_angle = math.radians(angle_degrees + rng.choice((-65.0, 65.0)))
        agent_b = [
            center[0] + distance * math.sin(triangle_angle),
            center[1],
            center[2] + distance * math.cos(triangle_angle),
        ]
    return center, agent_a, agent_b, distance, angle_degrees


def build_task(scene, task_id, rng, geometry_mode):
    center, agent_a, agent_b, distance, angle_degrees = spawn_pair(scene, rng, geometry_mode)
    target_region = scene["target_region"]
    max_error = float(scene["difficulty_constraints"].get("a_yaw_max", 0.0))
    a_yaw_error = rng.uniform(-max_error, max_error) if max_error else 0.0
    a_rotation = [round(normalize_yaw(yaw_toward(agent_a, center) + a_yaw_error), 1), 0.0]
    b_rotation = [yaw_toward(agent_b, agent_a), 0.0]
    return {
        "id": task_id,
        "scene_id": scene["scene_id"],
        "task_template": "truck_driver",
        "scene_setup_function": scene["setup_function"],
        "scene_clear_function": scene["clear_function"],
        "task_description": "Agent A is a blind truck driver who must reach the colored target area. Agent B can see the target and must guide Agent A.",
        "success_condition_logic": "all",
        "failure_condition_logic": "any",
        "failure_conditions": [],
        "players": {
            "player_a": {
                "role": "blind_truck_driver",
                "start_pos": agent_a,
                "start_rotation": a_rotation,
                "visibility_constraint": "target_location_and_color_hidden",
                "goal": {
                    "type": "reach_region",
                    "target_pos": center,
                    "target_region": target_region,
                    "description": "Follow Agent B's guidance and enter the colored target region.",
                },
            },
            "player_b": {
                "role": "navigator",
                "start_pos": agent_b,
                "start_rotation": b_rotation,
                "goal": {
                    "type": "guide_agent",
                    "target_agent": "player_a",
                    "target_pos": center,
                    "target_region": target_region,
                    "description": "Observe the target and guide Agent A into it.",
                },
            },
        },
        "success_conditions": [
            {
                "type": "player_in_region",
                "player": "player_a",
                "target_region": target_region,
                "description": "Agent A has entered the colored target region.",
            }
        ],
        "difficulty": scene["difficulty"],
        "difficulty_zh": scene["difficulty_zh"],
        "difficulty_constraints": scene["difficulty_constraints"],
        "spawn_metrics": {
            "player_a_target": "target_region_center",
            "player_a_distance": distance,
            "player_a_yaw_error_degrees": round(abs(a_yaw_error), 3),
            "player_b_target": "player_a",
            "player_b_yaw_error_degrees": 0.0,
            "geometry_mode": geometry_mode,
            "collinear": geometry_mode == "collinear",
            "target_between_agents": geometry_mode == "collinear",
            "spawn_angle_degrees": angle_degrees,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="final_data/truck/scene_manifest.json")
    parser.add_argument("--out", default="final_data/truck/generated_tasks.json")
    args = parser.parse_args()
    base = Path(__file__).resolve().parents[3]
    manifest_path = base / args.manifest
    output_path = base / args.out
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rng = random.Random(820)
    tasks = []
    task_id = 0
    for difficulty in ("easy", "medium", "hard"):
        scenes = [scene for scene in manifest["scenes"] if scene["difficulty"] == difficulty]
        if len(scenes) != SCENES_PER_DIFFICULTY:
            raise ValueError(f"Expected {SCENES_PER_DIFFICULTY} truck scenes for {difficulty}, got {len(scenes)}")
        constraints = scenes[0]["difficulty_constraints"]
        collinear_count = int(constraints.get("collinear_count", TIER_COUNTS[difficulty]))
        triangle_count = int(constraints.get("triangle_count", 0))
        geometry_modes = ["collinear"] * collinear_count + ["triangle"] * triangle_count
        if len(geometry_modes) != TIER_COUNTS[difficulty]:
            raise ValueError(f"Geometry counts for {difficulty} must total {TIER_COUNTS[difficulty]}.")
        rng.shuffle(geometry_modes)
        mode_index = 0
        for scene, count in zip(scenes, per_scene_counts(TIER_COUNTS[difficulty])):
            for _ in range(count):
                tasks.append(build_task(scene, task_id, rng, geometry_modes[mode_index]))
                task_id += 1
                mode_index += 1
    payload = {
        "dataset_name": "truck",
        "manifest_path": str(manifest_path.relative_to(base)),
        "namespace": manifest["namespace"],
        "task_count": len(tasks),
        "scene_count": len(manifest["scenes"]),
        "tasks": tasks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(tasks)} truck tasks into {output_path}")


if __name__ == "__main__":
    main()
