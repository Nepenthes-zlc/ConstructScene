#!/usr/bin/env python3
import json
import random
from pathlib import Path


PALETTES = [
    ("stone_pressure_plate", "red_concrete", "lime_concrete"),
    ("polished_blackstone_pressure_plate", "orange_concrete", "cyan_concrete"),
    ("oak_pressure_plate", "yellow_concrete", "blue_concrete"),
    ("spruce_pressure_plate", "lime_concrete", "magenta_concrete"),
    ("birch_pressure_plate", "cyan_concrete", "red_concrete"),
    ("jungle_pressure_plate", "blue_concrete", "yellow_concrete"),
    ("acacia_pressure_plate", "magenta_concrete", "green_concrete"),
    ("dark_oak_pressure_plate", "purple_concrete", "orange_concrete"),
    ("mangrove_pressure_plate", "green_concrete", "purple_concrete"),
    ("cherry_pressure_plate", "pink_concrete", "blue_concrete"),
]
SCENE_PALETTES = PALETTES + PALETTES[:5]
ELEVATOR_DOOR_COLORS = [
    "light_gray_concrete",
    "gray_concrete",
    "black_concrete",
    "brown_concrete",
    "light_blue_concrete",
]
DECORATION_BLOCKS = [
    "minecraft:bookshelf",
    "minecraft:chest",
    "minecraft:crafting_table",
    "minecraft:furnace",
    "minecraft:stone_slab[type=bottom]",
    "minecraft:oak_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]",
]

TIERS = {
    "easy": {
        "zh": "简单",
        "count": 100,
        "plate": 4,
        "door_width": 3,
        "plate_door_distance": [4, 5],
        "plate_door_distance_average": 4.5,
        "path_width": 4,
        "path_length": 4,
        "a_distance": [2.5, 3.5],
        "a_angle": [0.0, 30.0],
        "b_distance": [2.5, 3.5],
        "b_angle": [15.0, 20.0],
        "path_b_edge_max": 2,
    },
    "medium": {
        "zh": "中等",
        "count": 100,
        "plate": 3,
        "door_width": 2,
        "plate_door_distance": [5, 6],
        "plate_door_distance_average": 5.5,
        "path_width": 3,
        "path_length": 5,
        "a_distance": [2.5, 4.5],
        "a_angle": [0.0, 40.0],
        "b_distance": [3.5, 5.5],
        "b_angle": [25.0, 35.0],
        "path_b_edge_max": 2,
    },
    "hard": {
        "zh": "困难",
        "count": 100,
        "plate": 3,
        "door_width": 2,
        "plate_door_distance": [5, 6],
        "plate_door_distance_average": 5.5,
        "path_width": 3,
        "path_length": 6,
        "a_distance": [4.5, 7.5],
        "a_angle": [0.0, 45.0],
        "b_distance": [3.5, 7.5],
        "b_angle": [20.0, 40.0],
        "path_b_edge_max": 3,
    },
}

ELEVATOR_TIERS = {
    **TIERS,
    "medium": {
        **TIERS["medium"],
        "plate_door_distance": [4, 5],
        "plate_door_distance_average": 4.5,
        "a_distance": [2.5, 3.5],
        "a_angle": [0.0, 30.0],
        "b_distance": [2.5, 3.5],
        "b_angle": [15.0, 20.0],
    },
    "hard": {
        **TIERS["hard"],
        "a_distance": [3.5, 7.5],
        "b_distance": [3.5, 7.5],
        "b_angle": [20.0, 40.0],
    },
}


def block(name):
    return f"minecraft:{name}"


def decorations_for(template, difficulty, index, width, depth, plate_center, plate_size, path_length=None):
    rng = random.Random(f"time-lock-decor-v1:{template}:{difficulty}:{index}")
    count = rng.randint(3, 5)
    if template == "elevator_hold_door":
        boundary = depth // 2
    else:
        interior_length = depth - 2
        remaining_length = interior_length - int(path_length)
        boundary = 1 + remaining_length // 2
    candidates = []
    for x in range(2, width - 2):
        for z in range(2, boundary - 1):
            if x not in {2, width - 3} and z != 2:
                continue
            lower = (plate_size - 1) // 2
            px0, pz0 = plate_center[0] - lower, plate_center[1] - lower
            px1, pz1 = px0 + plate_size - 1, pz0 + plate_size - 1
            if px0 - 1 <= x <= px1 + 1 and pz0 - 1 <= z <= pz1 + 1:
                continue
            candidates.append((x, z))
    selected = rng.sample(candidates, count)
    return [
        {"block": rng.choice(DECORATION_BLOCKS), "relative_pos": [x, z]}
        for x, z in selected
    ]


def common(scene_id, template, palette, difficulty, index):
    pressure_plate, accent, path = palette
    tiers = ELEVATOR_TIERS if template == "elevator_hold_door" else TIERS
    tier = tiers[difficulty]
    return {
        "id": scene_id,
        "task_template": template,
        "difficulty": difficulty,
        "difficulty_zh": tier["zh"],
        "notes": f"{tier['zh']} difficulty variant {index} of 15 with 3-5 decorations.",
        "origin": [0, -59 if template == "elevator_hold_door" else -58, 0],
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
        "pressure_plate_block": block(pressure_plate),
        "pressure_plate_active_state": "powered=true",
        "pressure_plate_size": tier["plate"],
        "difficulty_constraints": tier,
        "_accent": accent,
        "_path": path,
    }


def elevator_spec(difficulty, index, palette):
    tier = ELEVATOR_TIERS[difficulty]
    pressure_plate, _, path = palette
    door_color = ELEVATOR_DOOR_COLORS[(index - 1) % len(ELEVATOR_DOOR_COLORS)]
    palette = (pressure_plate, door_color, path)
    plate_door_distance = tier["plate_door_distance"][(index - 1) % 2]
    item = common(f"tier_elevator_{difficulty}_{index:02d}", "elevator_hold_door", palette, difficulty, index)
    room_size = [21 + index % 3, 8, 23 + index % 2]
    plate_lateral_offset = ((index * 2) % 5) - 2
    item.update({
        "room_size": room_size,
        "divider_axis": "z",
        "divider_block": item["wall_block"],
        "elevator_block": block(item.pop("_accent")),
        "plate_pad_block": item["floor_block"],
        "door_width": tier["door_width"],
        "door_height": 3,
        "door_lateral_offset": (index % 3) - 1,
        "plate_lateral_offset": plate_lateral_offset,
        "plate_offset": plate_door_distance,
        "min_plate_door_clearance": 1.0,
        "preserve_materials": True,
        "auto_contrast_materials": False,
    })
    item["decorations"] = decorations_for(
        "elevator_hold_door", difficulty, index, room_size[0], room_size[2],
        (room_size[0] // 2 + plate_lateral_offset, room_size[2] // 2 - plate_door_distance),
        tier["plate"],
    )
    item.pop("_path")
    return item


def path_spec(difficulty, index, palette):
    tier = TIERS[difficulty]
    item = common(f"tier_path_{difficulty}_{index:02d}", "pressure_path_reveal", palette, difficulty, index)
    room_size = [21 + index % 3, 8, 31 + index % 2]
    interior_length = room_size[2] - 2
    gap_z0 = 1 + (interior_length - tier["path_length"]) // 2
    plate_center = (room_size[0] // 2, max(2, gap_z0 - 4))
    item.update({
        "room_size": room_size,
        "path_axis": "z",
        "foundation_block": item["floor_block"],
        "bottom_layer_block": "minecraft:black_concrete",
        "reveal_path_block": block(item.pop("_path")),
        "inactive_path_block": "minecraft:air",
        "goal_marker_block": "minecraft:gold_block",
        "foundation_thickness": 4,
        "solid_end_length": 10,
        "reveal_path_width": tier["path_width"],
        "reveal_path_length": tier["path_length"],
        "plate_offset_from_gap": 4,
    })
    item["decorations"] = decorations_for(
        "pressure_path_reveal", difficulty, index, room_size[0], room_size[2],
        plate_center, tier["plate"], tier["path_length"],
    )
    item.pop("_accent")
    return item


def main():
    specs_by_template = {"elevator": [], "path": []}
    for template in specs_by_template:
        for difficulty in ("easy", "medium", "hard"):
            palettes = SCENE_PALETTES if template == "path" else [
                PALETTES[(((index - 1) % 5) * 2 + (index - 1) // 5) % len(PALETTES)]
                for index in range(1, 16)
            ]
            for index, palette in enumerate(palettes, 1):
                builder = elevator_spec if template == "elevator" else path_spec
                spec = builder(difficulty, index, palette)
                if template == "path":
                    spec["origin"][0] = 900
                specs_by_template[template].append(spec)

    output_dir = Path(__file__).resolve().parents[1] / "scene_specs"
    outputs = {
        "elevator": output_dir / "time_lock_elevator_decorated_45_scenes.json",
        "path": output_dir / "time_lock_path_decorated_45_scenes.json",
    }
    for template, output in outputs.items():
        specs = specs_by_template[template]
        output.write_text(json.dumps(specs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(specs)} {template} scene specs to {output}")

    combined = specs_by_template["elevator"] + specs_by_template["path"]
    combined_output = output_dir / "time_lock_decorated_90_scenes.json"
    combined_output.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(combined)} combined scene specs to {combined_output}")


if __name__ == "__main__":
    main()
