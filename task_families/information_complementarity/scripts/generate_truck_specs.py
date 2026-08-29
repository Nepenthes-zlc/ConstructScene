#!/usr/bin/env python3
import json
import random
from pathlib import Path


COLORS = [
    "red_concrete",
    "orange_concrete",
    "yellow_concrete",
    "lime_concrete",
    "green_concrete",
    "cyan_concrete",
    "light_blue_concrete",
    "blue_concrete",
    "purple_concrete",
    "magenta_concrete",
]
SCENE_COLORS = COLORS + COLORS[:5]
DECORATION_BLOCKS = [
    "minecraft:bookshelf", "minecraft:chest", "minecraft:crafting_table",
    "minecraft:furnace", "minecraft:stone_slab[type=bottom]",
    "minecraft:oak_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]",
]

TIERS = {
    "easy": {"zh": "简单", "count": 100, "target_size": 4, "a_distance": [3.5, 4.5], "spawn_distance": 4.0},
    "medium": {"zh": "中等", "count": 100, "target_size": 3, "a_distance": [4.5, 6.5], "a_yaw_max": 15.0, "collinear_count": 67, "triangle_count": 33},
    "hard": {"zh": "困难", "count": 100, "target_size": 2, "a_distance": [5.5, 7.5], "a_yaw_max": 30.0, "collinear_count": 50, "triangle_count": 50},
}


def decorations_for(difficulty, index, width, depth):
    rng = random.Random(f"truck-decor-v1:{difficulty}:{index}")
    candidates = [(2, z) for z in range(2, depth - 2)] + [(width - 3, z) for z in range(2, depth - 2)]
    selected = rng.sample(candidates, rng.randint(10, 15))
    return [{"block": rng.choice(DECORATION_BLOCKS), "relative_pos": list(pos)} for pos in selected]


def main():
    specs = []
    for difficulty in ("easy", "medium", "hard"):
        tier = TIERS[difficulty]
        for index, color in enumerate(SCENE_COLORS, 1):
            room_size = [23 + index % 2, 8, 23 + (index + 1) % 2]
            specs.append(
                {
                    "id": f"truck_{difficulty}_{index:02d}",
                    "task_template": "truck_driver",
                    "difficulty": difficulty,
                    "difficulty_zh": tier["zh"],
                    "difficulty_constraints": tier,
                    "origin": [1800, -58, 0],
                    "room_size": room_size,
                    "wall_backing_thickness": 1,
                    "wall_backing_block": "minecraft:white_concrete",
                    "floor_block": "minecraft:white_concrete",
                    "wall_block": "minecraft:white_concrete",
                    "ceiling_block": "minecraft:white_concrete",
                    "ceiling_light_block": "minecraft:glowstone",
                    "ceiling_spotlight_block": "minecraft:glowstone",
                    "ceiling_light_mode": "inner_ring_spotlight",
                    "ceiling_spotlight_width": 3,
                    "ceiling_light_size": [5, 5],
                    "parking_block": f"minecraft:{color}",
                    "target_size": tier["target_size"],
                    "spawn_angle_degrees": (index - 1) * 24,
                    "decorations": decorations_for(difficulty, index, room_size[0], room_size[2]),
                }
            )

    output = Path(__file__).resolve().parents[1] / "scene_specs" / "truck_decorated_45_scenes.json"
    output.write_text(json.dumps(specs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(specs)} truck scene specs to {output}")


if __name__ == "__main__":
    main()
