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
    "easy": {"zh": "简单", "count": 100, "region_size": 5, "a_distance": [3.5, 5.5], "spawn_distance": 5.0},
    "medium": {"zh": "中等", "count": 100, "region_size": 4, "a_distance": [3.5, 5.5], "spawn_distance": 5.0},
    "hard": {"zh": "困难", "count": 100, "region_size": 3, "a_distance": [5.5, 7.5], "spawn_distance": 6.5},
}


def decorations_for(difficulty, index, region_offset, region_size):
    rng = random.Random(f"picture-decor-v1:{difficulty}:{index}")
    tx, tz = region_offset
    target_cells = {
        (x, z)
        for x in range(tx, tx + region_size)
        for z in range(tz, tz + region_size)
    }
    candidates = [
        (x, z)
        for x in range(1, 16)
        for z in range(1, 6)
        if (x, z) not in target_cells
    ]
    selected = rng.sample(candidates, rng.randint(3, 7))
    return [
        {"block": rng.choice(DECORATION_BLOCKS), "relative_pos": list(pos), "relative_y": 7}
        for pos in selected
    ]


def main():
    rng = random.Random(715)
    specs = []
    for difficulty in ("easy", "medium", "hard"):
        tier = TIERS[difficulty]
        size = tier["region_size"]
        distance = tier["spawn_distance"]
        for index, color in enumerate(SCENE_COLORS, 1):
            direction = 1 if index % 2 else -1
            min_center_x = 1 + (size - 1) / 2.0
            max_center_x = 15 - (size - 1) / 2.0
            if direction == 1:
                center_x_max = max_center_x - distance
                center_x = rng.uniform(min_center_x, center_x_max)
            else:
                center_x_min = min_center_x + distance
                center_x = rng.uniform(center_x_min, max_center_x)
            offset_x = round(center_x - (size - 1) / 2.0)
            offset_z = 1 if size == 5 else 1 + (index % 2)
            specs.append(
                {
                    "id": f"picture_{difficulty}_{index:02d}",
                    "task_template": "high_platform_gold_guidance",
                    "difficulty": difficulty,
                    "difficulty_zh": tier["zh"],
                    "difficulty_constraints": tier,
                    "origin": [2800, -58, 0],
                    "room_size": [17, 11, 19],
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
                    "platform_block": "minecraft:smooth_stone",
                    "platform_underlight_block": "minecraft:glowstone",
                    "fence_block": "minecraft:oak_fence",
                    "gold_block": f"minecraft:{color}",
                    "platform_height": 6,
                    "platform_width": 5,
                    "target_span": 3,
                    "side_path_enabled": False,
                    "hidden_region_size": [size, size],
                    "hidden_region_offset": [offset_x, offset_z],
                    "agent_a_direction": direction,
                    "observer_relative_pos": [8.5, 7.0, 10.5],
                    "observer_platform_relative_pos": [8.5, 7.0, 10.5],
                    "observer_rotation": [179.0, 26.0],
                    "observer_support_block": "minecraft:smooth_stone",
                    "observer_platform_size": [1, 1],
                    "decorations": decorations_for(difficulty, index, [offset_x, offset_z], size),
                }
            )

    output = Path(__file__).resolve().parents[1] / "scene_specs" / "picture_decorated_45_scenes.json"
    output.write_text(json.dumps(specs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(specs)} picture scene specs to {output}")


if __name__ == "__main__":
    main()
