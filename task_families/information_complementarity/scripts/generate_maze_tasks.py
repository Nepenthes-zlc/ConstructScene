#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


TIER_COUNTS = {"easy": 100, "medium": 100, "hard": 100}
SCENES_PER_DIFFICULTY = 15
A_YAW_OFFSETS = {
    "easy": [-35.0, -20.0, 18.0, 32.0],
    "medium": [-45.0, -28.0, 24.0, 42.0],
    "hard": [-65.0, -40.0, 35.0, 58.0],
}


def per_scene_counts(total):
    base, extra = divmod(total, SCENES_PER_DIFFICULTY)
    return [base + (1 if index < extra else 0) for index in range(SCENES_PER_DIFFICULTY)]


def center(region):
    return [(region[0] + region[3]) / 2.0, float(region[1]), (region[2] + region[5]) / 2.0]


def normalize_yaw(yaw):
    while yaw <= -180.0:
        yaw += 360.0
    while yaw > 180.0:
        yaw -= 360.0
    return round(yaw, 1)


def build_task(scene, task_id, repetition_index):
    goal_region = scene["goal_region"]
    goal_center = center(goal_region)
    agent_a_start = [float(value) for value in scene["agent_a_start_pos"]]
    agent_b_start = [float(value) for value in scene["agent_b_start_pos"]]
    base_a_yaw = float(scene["agent_a_start_rotation"][0])
    offsets = A_YAW_OFFSETS[scene["difficulty"]]
    a_yaw_offset = offsets[repetition_index % len(offsets)]
    agent_a_rotation = [normalize_yaw(base_a_yaw + a_yaw_offset), 0.0]
    return {
        "id": task_id,
        "scene_id": scene["scene_id"],
        "task_template": "maze_command_guidance",
        "scene_setup_function": scene["setup_function"],
        "scene_clear_function": scene["clear_function"],
        "task_description": "Agent A must walk through the two-block-wide maze corridor to the colored goal. Agent B flies at the top-center of the room, looks straight down at the maze, and guides Agent A.",
        "success_condition_logic": "all",
        "failure_condition_logic": "any",
        "failure_conditions": [],
        "players": {
            "player_a": {
                "role": "maze_walker",
                "start_pos": agent_a_start,
                "start_rotation": agent_a_rotation,
                "visibility_constraint": "maze_route_not_visible_from_above",
                "goal": {
                    "type": "reach_region",
                    "target_pos": goal_center,
                    "target_region": goal_region,
                    "description": "Follow Agent B's guidance and enter the colored goal region at the end of the maze.",
                },
            },
            "player_b": {
                "role": "overhead_maze_guide",
                "start_pos": agent_b_start,
                "start_rotation": [float(value) for value in scene["agent_b_start_rotation"]],
                "goal": {
                    "type": "guide_agent",
                    "target_agent": "player_a",
                    "target_pos": goal_center,
                    "target_region": goal_region,
                    "description": "Fly above the maze, observe the full route from a top-down view, and guide Agent A to the colored goal region.",
                },
            },
        },
        "success_conditions": [
            {
                "type": "player_in_region",
                "player": "player_a",
                "target_region": goal_region,
                "description": "Agent A has entered the colored maze goal region.",
            }
        ],
        "difficulty": scene["difficulty"],
        "difficulty_zh": scene["difficulty_zh"],
        "difficulty_constraints": scene["difficulty_constraints"],
        "spawn_metrics": {
            "player_a_target": "maze_goal_region",
            "player_a_goal_distance": round(math.hypot(agent_a_start[0] - goal_center[0], agent_a_start[2] - goal_center[2]), 3),
            "player_a_base_route_yaw": base_a_yaw,
            "player_a_yaw_offset_degrees": a_yaw_offset,
            "route_turn_count": scene["route_turn_count"],
            "route_straight_line_distance": scene["route_straight_line_distance"],
            "corridor_width": scene["maze_path_width"],
            "maze_wall_height": scene["maze_size"][1],
            "maze_walkable_area": scene["maze_walkable_area"],
            "target_walkable_area": scene["target_walkable_area"],
            "maze_wall_base_block": scene["maze_wall_base_block"],
            "maze_middle_layer_block": scene["maze_middle_layer_block"],
            "maze_middle_layer_lighting": scene["maze_middle_layer_lighting"],
            "player_b_position_mode": "flying_top_center_observer",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="final_data/maze/scene_manifest.json")
    parser.add_argument("--out", default="final_data/maze/generated_tasks.json")
    args = parser.parse_args()
    base = Path(__file__).resolve().parents[3]
    manifest_path = base / args.manifest
    output_path = base / args.out
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tasks = []
    task_id = 0
    for difficulty in ("easy", "medium", "hard"):
        scenes = [scene for scene in manifest["scenes"] if scene["difficulty"] == difficulty]
        if len(scenes) != SCENES_PER_DIFFICULTY:
            raise ValueError(f"Expected {SCENES_PER_DIFFICULTY} maze scenes for {difficulty}, got {len(scenes)}")
        for scene, count in zip(scenes, per_scene_counts(TIER_COUNTS[difficulty])):
            for repetition_index in range(count):
                tasks.append(build_task(scene, task_id, repetition_index))
                task_id += 1
    payload = {
        "dataset_name": "maze",
        "manifest_path": str(manifest_path.relative_to(base)),
        "namespace": manifest["namespace"],
        "task_count": len(tasks),
        "scene_count": len(manifest["scenes"]),
        "tasks": tasks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(tasks)} maze tasks into {output_path}")


if __name__ == "__main__":
    main()
