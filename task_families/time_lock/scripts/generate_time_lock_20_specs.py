#!/usr/bin/env python3
import json
from pathlib import Path


ELEVATOR_VARIANTS = [
    ([13, 6, 15], "white_concrete", "light_gray_concrete", "white_concrete", "black_concrete", 3, 3, 0, 4),
    ([15, 7, 17], "light_gray_concrete", "white_concrete", "quartz_block", "red_concrete", 3, 4, -2, 5),
    ([17, 8, 19], "quartz_block", "cyan_concrete", "white_concrete", "orange_concrete", 4, 4, 2, 4),
    ([14, 7, 18], "gray_concrete", "white_concrete", "light_gray_concrete", "yellow_concrete", 2, 3, -2, 5),
    ([18, 8, 20], "white_concrete", "blue_concrete", "quartz_block", "lime_concrete", 4, 4, 3, 4),
    ([16, 7, 21], "light_gray_concrete", "purple_concrete", "white_concrete", "cyan_concrete", 3, 4, -3, 5),
    ([19, 9, 17], "quartz_block", "orange_concrete", "light_gray_concrete", "blue_concrete", 4, 5, 4, 4),
    ([15, 8, 22], "white_concrete", "green_concrete", "quartz_block", "magenta_concrete", 3, 4, 1, 6),
    ([20, 7, 19], "light_gray_concrete", "red_concrete", "white_concrete", "purple_concrete", 5, 4, -4, 5),
    ([17, 9, 23], "gray_concrete", "yellow_concrete", "quartz_block", "white_concrete", 4, 5, 3, 6),
]

PATH_VARIANTS = [
    ([15, 7, 19], "white_concrete", "light_gray_concrete", "white_concrete", "lime_concrete", "black_concrete", 5, 2),
    ([17, 8, 21], "light_gray_concrete", "white_concrete", "quartz_block", "cyan_concrete", "gray_concrete", 5, 3),
    ([19, 9, 23], "quartz_block", "blue_concrete", "white_concrete", "yellow_concrete", "black_concrete", 6, 2),
    ([14, 8, 18], "gray_concrete", "white_concrete", "light_gray_concrete", "orange_concrete", "black_concrete", 5, 2),
    ([18, 7, 22], "white_concrete", "purple_concrete", "quartz_block", "magenta_concrete", "gray_concrete", 6, 3),
    ([16, 9, 20], "light_gray_concrete", "green_concrete", "white_concrete", "red_concrete", "black_concrete", 5, 2),
    ([20, 8, 24], "quartz_block", "orange_concrete", "light_gray_concrete", "blue_concrete", "gray_concrete", 6, 4),
    ([15, 9, 21], "white_concrete", "cyan_concrete", "quartz_block", "purple_concrete", "black_concrete", 5, 3),
    ([19, 7, 25], "light_gray_concrete", "red_concrete", "white_concrete", "green_concrete", "gray_concrete", 7, 2),
    ([17, 8, 23], "gray_concrete", "yellow_concrete", "quartz_block", "white_concrete", "black_concrete", 6, 3),
]


def block(name):
    return f"minecraft:{name}"


def elevator_spec(index, variant):
    size, floor, wall, ceiling, door, door_width, door_height, lateral, plate_offset = variant
    return {
        "id": f"time_lock_elevator_{index:02d}",
        "task_template": "elevator_hold_door",
        "notes": f"Elevator time-lock visual variant {index} of 10.",
        "origin": [0, -59, 0],
        "room_size": size,
        "divider_axis": "z",
        "floor_block": block(floor),
        "wall_block": block(wall),
        "ceiling_block": block(ceiling),
        "divider_block": block(wall),
        "elevator_block": block(door),
        "plate_pad_block": block(floor),
        "pressure_plate_block": "minecraft:stone_pressure_plate",
        "pressure_plate_active_state": "powered=true",
        "ceiling_light_block": "minecraft:glowstone",
        "ceiling_spotlight_block": "minecraft:glowstone",
        "ceiling_light_mode": "inner_ring_spotlight",
        "ceiling_light_size": [5, 5],
        "door_width": door_width,
        "door_height": door_height,
        "door_lateral_offset": lateral,
        "plate_offset": plate_offset,
        "pressure_plate_size": 3,
        "preserve_materials": True,
        "auto_contrast_materials": False,
    }


def path_spec(index, variant):
    size, floor, wall, ceiling, path, bottom, end_length, path_width = variant
    return {
        "id": f"time_lock_pressure_path_{index:02d}",
        "task_template": "pressure_path_reveal",
        "notes": f"Four-layer river-path visual variant {index} of 10.",
        "origin": [0, -58, 0],
        "room_size": size,
        "path_axis": "z",
        "floor_block": block(floor),
        "wall_block": block(wall),
        "ceiling_block": block(ceiling),
        "foundation_block": block(floor),
        "bottom_layer_block": block(bottom),
        "pressure_plate_block": "minecraft:stone_pressure_plate",
        "pressure_plate_active_state": "powered=true",
        "reveal_path_block": block(path),
        "inactive_path_block": "minecraft:air",
        "goal_marker_block": "minecraft:gold_block",
        "ceiling_light_block": "minecraft:glowstone",
        "ceiling_spotlight_block": "minecraft:glowstone",
        "ceiling_light_mode": "inner_ring_spotlight",
        "ceiling_light_size": [5, 5],
        "foundation_thickness": 4,
        "solid_end_length": end_length,
        "reveal_path_width": path_width,
        "pressure_plate_size": 3,
        "plate_offset_from_gap": 2,
    }


def main():
    specs = [elevator_spec(index, item) for index, item in enumerate(ELEVATOR_VARIANTS, 1)]
    specs.extend(path_spec(index, item) for index, item in enumerate(PATH_VARIANTS, 1))
    output = Path(__file__).resolve().parents[1] / "scene_specs" / "time_lock_20_scenes.json"
    output.write_text(json.dumps(specs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(specs)} scene specs to {output}")


if __name__ == "__main__":
    main()
