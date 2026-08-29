#!/usr/bin/env python3
"""Batch-generate multi-agent Minecraft scenes as mcfunction files."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


DEFAULT_NAMESPACE = "multiagent_scene"
DEFAULT_PACK_NAME = "multiagent_scene_pack"
DEFAULT_PACK_FORMAT = 48
DEFAULT_SUPPORTED_FORMATS = [48, 81]
FUNCTION_DIR_NAMES = ("function", "functions")
DEFAULT_SCENE_GAP = 8

BLOCK_RGB = {
    "minecraft:white_concrete": (230, 235, 235),
    "minecraft:light_gray_concrete": (125, 125, 115),
    "minecraft:gray_concrete": (55, 58, 62),
    "minecraft:black_concrete": (8, 10, 15),
    "minecraft:red_concrete": (140, 30, 30),
    "minecraft:orange_concrete": (220, 105, 20),
    "minecraft:yellow_concrete": (240, 175, 35),
    "minecraft:lime_concrete": (95, 170, 25),
    "minecraft:green_concrete": (70, 90, 35),
    "minecraft:cyan_concrete": (20, 120, 135),
    "minecraft:blue_concrete": (45, 55, 160),
    "minecraft:purple_concrete": (100, 35, 150),
    "minecraft:magenta_concrete": (170, 50, 160),
    "minecraft:stone_pressure_plate": (125, 125, 125),
    "minecraft:polished_blackstone_pressure_plate": (25, 22, 28),
    "minecraft:birch_pressure_plate": (205, 185, 120),
    "minecraft:quartz_block": (235, 230, 220),
    "minecraft:gold_block": (245, 190, 35),
    "minecraft:lapis_block": (25, 65, 180),
}

HIGH_CONTRAST_ELEVATOR_PALETTES = [
    # Uniform light shell (floor + walls + divider + ceiling) with distinct
    # target colors: a BLACK elevator door and a GRAY pressure plate. No separate
    # pressure-plate pad is used; the plate sits directly on the normal floor.
    {
        "floor_block": "minecraft:white_concrete",
        "wall_block": "minecraft:white_concrete",
        "divider_block": "minecraft:white_concrete",
        "ceiling_block": "minecraft:white_concrete",
        "plate_pad_block": "minecraft:white_concrete",
        "pressure_plate_block": "minecraft:stone_pressure_plate",
        "elevator_block": "minecraft:black_concrete",
    },
]



@dataclass(frozen=True)
class Vec3:
    x: int
    y: int
    z: int

    def shift(self, dx: int = 0, dy: int = 0, dz: int = 0) -> "Vec3":
        return Vec3(self.x + dx, self.y + dy, self.z + dz)

    def to_cmd(self) -> str:
        return f"{self.x} {self.y} {self.z}"


def fill_cmd(start: Vec3, end: Vec3, block: str) -> str:
    return f"fill {start.to_cmd()} {end.to_cmd()} {block}"


def setblock_cmd(pos: Vec3, block: str) -> str:
    return f"setblock {pos.to_cmd()} {block}"


def region_positions(min_pos: Vec3, max_pos: Vec3) -> List[Vec3]:
    return [
        Vec3(x, y, z)
        for x in range(min_pos.x, max_pos.x + 1)
        for y in range(min_pos.y, max_pos.y + 1)
        for z in range(min_pos.z, max_pos.z + 1)
    ]


def say_cmd(text: str) -> str:
    escaped = text.replace('"', '\\"')
    return f'tellraw @a {{"text":"{escaped}","color":"yellow"}}'


def sanitize_name(name: str) -> str:
    allowed = []
    for char in name.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "scene"


def material_suffix(block: str) -> str:
    return sanitize_name(block.split(":")[-1])


def short_variant_token(value: str, limit: int = 10) -> str:
    parts = [part for part in sanitize_name(value).split("_") if part]
    if not parts:
        return "v"
    token = "".join(part[:2] for part in parts[: min(3, len(parts))])
    return token[:limit] or "v"


def make_variant_scene_id(base_id: str, variant_key: str, index: int) -> str:
    digest = hashlib.sha1(variant_key.encode("utf-8")).hexdigest()[:8]
    return f"{base_id}__v{index:02d}_{digest}"


def relativize_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_function_file(datapack_root: Path, namespace: str, relative_path: Path, content: str) -> None:
    for dir_name in FUNCTION_DIR_NAMES:
        write_text(datapack_root / "data" / namespace / dir_name / relative_path, content)


def add_decorations(
    spec: Dict[str, Any], common: Dict[str, Any], setup_lines: List[str]
) -> List[Dict[str, Any]]:
    """Place spec-defined, floor-level decorative blocks using room-relative coordinates."""
    decorations = spec.get("decorations", [])
    if not isinstance(decorations, list):
        raise ValueError(f"{common['scene_id']}: decorations must be a list.")

    ox, oy, oz = common["origin"].x, common["origin"].y, common["origin"].z
    width, _, depth = common["room_size"]
    placed: List[Dict[str, Any]] = []
    occupied = set()
    for decoration in decorations:
        if not isinstance(decoration, dict):
            raise ValueError(f"{common['scene_id']}: each decoration must be an object.")
        relative_pos = decoration.get("relative_pos")
        if not isinstance(relative_pos, list) or len(relative_pos) != 2:
            raise ValueError(f"{common['scene_id']}: decoration.relative_pos must be [x, z].")
        relative_x, relative_z = (int(value) for value in relative_pos)
        if not (1 <= relative_x < width - 1 and 1 <= relative_z < depth - 1):
            raise ValueError(f"{common['scene_id']}: decoration is outside the room interior.")
        relative_y = int(decoration.get("relative_y", 1))
        position = Vec3(ox + relative_x, oy + relative_y, oz + relative_z)
        key = (position.x, position.y, position.z)
        if key in occupied:
            raise ValueError(f"{common['scene_id']}: duplicate decoration position {key}.")
        occupied.add(key)
        block = str(decoration.get("block", "minecraft:bookshelf"))
        setup_lines.append(setblock_cmd(position, block))
        placed.append({"block": block, "position": [position.x, position.y, position.z]})
    return placed


def load_specs(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("Spec file must be a JSON list.")
    return data


def validate_size(size: Iterable[Any], key: str) -> Tuple[int, int, int]:
    values = list(size)
    if len(values) != 3 or not all(isinstance(v, int) for v in values):
        raise ValueError(f"{key} must be [int, int, int].")
    return values[0], values[1], values[2]


def validate_size_2(size: Iterable[Any], key: str) -> Tuple[int, int]:
    values = list(size)
    if len(values) != 2 or not all(isinstance(v, int) for v in values):
        raise ValueError(f"{key} must be [int, int].")
    return values[0], values[1]


def get_required_int(spec: Dict[str, Any], key: str) -> int:
    value = spec.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an int.")
    return value


def normalize_options(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return value
    raise ValueError("Block option must be a string or a non-empty list of strings.")


def block_rgb(block: str) -> Tuple[int, int, int]:
    return BLOCK_RGB.get(str(block), (128, 128, 128))


def color_distance(left: str, right: str) -> float:
    a = block_rgb(left)
    b = block_rgb(right)
    return round(sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5, 2)


def luminance(block: str) -> float:
    r, g, b = block_rgb(block)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def visual_contrast_summary(spec: Dict[str, Any]) -> Dict[str, Any]:
    floor = str(spec.get("floor_block", "minecraft:smooth_stone"))
    pad = str(spec.get("plate_pad_block", floor))
    plate = str(spec.get("pressure_plate_block", "minecraft:stone_pressure_plate"))
    wall = str(spec.get("divider_block", spec.get("wall_block", "minecraft:white_concrete")))
    door = str(spec.get("elevator_block", "minecraft:iron_block"))
    return {
        "floor_block": floor,
        "plate_pad_block": pad,
        "pressure_plate_block": plate,
        "wall_block": wall,
        "elevator_block": door,
        "plate_floor_distance": color_distance(plate, floor),
        "plate_pad_distance": color_distance(plate, pad),
        "pad_floor_distance": color_distance(pad, floor),
        "door_wall_distance": color_distance(door, wall),
        "door_plate_distance": color_distance(door, plate),
        "plate_pad_luminance_gap": round(abs(luminance(plate) - luminance(pad)), 2),
        "door_wall_luminance_gap": round(abs(luminance(door) - luminance(wall)), 2),
    }


def apply_high_contrast_elevator_palette(spec: Dict[str, Any]) -> Dict[str, Any]:
    if str(spec.get("task_template", "elevator_hold_door")) != "elevator_hold_door":
        return dict(spec)
    if spec.get("preserve_materials") or spec.get("auto_contrast_materials") is False:
        return dict(spec)

    item = dict(spec)
    scene_id = sanitize_name(str(item.get("id", "scene")))
    digest = int(hashlib.sha1(scene_id.encode("utf-8")).hexdigest()[:8], 16)
    palette = HIGH_CONTRAST_ELEVATOR_PALETTES[digest % len(HIGH_CONTRAST_ELEVATOR_PALETTES)]
    item.update(palette)
    item["auto_contrast_materials"] = True
    item["visual_contrast"] = visual_contrast_summary(item)
    original_notes = str(item.get("notes", "")).strip()
    contrast_note = (
        "Auto high-contrast materials: pressure plate/floor and elevator door/wall colors are separated for VLM visibility; no separate pressure-plate pad is used."
    )
    item["notes"] = f"{original_notes} {contrast_note}".strip()
    return item


def expand_specs(specs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    expanded: List[Dict[str, Any]] = []

    for spec in specs:
        option_lists: List[List[str]] = []
        present_keys: List[str] = []
        for key, value in spec.items():
            if not key.endswith("_block"):
                continue
            if isinstance(value, str):
                continue
            if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
                present_keys.append(key)
                option_lists.append(value)

        if not present_keys:
            expanded.append(dict(spec))
            continue

        base_id = sanitize_name(str(spec.get("id", "scene")))
        for index, combo in enumerate(itertools.product(*option_lists), start=1):
            item = dict(spec)
            variant_parts = []
            variant_options: Dict[str, str] = {}
            for key, value in zip(present_keys, combo):
                item[key] = value
                short_key = key.replace("_block", "")
                variant_parts.append(f"{short_key}={material_suffix(value)}")
                variant_options[short_key] = value
            variant_key = "|".join(variant_parts)
            item["id"] = make_variant_scene_id(base_id, variant_key, index)
            item["variant_of"] = spec.get("id", base_id)
            item["variant_index"] = index
            item["variant_key"] = variant_key
            item["variant_label"] = short_variant_token(variant_key)
            item["variant_options"] = variant_options
            expanded.append(item)

    return expanded


def layout_specs_non_overlapping(specs: Sequence[Dict[str, Any]], gap: int = DEFAULT_SCENE_GAP) -> List[Dict[str, Any]]:
    if gap < 0:
        raise ValueError("scene gap must be >= 0.")

    laid_out: List[Dict[str, Any]] = []
    cursor_x: int | None = None

    for spec in specs:
        item = dict(spec)
        origin_values = item.get("origin")
        room_values = item.get("room_size")
        if origin_values is None or room_values is None:
            raise ValueError("Each spec must include origin and room_size before layout.")

        ox, oy, oz = validate_size(origin_values, "origin")
        width, _, _ = validate_size(room_values, "room_size")
        if cursor_x is None:
            cursor_x = ox
        shift_x = cursor_x - ox
        item["origin"] = [cursor_x, oy, oz]
        command_block_base = item.get("command_block_base")
        if command_block_base is not None:
            cbx, cby, cbz = validate_size(command_block_base, "command_block_base")
            item["command_block_base"] = [cbx + shift_x, cby, cbz]
        laid_out.append(item)
        cursor_x += width + gap

    return laid_out


def fill_outline(min_pos: Vec3, max_pos: Vec3, block: str) -> List[str]:
    return [
        fill_cmd(Vec3(min_pos.x, min_pos.y, min_pos.z), Vec3(max_pos.x, min_pos.y, max_pos.z), block),
        fill_cmd(Vec3(min_pos.x, max_pos.y, min_pos.z), Vec3(max_pos.x, max_pos.y, max_pos.z), block),
        fill_cmd(Vec3(min_pos.x, min_pos.y, min_pos.z), Vec3(min_pos.x, max_pos.y, max_pos.z), block),
        fill_cmd(Vec3(max_pos.x, min_pos.y, min_pos.z), Vec3(max_pos.x, max_pos.y, max_pos.z), block),
        fill_cmd(Vec3(min_pos.x, min_pos.y, min_pos.z), Vec3(max_pos.x, max_pos.y, min_pos.z), block),
        fill_cmd(Vec3(min_pos.x, min_pos.y, max_pos.z), Vec3(max_pos.x, max_pos.y, max_pos.z), block),
    ]


def fill_plane_outline(min_pos: Vec3, max_pos: Vec3, block: str) -> List[str]:
    if min_pos.y != max_pos.y:
        raise ValueError("fill_plane_outline requires positions on the same Y plane.")
    if min_pos.x > max_pos.x or min_pos.z > max_pos.z:
        raise ValueError("fill_plane_outline requires min_pos <= max_pos.")
    if min_pos.x == max_pos.x or min_pos.z == max_pos.z:
        return [fill_cmd(min_pos, max_pos, block)]
    return [
        fill_cmd(Vec3(min_pos.x, min_pos.y, min_pos.z), Vec3(max_pos.x, max_pos.y, min_pos.z), block),
        fill_cmd(Vec3(min_pos.x, min_pos.y, max_pos.z), Vec3(max_pos.x, max_pos.y, max_pos.z), block),
        fill_cmd(Vec3(min_pos.x, min_pos.y, min_pos.z + 1), Vec3(min_pos.x, max_pos.y, max_pos.z - 1), block),
        fill_cmd(Vec3(max_pos.x, min_pos.y, min_pos.z + 1), Vec3(max_pos.x, max_pos.y, max_pos.z - 1), block),
    ]


def fill_plane_ring(min_pos: Vec3, max_pos: Vec3, block: str, thickness: int) -> List[str]:
    if thickness < 1:
        raise ValueError("fill_plane_ring thickness must be >= 1.")
    commands: List[str] = []
    for inset in range(thickness):
        ring_min = min_pos.shift(dx=inset, dz=inset)
        ring_max = max_pos.shift(dx=-inset, dz=-inset)
        if ring_min.x > ring_max.x or ring_min.z > ring_max.z:
            raise ValueError("fill_plane_ring thickness is too large for the selected region.")
        commands.extend(fill_plane_outline(ring_min, ring_max, block))
    return commands


def exterior_wall_backing_commands(ox: int, oy: int, oz: int, x1: int, y1: int, z1: int, block: str, thickness: int) -> List[str]:
    if thickness <= 0:
        return []
    y0 = oy + 1
    y_top = y1 - 1
    return [
        fill_cmd(Vec3(ox - thickness, y0, oz), Vec3(ox - 1, y_top, z1), block),
        fill_cmd(Vec3(x1 + 1, y0, oz), Vec3(x1 + thickness, y_top, z1), block),
        fill_cmd(Vec3(ox - thickness, y0, oz - thickness), Vec3(x1 + thickness, y_top, oz - 1), block),
        fill_cmd(Vec3(ox - thickness, y0, z1 + 1), Vec3(x1 + thickness, y_top, z1 + thickness), block),
    ]


def default_command_base(ox: int, y1: int, oz: int) -> Vec3:
    return Vec3(ox + 1, y1 - 1, oz + 1)


def prepare_common(spec: Dict[str, Any]) -> Dict[str, Any]:
    scene_id = sanitize_name(str(spec.get("id", "scene")))
    origin_values = spec.get("origin")
    room_values = spec.get("room_size")
    if origin_values is None or room_values is None:
        raise ValueError(f"{scene_id}: missing origin or room_size.")

    ox, oy, oz = validate_size(origin_values, "origin")
    width, height, depth = validate_size(room_values, "room_size")
    if width < 7 or height < 5 or depth < 7:
        raise ValueError(f"{scene_id}: room_size is too small.")

    x1 = ox + width - 1
    y1 = oy + height - 1
    z1 = oz + depth - 1

    task_template = str(spec.get("task_template", "elevator_hold_door"))
    floor_block = str(spec.get("floor_block", "minecraft:smooth_stone"))
    wall_block = str(spec.get("wall_block", "minecraft:white_concrete"))
    ceiling_block = str(spec.get("ceiling_block", wall_block))
    default_backing = 1 if task_template == "elevator_hold_door" else 0
    wall_backing_thickness = int(spec.get("wall_backing_thickness", default_backing))
    wall_backing_block = str(spec.get("wall_backing_block", wall_block))
    light_block = str(spec.get("ceiling_light_block", "minecraft:glowstone"))
    light_mode = str(
        spec.get(
            "ceiling_light_mode",
            "inner_ring_spotlight" if task_template == "elevator_hold_door" else "panel",
        )
    ).lower()
    spotlight_block = str(spec.get("ceiling_spotlight_block", light_block))
    notes = str(spec.get("notes", "")).strip()
    variant_of = spec.get("variant_of")
    variant_index = spec.get("variant_index")
    variant_key = str(spec.get("variant_key", "")).strip()
    variant_label = str(spec.get("variant_label", "")).strip()
    variant_options = spec.get("variant_options")

    command_block_base = spec.get("command_block_base")
    if command_block_base is None:
        command_base = default_command_base(ox, y1, oz)
    else:
        cbx, cby, cbz = validate_size(command_block_base, "command_block_base")
        command_base = Vec3(cbx, cby, cbz)

    if not (ox < command_base.x < x1 and oy < command_base.y < y1 and oz < command_base.z < z1):
        raise ValueError(f"{scene_id}: command_block_base must be inside the room shell.")

    light_size_raw = spec.get("ceiling_light_size", [1, 1])
    spotlight_inset = get_required_int(spec, "ceiling_spotlight_inset") if "ceiling_spotlight_inset" in spec else 1
    spotlight_width = int(spec.get("ceiling_spotlight_width", 1))
    if spotlight_width < 1:
        raise ValueError(f"{scene_id}: ceiling_spotlight_width must be >= 1.")
    light_size_x, light_size_z = validate_size_2(light_size_raw, "ceiling_light_size")
    if light_size_x < 1 or light_size_z < 1:
        raise ValueError(f"{scene_id}: ceiling_light_size values must be >= 1.")

    light_size_x = max(light_size_x, 3) if light_mode == "inner_ring_spotlight" else light_size_x
    light_size_z = max(light_size_z, 3) if light_mode == "inner_ring_spotlight" else light_size_z

    light_x0 = ox + (width - light_size_x) // 2
    light_z0 = oz + (depth - light_size_z) // 2
    light_x1 = light_x0 + light_size_x - 1
    light_z1 = light_z0 + light_size_z - 1
    if light_x0 <= ox or light_x1 >= x1 or light_z0 <= oz or light_z1 >= z1:
        raise ValueError(f"{scene_id}: ceiling_light_size is too large for this room.")

    light_min = Vec3(light_x0, y1, light_z0)
    light_max = Vec3(light_x1, y1, light_z1)
    inner_light_min = Vec3(light_x0, y1, light_z0)
    inner_light_max = Vec3(light_x1, y1, light_z1)
    spotlight_ring_min = Vec3(ox + spotlight_inset, y1, oz + spotlight_inset)
    spotlight_ring_max = Vec3(x1 - spotlight_inset, y1, z1 - spotlight_inset)
    if light_mode == "inner_ring_spotlight":
        if spotlight_ring_min.x > spotlight_ring_max.x or spotlight_ring_min.z > spotlight_ring_max.z:
            raise ValueError(f"{scene_id}: ceiling_spotlight_inset is too large for this room.")

    base_setup = [
        f"# Scene: {scene_id}",
        "# Auto-generated by multiagent/scene/generate_scenes.py",
    ]
    if notes:
        base_setup.append(f"# Notes: {notes}")
    base_setup.extend(
        [
            fill_cmd(Vec3(ox, oy, oz), Vec3(x1, oy, z1), floor_block),
            fill_cmd(Vec3(ox, oy + 1, oz), Vec3(x1, y1 - 1, z1), wall_block),
            *exterior_wall_backing_commands(ox, oy, oz, x1, y1, z1, wall_backing_block, wall_backing_thickness),
            fill_cmd(Vec3(ox + 1, oy + 1, oz + 1), Vec3(x1 - 1, y1 - 1, z1 - 1), "minecraft:air"),
            fill_cmd(Vec3(ox, y1, oz), Vec3(x1, y1, z1), ceiling_block),
        ]
    )
    if light_mode == "inner_ring_spotlight":
        base_setup.extend(fill_plane_ring(spotlight_ring_min, spotlight_ring_max, spotlight_block, spotlight_width))
        base_setup.append(fill_cmd(inner_light_min, inner_light_max, light_block))
    else:
        base_setup.append(fill_cmd(light_min, light_max, light_block))

    clear_lines = [
        f"# Clear scene: {scene_id}",
        fill_cmd(
            Vec3(ox - wall_backing_thickness, oy, oz - wall_backing_thickness),
            Vec3(x1 + wall_backing_thickness, y1, z1 + wall_backing_thickness),
            "minecraft:air",
        ),
    ]

    return {
        "scene_id": scene_id,
        "origin": Vec3(ox, oy, oz),
        "room_size": [width, height, depth],
        "bounds_max": Vec3(x1, y1, z1),
        "floor_block": floor_block,
        "wall_block": wall_block,
        "wall_backing_thickness": wall_backing_thickness,
        "wall_backing_block": wall_backing_block,
        "ceiling_block": ceiling_block,
        "light_block": light_block,
        "light_mode": light_mode,
        "spotlight_block": spotlight_block,
        "spotlight_width": spotlight_width,
        "light_region": [light_min.x, light_min.y, light_min.z, light_max.x, light_max.y, light_max.z],
        "inner_light_region": [
            inner_light_min.x,
            inner_light_min.y,
            inner_light_min.z,
            inner_light_max.x,
            inner_light_max.y,
            inner_light_max.z,
        ],
        "spotlight_ring_region": [
            spotlight_ring_min.x,
            spotlight_ring_min.y,
            spotlight_ring_min.z,
            spotlight_ring_max.x,
            spotlight_ring_max.y,
            spotlight_ring_max.z,
        ],
        "command_base": command_base,
        "setup_lines": base_setup,
        "clear_lines": clear_lines,
        "notes": notes,
        "variant_of": variant_of,
        "variant_index": variant_index,
        "variant_key": variant_key,
        "variant_label": variant_label,
        "variant_options": variant_options if isinstance(variant_options, dict) else None,
        "spec": spec,
    }


def finalize_scene(
    common: Dict[str, Any],
    namespace: str,
    task_template: str,
    setup_lines: List[str],
    place_command_blocks_lines: List[str],
    tick_lines: List[str],
    clear_lines: List[str],
    extras: Dict[str, Any],
) -> Dict[str, Any]:
    scene_id = common["scene_id"]
    summary = {
        "scene_id": scene_id,
        "variant_of": common["variant_of"],
        "variant_index": common["variant_index"],
        "variant_label": common["variant_label"],
        "variant_key": common["variant_key"],
        "variant_options": common["variant_options"],
        "namespace": namespace,
        "task_template": task_template,
        "origin": [common["origin"].x, common["origin"].y, common["origin"].z],
        "room_size": common["room_size"],
        "wall_backing_thickness": common["wall_backing_thickness"],
        "wall_backing_block": common["wall_backing_block"],
        "command_block_base": [
            common["command_base"].x,
            common["command_base"].y,
            common["command_base"].z,
        ],
        "ceiling_light_region": common["light_region"],
        "ceiling_light_block": common["light_block"],
        "ceiling_light_mode": common["light_mode"],
        "ceiling_inner_light_region": common["inner_light_region"],
        "ceiling_spotlight_ring_region": common["spotlight_ring_region"],
        "ceiling_spotlight_block": common["spotlight_block"],
        "ceiling_spotlight_width": common["spotlight_width"],
        "setup_function": f"{namespace}:{scene_id}/setup",
        "place_command_blocks_function": f"{namespace}:{scene_id}/place_command_blocks",
        "tick_function": f"{namespace}:{scene_id}/tick",
        "clear_function": f"{namespace}:{scene_id}/clear",
    }
    summary.update(extras)

    return {
        "scene_id": scene_id,
        "setup": "\n".join(setup_lines) + "\n",
        "place_command_blocks": "\n".join(place_command_blocks_lines) + "\n",
        "tick": "\n".join(tick_lines) + "\n",
        "clear": "\n".join(clear_lines) + "\n",
        "summary": summary,
    }


def build_elevator_scene(spec: Dict[str, Any], namespace: str) -> Dict[str, Any]:
    spec = apply_high_contrast_elevator_palette(spec)
    common = prepare_common(spec)
    scene_id = common["scene_id"]
    ox, oy, oz = common["origin"].x, common["origin"].y, common["origin"].z
    x1, y1, z1 = common["bounds_max"].x, common["bounds_max"].y, common["bounds_max"].z
    width, height, depth = common["room_size"]

    divider_block = str(spec.get("divider_block", common["wall_block"]))
    elevator_block = str(spec.get("elevator_block", "minecraft:iron_block"))
    plate_block = str(spec.get("pressure_plate_block", "minecraft:stone_pressure_plate"))
    plate_state = str(spec.get("pressure_plate_active_state", "powered=true"))
    divider_axis = str(spec.get("divider_axis", "z")).lower()
    if divider_axis not in {"x", "z"}:
        raise ValueError(f"{scene_id}: divider_axis must be 'x' or 'z'.")

    door_width = get_required_int(spec, "door_width")
    door_height = get_required_int(spec, "door_height")
    plate_offset = get_required_int(spec, "plate_offset")
    min_plate_door_clearance = float(spec.get("min_plate_door_clearance", 2.5))
    door_lateral_offset = int(spec.get("door_lateral_offset", 0))
    plate_lateral_offset = int(spec.get("plate_lateral_offset", 0))
    pressure_plate_size = int(spec.get("pressure_plate_size", 3))
    if pressure_plate_size < 1:
        raise ValueError(f"{scene_id}: pressure_plate_size must be a positive integer.")
    plate_lower_offset = (pressure_plate_size - 1) // 2

    if divider_axis == "z":
        divider_coord = oz + depth // 2
        door_center_x = ox + width // 2 + door_lateral_offset
        door_x0 = door_center_x - door_width // 2
        door_x1 = door_x0 + door_width - 1
        door_min = Vec3(door_x0, oy + 1, divider_coord)
        door_max = Vec3(door_x1, oy + door_height, divider_coord)
        divider_start = Vec3(ox + 1, oy + 1, divider_coord)
        divider_end = Vec3(x1 - 1, y1 - 1, divider_coord)
        plate_pos = Vec3(ox + width // 2 + plate_lateral_offset, oy + 1, divider_coord - plate_offset)
        plate_min = Vec3(plate_pos.x - plate_lower_offset, plate_pos.y, plate_pos.z - plate_lower_offset)
        plate_max = Vec3(plate_min.x + pressure_plate_size - 1, plate_pos.y, plate_min.z + pressure_plate_size - 1)
        if door_x0 <= ox or door_x1 >= x1:
            raise ValueError(f"{scene_id}: elevator door is outside the room wall.")
        if plate_min.x <= ox or plate_max.x >= x1 or plate_min.z <= oz or plate_max.z >= divider_coord:
            raise ValueError(f"{scene_id}: pressure plate region is outside the first room.")
        plate_door_clearance = float(divider_coord - plate_max.z)
        if plate_door_clearance < min_plate_door_clearance:
            raise ValueError(
                f"{scene_id}: pressure plate region must be at least {min_plate_door_clearance} blocks away from the elevator door."
            )
    else:
        divider_coord = ox + width // 2
        door_center_z = oz + depth // 2 + door_lateral_offset
        door_z0 = door_center_z - door_width // 2
        door_z1 = door_z0 + door_width - 1
        door_min = Vec3(divider_coord, oy + 1, door_z0)
        door_max = Vec3(divider_coord, oy + door_height, door_z1)
        divider_start = Vec3(divider_coord, oy + 1, oz + 1)
        divider_end = Vec3(divider_coord, y1 - 1, z1 - 1)
        plate_pos = Vec3(divider_coord - plate_offset, oy + 1, oz + depth // 2 + plate_lateral_offset)
        plate_min = Vec3(plate_pos.x - plate_lower_offset, plate_pos.y, plate_pos.z - plate_lower_offset)
        plate_max = Vec3(plate_min.x + pressure_plate_size - 1, plate_pos.y, plate_min.z + pressure_plate_size - 1)
        if door_z0 <= oz or door_z1 >= z1:
            raise ValueError(f"{scene_id}: elevator door is outside the room wall.")
        if plate_min.x <= ox or plate_min.z <= oz or plate_max.z >= z1 or plate_max.x >= divider_coord:
            raise ValueError(f"{scene_id}: pressure plate region is outside the first room.")
        plate_door_clearance = float(divider_coord - plate_max.x)
        if plate_door_clearance < min_plate_door_clearance:
            raise ValueError(
                f"{scene_id}: pressure plate region must be at least {min_plate_door_clearance} blocks away from the elevator door."
            )

    if door_height >= height - 1:
        raise ValueError(f"{scene_id}: door_height is too large for room height.")

    plate_positions = region_positions(plate_min, plate_max)
    plate_pad_block = str(spec.get("plate_pad_block", common["floor_block"]))
    pad_min = Vec3(max(ox + 1, plate_min.x - 1), plate_pos.y - 1, max(oz + 1, plate_min.z - 1))
    pad_max = Vec3(min(x1 - 1, plate_max.x + 1), plate_pos.y - 1, min(z1 - 1, plate_max.z + 1))

    setup_lines = list(common["setup_lines"])
    setup_lines.extend(
        [
            fill_cmd(divider_start, divider_end, divider_block),
            fill_cmd(door_min, door_max, elevator_block),
        ]
    )
    if plate_pad_block != common["floor_block"]:
        setup_lines.append(fill_cmd(pad_min, pad_max, plate_pad_block))
    setup_lines.extend(
        [
            *[setblock_cmd(pos, plate_block) for pos in plate_positions],
        ]
    )
    placed_decorations = add_decorations(spec, common, setup_lines)
    setup_lines.extend(
        [
            "",
            "# Command blocks that keep the elevator door open while the plate is pressed.",
            f"function {namespace}:{scene_id}/place_command_blocks",
        ]
    )

    active_plate_block = f"{plate_block}[{plate_state}]"
    open_cmd = fill_cmd(door_min, door_max, "minecraft:air")
    close_cmd = fill_cmd(door_min, door_max, elevator_block)
    close_condition = " ".join(f"unless block {pos.to_cmd()} {active_plate_block}" for pos in plate_positions)
    command_base = common["command_base"]
    open_command_lines = [
        (
            f'setblock {command_base.shift(dx=index).to_cmd()} minecraft:repeating_command_block[facing=east]'
            f'{{auto:1b,Command:"execute if block {pos.to_cmd()} {active_plate_block} run {open_cmd}"}}'
        )
        for index, pos in enumerate(plate_positions)
    ]
    close_command_line = (
        f'setblock {command_base.shift(dx=len(plate_positions)).to_cmd()} minecraft:repeating_command_block[facing=east]'
        f'{{auto:1b,Command:"execute {close_condition} run {close_cmd}"}}'
    )
    place_command_blocks_lines = [
        f"# Place command blocks for scene: {scene_id}",
        *open_command_lines,
        close_command_line,
    ]
    tick_lines = [
        f"# Tick logic for scene: {scene_id}",
        *[f"execute if block {pos.to_cmd()} {active_plate_block} run {open_cmd}" for pos in plate_positions],
        f"execute {close_condition} run {close_cmd}",
    ]
    clear_lines = list(common["clear_lines"])
    clear_lines.append(fill_cmd(command_base, command_base.shift(dx=len(plate_positions)), "minecraft:air"))

    return finalize_scene(
        common,
        namespace,
        "elevator_hold_door",
        setup_lines,
        place_command_blocks_lines,
        tick_lines,
        clear_lines,
        {
            "divider_axis": divider_axis,
            "door_lateral_offset": door_lateral_offset,
            "plate_lateral_offset": plate_lateral_offset,
            "plate_offset": plate_offset,
            "min_plate_door_clearance": min_plate_door_clearance,
            "pressure_plate_size": pressure_plate_size,
            "door_region": [door_min.x, door_min.y, door_min.z, door_max.x, door_max.y, door_max.z],
            "pressure_plate_pos": [plate_pos.x, plate_pos.y, plate_pos.z],
            "pressure_plate_region": [plate_min.x, plate_min.y, plate_min.z, plate_max.x, plate_max.y, plate_max.z],
            "pressure_plate_positions": [[pos.x, pos.y, pos.z] for pos in plate_positions],
            "pressure_plate_block": plate_block,
            "plate_pad_block": plate_pad_block,
            "plate_pad_region": [pad_min.x, pad_min.y, pad_min.z, pad_max.x, pad_max.y, pad_max.z],
            "floor_block": common["floor_block"],
            "wall_block": common["wall_block"],
            "divider_block": divider_block,
            "elevator_block": elevator_block,
            "visual_contrast": visual_contrast_summary(spec),
            "decorations": placed_decorations,
            "decoration_count": len(placed_decorations),
            "difficulty": spec.get("difficulty"),
            "difficulty_zh": spec.get("difficulty_zh"),
            "difficulty_constraints": spec.get("difficulty_constraints"),
        },
    )


def build_pressure_path_reveal_scene(spec: Dict[str, Any], namespace: str) -> Dict[str, Any]:
    common = prepare_common(spec)
    scene_id = common["scene_id"]
    ox, oy, oz = common["origin"].x, common["origin"].y, common["origin"].z
    x1, y1, z1 = common["bounds_max"].x, common["bounds_max"].y, common["bounds_max"].z
    width, height, depth = common["room_size"]

    path_axis = str(spec.get("path_axis", "z")).lower()
    if path_axis not in {"x", "z"}:
        raise ValueError(f"{scene_id}: path_axis must be 'x' or 'z'.")

    foundation_thickness = int(spec.get("foundation_thickness", 3))
    end_length = int(spec.get("solid_end_length", 5))
    path_width = int(spec.get("reveal_path_width", 2))
    path_length_value = spec.get("reveal_path_length")
    path_length = int(path_length_value) if path_length_value is not None else None
    plate_offset = int(spec.get("plate_offset_from_gap", 2))
    pressure_plate_size = int(spec.get("pressure_plate_size", 3))
    if foundation_thickness < 3:
        raise ValueError(f"{scene_id}: foundation_thickness must be >= 3.")
    if end_length < 3:
        raise ValueError(f"{scene_id}: solid_end_length must be >= 3.")
    if path_width < 1:
        raise ValueError(f"{scene_id}: reveal_path_width must be >= 1.")
    if path_length is not None and path_length < 1:
        raise ValueError(f"{scene_id}: reveal_path_length must be >= 1.")
    if pressure_plate_size < 1:
        raise ValueError(f"{scene_id}: pressure_plate_size must be a positive integer.")

    plate_block = str(spec.get("pressure_plate_block", "minecraft:stone_pressure_plate"))
    plate_state = str(spec.get("pressure_plate_active_state", "powered=true"))
    active_path_block = str(spec.get("reveal_path_block", "minecraft:lime_concrete"))
    inactive_path_block = str(spec.get("inactive_path_block", "minecraft:air"))
    goal_marker_block = str(spec.get("goal_marker_block", "minecraft:gold_block"))
    foundation_block = str(spec.get("foundation_block", common["floor_block"]))
    bottom_layer_block = str(spec.get("bottom_layer_block", "minecraft:black_concrete"))
    foundation_y0 = oy - foundation_thickness + 1
    plate_lower_offset = (pressure_plate_size - 1) // 2

    if path_axis == "z":
        interior_length = depth - 2
        if path_length is not None:
            remaining_length = interior_length - path_length
            if remaining_length < end_length * 2:
                raise ValueError(f"{scene_id}: room depth is too small for the requested path length and solid ends.")
            gap_z0 = oz + 1 + remaining_length // 2
            gap_z1 = gap_z0 + path_length - 1
        else:
            gap_z0 = oz + 1 + end_length
            gap_z1 = z1 - 1 - end_length
        if gap_z1 - gap_z0 + 1 < 3:
            raise ValueError(f"{scene_id}: room depth is too small for the requested solid ends and hollow middle.")
        solid_a_min = Vec3(ox, foundation_y0, oz)
        solid_a_max = Vec3(x1, oy, gap_z0 - 1)
        solid_b_min = Vec3(ox, foundation_y0, gap_z1 + 1)
        solid_b_max = Vec3(x1, oy, z1)
        hollow_min = Vec3(ox + 1, foundation_y0, gap_z0)
        hollow_max = Vec3(x1 - 1, oy, gap_z1)
        path_x0 = ox + (width - path_width) // 2
        path_x1 = path_x0 + path_width - 1
        path_min = Vec3(path_x0, oy, gap_z0)
        path_max = Vec3(path_x1, oy, gap_z1)
        plate_center = Vec3(ox + width // 2, oy + 1, max(oz + 2, gap_z0 - plate_offset))
        opposite_bank_min = Vec3(ox + 1, oy + 1, gap_z1 + 1)
        opposite_bank_max = Vec3(x1 - 1, oy + 1, z1 - 1)
        goal_min = Vec3(path_x0, oy + 1, min(z1 - 2, gap_z1 + 2))
        goal_max = Vec3(path_x1, oy + 1, min(z1 - 2, gap_z1 + 2))
    else:
        interior_length = width - 2
        if path_length is not None:
            remaining_length = interior_length - path_length
            if remaining_length < end_length * 2:
                raise ValueError(f"{scene_id}: room width is too small for the requested path length and solid ends.")
            gap_x0 = ox + 1 + remaining_length // 2
            gap_x1 = gap_x0 + path_length - 1
        else:
            gap_x0 = ox + 1 + end_length
            gap_x1 = x1 - 1 - end_length
        if gap_x1 - gap_x0 + 1 < 3:
            raise ValueError(f"{scene_id}: room width is too small for the requested solid ends and hollow middle.")
        solid_a_min = Vec3(ox, foundation_y0, oz)
        solid_a_max = Vec3(gap_x0 - 1, oy, z1)
        solid_b_min = Vec3(gap_x1 + 1, foundation_y0, oz)
        solid_b_max = Vec3(x1, oy, z1)
        hollow_min = Vec3(gap_x0, foundation_y0, oz + 1)
        hollow_max = Vec3(gap_x1, oy, z1 - 1)
        path_z0 = oz + (depth - path_width) // 2
        path_z1 = path_z0 + path_width - 1
        path_min = Vec3(gap_x0, oy, path_z0)
        path_max = Vec3(gap_x1, oy, path_z1)
        plate_center = Vec3(max(ox + 2, gap_x0 - plate_offset), oy + 1, oz + depth // 2)
        opposite_bank_min = Vec3(gap_x1 + 1, oy + 1, oz + 1)
        opposite_bank_max = Vec3(x1 - 1, oy + 1, z1 - 1)
        goal_min = Vec3(min(x1 - 2, gap_x1 + 2), oy + 1, path_z0)
        goal_max = Vec3(min(x1 - 2, gap_x1 + 2), oy + 1, path_z1)

    if path_max.x <= ox or path_min.x >= x1 or path_max.z <= oz or path_min.z >= z1:
        raise ValueError(f"{scene_id}: reveal path must stay inside the room.")
    if y1 - oy < 4 or height < 5:
        raise ValueError(f"{scene_id}: room height is too small for pressure_path_reveal.")

    plate_min = Vec3(plate_center.x - plate_lower_offset, plate_center.y, plate_center.z - plate_lower_offset)
    plate_max = Vec3(plate_min.x + pressure_plate_size - 1, plate_center.y, plate_min.z + pressure_plate_size - 1)
    if plate_min.x <= ox or plate_max.x >= x1 or plate_min.z <= oz or plate_max.z >= z1:
        raise ValueError(f"{scene_id}: pressure plate region is outside the room.")
    plate_positions = region_positions(plate_min, plate_max)
    marker_min = goal_min
    marker_max = goal_max

    setup_lines = list(common["setup_lines"])
    setup_lines.extend(
        [
            fill_cmd(Vec3(ox, foundation_y0, oz), Vec3(x1, oy, z1), foundation_block),
            fill_cmd(solid_a_min, solid_a_max, foundation_block),
            fill_cmd(solid_b_min, solid_b_max, foundation_block),
            fill_cmd(hollow_min, hollow_max, "minecraft:air"),
            fill_cmd(Vec3(ox, foundation_y0, oz), Vec3(x1, foundation_y0, z1), bottom_layer_block),
            fill_cmd(path_min, path_max, inactive_path_block),
            fill_cmd(marker_min, marker_max, goal_marker_block),
            *[setblock_cmd(pos, plate_block) for pos in plate_positions],
        ]
    )
    placed_decorations = add_decorations(spec, common, setup_lines)
    setup_lines.extend(
        [
            "",
            "# Command blocks that reveal the middle path while the plate is pressed.",
            f"function {namespace}:{scene_id}/place_command_blocks",
        ]
    )

    active_plate_block = f"{plate_block}[{plate_state}]"
    reveal_cmd = fill_cmd(path_min, path_max, active_path_block)
    hide_cmd = fill_cmd(path_min, path_max, inactive_path_block)
    hide_condition = " ".join(f"unless block {pos.to_cmd()} {active_plate_block}" for pos in plate_positions)
    command_base = common["command_base"]
    reveal_command_lines = [
        (
            f'setblock {command_base.shift(dx=index).to_cmd()} minecraft:repeating_command_block[facing=east]'
            f'{{auto:1b,Command:"execute if block {pos.to_cmd()} {active_plate_block} run {reveal_cmd}"}}'
        )
        for index, pos in enumerate(plate_positions)
    ]
    hide_command_line = (
        f'setblock {command_base.shift(dx=len(plate_positions)).to_cmd()} minecraft:repeating_command_block[facing=east]'
        f'{{auto:1b,Command:"execute {hide_condition} run {hide_cmd}"}}'
    )
    place_command_blocks_lines = [
        f"# Place command blocks for scene: {scene_id}",
        *reveal_command_lines,
        hide_command_line,
    ]
    tick_lines = [
        f"# Tick logic for scene: {scene_id}",
        *[f"execute if block {pos.to_cmd()} {active_plate_block} run {reveal_cmd}" for pos in plate_positions],
        f"execute {hide_condition} run {hide_cmd}",
    ]
    clear_lines = list(common["clear_lines"])
    clear_lines.append(fill_cmd(Vec3(ox, foundation_y0, oz), Vec3(x1, oy - 1, z1), "minecraft:air"))
    clear_lines.append(fill_cmd(command_base, command_base.shift(dx=len(plate_positions)), "minecraft:air"))

    return finalize_scene(
        common,
        namespace,
        "pressure_path_reveal",
        setup_lines,
        place_command_blocks_lines,
        tick_lines,
        clear_lines,
        {
            "path_axis": path_axis,
            "foundation_thickness": foundation_thickness,
            "solid_end_length": end_length,
            "reveal_path_length": path_max.z - path_min.z + 1 if path_axis == "z" else path_max.x - path_min.x + 1,
            "reveal_path_width": path_max.x - path_min.x + 1 if path_axis == "z" else path_max.z - path_min.z + 1,
            "pressure_plate_size": pressure_plate_size,
            "plate_offset_from_gap": plate_offset,
            "solid_end_a_region": [solid_a_min.x, solid_a_min.y, solid_a_min.z, solid_a_max.x, solid_a_max.y, solid_a_max.z],
            "solid_end_b_region": [solid_b_min.x, solid_b_min.y, solid_b_min.z, solid_b_max.x, solid_b_max.y, solid_b_max.z],
            "hollow_middle_region": [hollow_min.x, hollow_min.y, hollow_min.z, hollow_max.x, hollow_max.y, hollow_max.z],
            "reveal_path_region": [path_min.x, path_min.y, path_min.z, path_max.x, path_max.y, path_max.z],
            "pressure_plate_pos": [plate_center.x, plate_center.y, plate_center.z],
            "pressure_plate_region": [plate_min.x, plate_min.y, plate_min.z, plate_max.x, plate_max.y, plate_max.z],
            "pressure_plate_positions": [[pos.x, pos.y, pos.z] for pos in plate_positions],
            "pressure_plate_block": plate_block,
            "reveal_path_block": active_path_block,
            "inactive_path_block": inactive_path_block,
            "bottom_layer_block": bottom_layer_block,
            "goal_region": [opposite_bank_min.x, opposite_bank_min.y, opposite_bank_min.z, opposite_bank_max.x, opposite_bank_max.y, opposite_bank_max.z],
            "goal_marker_region": [marker_min.x, marker_min.y, marker_min.z, marker_max.x, marker_max.y, marker_max.z],
            "floor_block": common["floor_block"],
            "wall_block": common["wall_block"],
            "decorations": placed_decorations,
            "decoration_count": len(placed_decorations),
            "difficulty": spec.get("difficulty"),
            "difficulty_zh": spec.get("difficulty_zh"),
            "difficulty_constraints": spec.get("difficulty_constraints"),
        },
    )


def build_middle_wall_opening_scene(spec: Dict[str, Any], namespace: str) -> Dict[str, Any]:
    common = prepare_common(spec)
    scene_id = common["scene_id"]
    ox, oy, oz = common["origin"].x, common["origin"].y, common["origin"].z
    x1, y1, z1 = common["bounds_max"].x, common["bounds_max"].y, common["bounds_max"].z
    width, height, depth = common["room_size"]

    divider_block = str(spec.get("divider_block", common["wall_block"]))
    divider_axis = str(spec.get("divider_axis", "z")).lower()
    if divider_axis not in {"x", "z"}:
        raise ValueError(f"{scene_id}: divider_axis must be 'x' or 'z'.")

    door_width = get_required_int(spec, "door_width")
    door_height = get_required_int(spec, "door_height")
    if door_height >= height - 1:
        raise ValueError(f"{scene_id}: door_height is too large for room height.")

    if divider_axis == "z":
        divider_coord = oz + depth // 2
        door_x0 = ox + (width - door_width) // 2
        door_x1 = door_x0 + door_width - 1
        divider_start = Vec3(ox + 1, oy + 1, divider_coord)
        divider_end = Vec3(x1 - 1, y1 - 1, divider_coord)
        door_min = Vec3(door_x0, oy + 1, divider_coord)
        door_max = Vec3(door_x1, oy + door_height, divider_coord)
    else:
        divider_coord = ox + width // 2
        door_z0 = oz + (depth - door_width) // 2
        door_z1 = door_z0 + door_width - 1
        divider_start = Vec3(divider_coord, oy + 1, oz + 1)
        divider_end = Vec3(divider_coord, y1 - 1, z1 - 1)
        door_min = Vec3(divider_coord, oy + 1, door_z0)
        door_max = Vec3(divider_coord, oy + door_height, door_z1)

    setup_lines = list(common["setup_lines"])
    setup_lines.extend(
        [
            fill_cmd(divider_start, divider_end, divider_block),
            fill_cmd(door_min, door_max, "minecraft:air"),
        ]
    )

    place_command_blocks_lines = [
        f"# No command blocks are needed for scene: {scene_id}",
    ]
    tick_lines = [
        f"# No tick logic is needed for scene: {scene_id}",
    ]
    clear_lines = list(common["clear_lines"])

    return finalize_scene(
        common,
        namespace,
        "middle_wall_opening",
        setup_lines,
        place_command_blocks_lines,
        tick_lines,
        clear_lines,
        {
            "divider_axis": divider_axis,
            "divider_region": [
                divider_start.x,
                divider_start.y,
                divider_start.z,
                divider_end.x,
                divider_end.y,
                divider_end.z,
            ],
            "door_region": [door_min.x, door_min.y, door_min.z, door_max.x, door_max.y, door_max.z],
        },
    )


def build_reverse_parking_opening_scene(spec: Dict[str, Any], namespace: str) -> Dict[str, Any]:
    common = prepare_common(spec)
    scene_id = common["scene_id"]
    ox, oy, oz = common["origin"].x, common["origin"].y, common["origin"].z
    x1, y1, z1 = common["bounds_max"].x, common["bounds_max"].y, common["bounds_max"].z
    width, height, depth = common["room_size"]

    divider_block = str(spec.get("divider_block", common["wall_block"]))
    divider_axis = str(spec.get("divider_axis", "z")).lower()
    if divider_axis not in {"x", "z"}:
        raise ValueError(f"{scene_id}: divider_axis must be 'x' or 'z'.")

    door_width = get_required_int(spec, "door_width")
    door_height = get_required_int(spec, "door_height")
    if door_height >= height - 1:
        raise ValueError(f"{scene_id}: door_height is too large for room height.")

    if divider_axis == "z":
        divider_coord = oz + depth // 2
        door_x0 = ox + (width - door_width) // 2
        door_x1 = door_x0 + door_width - 1
        divider_start = Vec3(ox + 1, oy + 1, divider_coord)
        divider_end = Vec3(x1 - 1, y1 - 1, divider_coord)
        door_min = Vec3(door_x0, oy + 1, divider_coord)
        door_max = Vec3(door_x1, oy + door_height, divider_coord)
        lane_x0 = ox + (width - door_width) // 2
        lane_x1 = lane_x0 + door_width - 1
        lane_start = Vec3(lane_x0, oy, oz + 1)
        lane_end = Vec3(lane_x1, oy, z1 - 1)
    else:
        divider_coord = ox + width // 2
        door_z0 = oz + (depth - door_width) // 2
        door_z1 = door_z0 + door_width - 1
        divider_start = Vec3(divider_coord, oy + 1, oz + 1)
        divider_end = Vec3(divider_coord, y1 - 1, z1 - 1)
        door_min = Vec3(divider_coord, oy + 1, door_z0)
        door_max = Vec3(divider_coord, oy + door_height, door_z1)
        lane_z0 = oz + (depth - door_width) // 2
        lane_z1 = lane_z0 + door_width - 1
        lane_start = Vec3(ox + 1, oy, lane_z0)
        lane_end = Vec3(x1 - 1, oy, lane_z1)

    reverse_lane_block = str(spec.get("reverse_lane_block", common["floor_block"]))
    opening_marker_block = str(spec.get("opening_marker_block", "minecraft:yellow_concrete"))

    setup_lines = list(common["setup_lines"])
    setup_lines.extend(
        [
            fill_cmd(divider_start, divider_end, divider_block),
            fill_cmd(door_min, door_max, "minecraft:air"),
            fill_cmd(lane_start, lane_end, reverse_lane_block),
            fill_cmd(door_min.shift(dy=-1), door_max.shift(dy=-1), opening_marker_block),
        ]
    )

    place_command_blocks_lines = [
        f"# No command blocks are needed for scene: {scene_id}",
    ]
    tick_lines = [
        f"# No tick logic is needed for scene: {scene_id}",
    ]
    clear_lines = list(common["clear_lines"])

    return finalize_scene(
        common,
        namespace,
        "reverse_parking_opening",
        setup_lines,
        place_command_blocks_lines,
        tick_lines,
        clear_lines,
        {
            "divider_axis": divider_axis,
            "divider_region": [
                divider_start.x,
                divider_start.y,
                divider_start.z,
                divider_end.x,
                divider_end.y,
                divider_end.z,
            ],
            "door_region": [door_min.x, door_min.y, door_min.z, door_max.x, door_max.y, door_max.z],
            "reverse_lane_region": [lane_start.x, lane_start.y, lane_start.z, lane_end.x, lane_end.y, lane_end.z],
        },
    )


def build_truck_reverse_guidance_scene(spec: Dict[str, Any], namespace: str) -> Dict[str, Any]:
    common = prepare_common(spec)
    scene_id = common["scene_id"]
    ox, oy, oz = common["origin"].x, common["origin"].y, common["origin"].z
    x1, y1, z1 = common["bounds_max"].x, common["bounds_max"].y, common["bounds_max"].z
    width, height, depth = common["room_size"]

    lane_marker_block = str(spec.get("lane_marker_block", "minecraft:yellow_concrete"))
    blind_wall_block = str(spec.get("blind_wall_block", "minecraft:gray_concrete"))
    parking_border_block = str(spec.get("parking_border_block", "minecraft:white_concrete"))
    parking_fill_block = str(spec.get("parking_fill_block", "minecraft:black_concrete"))
    truck_block = str(spec.get("truck_block", "minecraft:blue_concrete"))
    guidance_indicator_off_block = str(spec.get("guidance_indicator_off_block", "minecraft:red_concrete"))
    guidance_indicator_on_block = str(spec.get("guidance_indicator_on_block", "minecraft:lime_concrete"))
    checkpoint_plate_block = str(spec.get("checkpoint_plate_block", "minecraft:light_weighted_pressure_plate"))
    checkpoint_state = str(spec.get("checkpoint_plate_active_state", "powered=true"))
    observation_platform_block = str(spec.get("observation_platform_block", "minecraft:polished_andesite"))

    truck_size = validate_size(spec.get("truck_size", [3, 2, 5]), "truck_size")
    parking_size = validate_size(spec.get("parking_zone_size", [5, 1, 6]), "parking_zone_size")
    observation_size = validate_size(spec.get("observation_platform_size", [2, 2, 4]), "observation_platform_size")
    reverse_lane_width = get_required_int(spec, "reverse_lane_width")
    blind_wall_offset = get_required_int(spec, "blind_wall_offset")

    if reverse_lane_width < truck_size[0]:
        raise ValueError(f"{scene_id}: reverse_lane_width must be >= truck width.")

    lane_x0 = ox + (width - reverse_lane_width) // 2
    lane_x1 = lane_x0 + reverse_lane_width - 1
    lane_z0 = oz + 1
    lane_z1 = z1 - 1

    truck_min = Vec3(ox + (width - truck_size[0]) // 2, oy + 1, oz + 2)
    truck_max = Vec3(truck_min.x + truck_size[0] - 1, truck_min.y + truck_size[1] - 1, truck_min.z + truck_size[2] - 1)
    if truck_max.z >= z1 - 4:
        raise ValueError(f"{scene_id}: truck_size is too large for this room depth.")

    parking_min = Vec3(ox + (width - parking_size[0]) // 2, oy + 1, z1 - parking_size[2] - 1)
    parking_max = Vec3(parking_min.x + parking_size[0] - 1, parking_min.y + parking_size[1] - 1, parking_min.z + parking_size[2] - 1)

    blind_wall_z = min(truck_max.z + blind_wall_offset, parking_min.z - 2)
    if blind_wall_z <= truck_max.z:
        raise ValueError(f"{scene_id}: blind_wall_offset leaves no room for the truck blind wall.")
    blind_wall_min = Vec3(lane_x0, oy + 1, blind_wall_z)
    blind_wall_max = Vec3(lane_x1, oy + min(height - 2, truck_size[1] + 2), blind_wall_z)

    obs_w, obs_h, obs_d = observation_size
    observation_min = Vec3(ox + 1, oy + 1, parking_min.z)
    observation_max = Vec3(observation_min.x + obs_w - 1, observation_min.y + obs_h - 1, observation_min.z + obs_d - 1)
    if observation_max.z >= z1 or observation_max.y >= y1:
        raise ValueError(f"{scene_id}: observation_platform_size is too large.")

    rear_left_plate = Vec3(parking_min.x + 1, oy + 1, parking_min.z + 1)
    rear_right_plate = Vec3(parking_max.x - 1, oy + 1, parking_min.z + 1)
    indicator_min = Vec3(ox + width // 2 - 1, y1 - 1, z1 - 1)
    indicator_max = Vec3(ox + width // 2 + 1, y1 - 1, z1 - 1)

    setup_lines = list(common["setup_lines"])
    setup_lines.extend(
        [
            fill_cmd(Vec3(lane_x0, oy, lane_z0), Vec3(lane_x1, oy, lane_z1), lane_marker_block),
            fill_cmd(Vec3(lane_x0 + 1, oy, lane_z0), Vec3(lane_x1 - 1, oy, lane_z1), common["floor_block"]),
        ]
    )
    setup_lines.extend(fill_outline(parking_min, parking_max, parking_border_block))
    setup_lines.append(fill_cmd(parking_min.shift(dx=1, dz=1), parking_max.shift(dx=-1, dz=-1), parking_fill_block))
    setup_lines.extend(
        [
            fill_cmd(truck_min, truck_max, truck_block),
            fill_cmd(blind_wall_min, blind_wall_max, blind_wall_block),
            fill_cmd(observation_min.shift(dy=-1), observation_max.shift(dy=-1), observation_platform_block),
            fill_cmd(observation_min, observation_max, "minecraft:air"),
            setblock_cmd(rear_left_plate, checkpoint_plate_block),
            setblock_cmd(rear_right_plate, checkpoint_plate_block),
            fill_cmd(indicator_min, indicator_max, guidance_indicator_off_block),
            "",
            "# Command blocks that update the parking guidance indicator.",
            f"function {namespace}:{scene_id}/place_command_blocks",
        ]
    )

    active_plate_block = f"{checkpoint_plate_block}[{checkpoint_state}]"
    success_cond = (
        f"if block {rear_left_plate.to_cmd()} {active_plate_block} "
        f"if block {rear_right_plate.to_cmd()} {active_plate_block}"
    )
    success_cmd = fill_cmd(indicator_min, indicator_max, guidance_indicator_on_block)
    failure_cmd = fill_cmd(indicator_min, indicator_max, guidance_indicator_off_block)
    command_base = common["command_base"]
    place_command_blocks_lines = [
        f"# Place command blocks for scene: {scene_id}",
        (
            f'setblock {command_base.to_cmd()} minecraft:repeating_command_block[facing=east]'
            f'{{auto:1b,Command:"execute {success_cond} run {success_cmd}"}}'
        ),
        (
            f'setblock {command_base.shift(dx=1).to_cmd()} minecraft:repeating_command_block[facing=east]'
            f'{{auto:1b,Command:"execute unless block {rear_left_plate.to_cmd()} {active_plate_block} run {failure_cmd}"}}'
        ),
        (
            f'setblock {command_base.shift(dx=2).to_cmd()} minecraft:repeating_command_block[facing=east]'
            f'{{auto:1b,Command:"execute if block {rear_left_plate.to_cmd()} {active_plate_block} unless block {rear_right_plate.to_cmd()} {active_plate_block} run {failure_cmd}"}}'
        ),
    ]
    tick_lines = [
        f"# Tick logic for scene: {scene_id}",
        f"execute {success_cond} run {success_cmd}",
        f"execute unless block {rear_left_plate.to_cmd()} {active_plate_block} run {failure_cmd}",
        f"execute if block {rear_left_plate.to_cmd()} {active_plate_block} unless block {rear_right_plate.to_cmd()} {active_plate_block} run {failure_cmd}",
    ]
    clear_lines = list(common["clear_lines"])
    clear_lines.append(fill_cmd(command_base, command_base.shift(dx=2), "minecraft:air"))

    return finalize_scene(
        common,
        namespace,
        "truck_reverse_guidance",
        setup_lines,
        place_command_blocks_lines,
        tick_lines,
        clear_lines,
        {
            "truck_region": [truck_min.x, truck_min.y, truck_min.z, truck_max.x, truck_max.y, truck_max.z],
            "parking_zone": [parking_min.x, parking_min.y, parking_min.z, parking_max.x, parking_max.y, parking_max.z],
            "blind_wall": [blind_wall_min.x, blind_wall_min.y, blind_wall_min.z, blind_wall_max.x, blind_wall_max.y, blind_wall_max.z],
            "observation_platform": [
                observation_min.x,
                observation_min.y,
                observation_min.z,
                observation_max.x,
                observation_max.y,
                observation_max.z,
            ],
            "parking_checkpoint_plates": [
                [rear_left_plate.x, rear_left_plate.y, rear_left_plate.z],
                [rear_right_plate.x, rear_right_plate.y, rear_right_plate.z],
            ],
            "indicator_region": [indicator_min.x, indicator_min.y, indicator_min.z, indicator_max.x, indicator_max.y, indicator_max.z],
        },
    )


def build_truck_driver_scene(spec: Dict[str, Any], namespace: str) -> Dict[str, Any]:
    common = prepare_common(spec)
    scene_id = common["scene_id"]
    ox, oy, oz = common["origin"].x, common["origin"].y, common["origin"].z
    x1, z1 = common["bounds_max"].x, common["bounds_max"].z
    width, _, depth = common["room_size"]

    parking_block = str(spec.get("parking_block", "minecraft:yellow_concrete"))
    target_size = int(spec.get("target_size", 3))
    if parking_block == common["floor_block"]:
        raise ValueError(f"{scene_id}: parking_block must differ from floor_block.")
    if target_size < 1:
        raise ValueError(f"{scene_id}: target_size must be positive.")
    if width < 13 or depth < 17:
        raise ValueError(f"{scene_id}: room_size must be at least [13, 5, 17].")

    parking_center_x = ox + width // 2
    parking_center_z = oz + depth // 2
    parking_min = Vec3(parking_center_x - (target_size - 1) // 2, oy, parking_center_z - (target_size - 1) // 2)
    parking_max = Vec3(parking_min.x + target_size - 1, oy, parking_min.z + target_size - 1)
    target_center = [
        (parking_min.x + parking_max.x) / 2.0,
        float(oy + 1),
        (parking_min.z + parking_max.z) / 2.0,
    ]

    setup_lines = list(common["setup_lines"])
    setup_lines.append(fill_cmd(parking_min, parking_max, parking_block))
    placed_decorations = add_decorations(spec, common, setup_lines)
    return finalize_scene(
        common,
        namespace,
        "truck_driver",
        setup_lines,
        [f"# No command blocks are needed for scene: {scene_id}"],
        [f"# No tick logic is needed for scene: {scene_id}"],
        list(common["clear_lines"]),
        {
            "parking_region": [parking_min.x, parking_min.y, parking_min.z, parking_max.x, parking_max.y, parking_max.z],
            "target_region": [parking_min.x, oy + 1, parking_min.z, parking_max.x, oy + 1, parking_max.z],
            "target_center": target_center,
            "target_size": target_size,
            "parking_block": parking_block,
            "decorations": placed_decorations,
            "decoration_count": len(placed_decorations),
            "agent_a_visibility_constraint": "parking_region_location_and_color_hidden",
            "difficulty": spec.get("difficulty"),
            "difficulty_zh": spec.get("difficulty_zh"),
            "difficulty_constraints": spec.get("difficulty_constraints"),
            "spawn_angle_degrees": float(spec.get("spawn_angle_degrees", 0.0)),
        },
    )


def build_high_platform_gold_guidance_scene(spec: Dict[str, Any], namespace: str) -> Dict[str, Any]:
    common = prepare_common(spec)
    scene_id = common["scene_id"]
    ox, oy, oz = common["origin"].x, common["origin"].y, common["origin"].z
    x1, y1, z1 = common["bounds_max"].x, common["bounds_max"].y, common["bounds_max"].z
    width, height, depth = common["room_size"]

    platform_block = str(spec.get("platform_block", "minecraft:smooth_stone"))
    platform_underlight_block = str(spec.get("platform_underlight_block", "minecraft:glowstone"))
    fence_block = str(spec.get("fence_block", "minecraft:oak_fence"))
    gold_block = str(spec.get("gold_block", "minecraft:gold_block"))
    platform_height = int(spec.get("platform_height", 6))
    platform_width = int(spec.get("platform_width", 3))
    target_span = int(spec.get("target_span", 3))
    path_width = int(spec.get("path_width", 2))
    side_path_length = int(spec.get("side_path_length", 5))
    side_path_side = str(spec.get("side_path_side", "left")).lower()
    side_path_enabled = bool(spec.get("side_path_enabled", True))
    observer_relative_pos = spec.get("observer_relative_pos")
    observer_platform_relative_pos = spec.get("observer_platform_relative_pos", observer_relative_pos)
    observer_rotation = spec.get("observer_rotation", [180.0, 0.0])
    observer_support_block = str(spec.get("observer_support_block", "minecraft:barrier"))
    observer_platform_size = spec.get("observer_platform_size", [1, 1])
    hidden_region_size_value = spec.get("hidden_region_size")
    hidden_region_offset = spec.get("hidden_region_offset")
    gold_candidate_index = int(spec.get("gold_candidate_index", 0))

    if height - 2 != 9:
        raise ValueError(f"{scene_id}: room must have exactly 9 blocks of interior height.")
    if platform_height != 6 or platform_width < 1:
        raise ValueError(f"{scene_id}: wall-side platform must have positive width at floor-relative height 6.")
    if target_span != 3:
        raise ValueError(f"{scene_id}: target span must contain exactly 3 candidate columns.")
    if side_path_enabled and path_width != 2:
        raise ValueError(f"{scene_id}: side path width must be 2.")
    if side_path_enabled and side_path_length != 5:
        raise ValueError(f"{scene_id}: side path length must be 5.")
    if side_path_enabled and side_path_side not in {"left", "right"}:
        raise ValueError(f"{scene_id}: side_path_side must be left or right.")
    if width < 13 or depth < 15:
        raise ValueError(f"{scene_id}: room is too small for the elevated platform and path.")
    if gold_candidate_index not in range(target_span):
        raise ValueError(f"{scene_id}: gold_candidate_index must be 0, 1, or 2.")

    center_x = ox + width // 2
    platform_y = oy + platform_height
    platform_min = Vec3(ox + 1, platform_y, oz + 1)
    platform_max = Vec3(x1 - 1, platform_y, oz + platform_width)
    if platform_min.z != oz + 1:
        raise ValueError(f"{scene_id}: platform must touch the north interior wall with zero gap.")
    path_x0 = platform_min.x if side_path_side == "left" else platform_max.x - path_width + 1
    path_x1 = path_x0 + path_width - 1
    path_min = Vec3(path_x0, platform_y, platform_max.z + 1)
    path_max = Vec3(path_x1, platform_y, platform_max.z + side_path_length)
    if side_path_enabled and path_max.z >= z1:
        raise ValueError(f"{scene_id}: side path does not fit inside the room.")

    if hidden_region_size_value is not None:
        hidden_width, hidden_depth = validate_size_2(hidden_region_size_value, "hidden_region_size")
        if hidden_region_offset is None or len(hidden_region_offset) != 2:
            raise ValueError(f"{scene_id}: hidden_region_offset must contain [x, z].")
        gold_min = Vec3(ox + int(hidden_region_offset[0]), oy + 1, oz + int(hidden_region_offset[1]))
        gold_max = Vec3(gold_min.x + hidden_width - 1, oy + 1, gold_min.z + hidden_depth - 1)
        if gold_min.x < platform_min.x or gold_max.x > platform_max.x or gold_min.z < platform_min.z or gold_max.z > platform_max.z:
            raise ValueError(f"{scene_id}: hidden colored region must stay fully below the platform footprint.")
        gold_region_candidates = [(gold_min, gold_max)]
        gold_candidate_index = 0
    elif side_path_side == "left":
        gold_start_x = platform_max.x - target_span
        gold_x_values = range(gold_start_x, gold_start_x + target_span)
        gold_region_candidates = [
            (Vec3(x, oy + 1, oz + 1), Vec3(x + 1, oy + 1, oz + 2))
            for x in gold_x_values
        ]
    else:
        gold_start_x = platform_min.x
        gold_x_values = range(gold_start_x, gold_start_x + target_span)
        gold_region_candidates = [
            (Vec3(x, oy + 1, oz + 1), Vec3(x + 1, oy + 1, oz + 2))
            for x in gold_x_values
        ]
    if hidden_region_size_value is None:
        gold_min, gold_max = gold_region_candidates[gold_candidate_index]
    target_min = Vec3(gold_min.x, platform_y + 1, gold_min.z)
    target_max = Vec3(gold_max.x, platform_y + 1, gold_max.z)
    agent_a_spawn = Vec3(center_x, platform_y + 1, platform_max.z)
    if observer_relative_pos is None:
        agent_b_start_pos = [center_x + 0.5, float(oy + 1), z1 - 0.5]
    else:
        if len(observer_relative_pos) != 3:
            raise ValueError(f"{scene_id}: observer_relative_pos must contain [x, y, z].")
        agent_b_start_pos = [
            ox + float(observer_relative_pos[0]),
            oy + float(observer_relative_pos[1]),
            oz + float(observer_relative_pos[2]),
        ]
    if len(observer_rotation) != 2:
        raise ValueError(f"{scene_id}: observer_rotation must contain [yaw, pitch].")
    if observer_platform_relative_pos is None:
        observer_platform_pos = agent_b_start_pos
    else:
        if len(observer_platform_relative_pos) != 3:
            raise ValueError(f"{scene_id}: observer_platform_relative_pos must contain [x, y, z].")
        observer_platform_pos = [
            ox + float(observer_platform_relative_pos[0]),
            oy + float(observer_platform_relative_pos[1]),
            oz + float(observer_platform_relative_pos[2]),
        ]
    observer_support = Vec3(
        math.floor(observer_platform_pos[0]),
        math.floor(observer_platform_pos[1]) - 1,
        math.floor(observer_platform_pos[2]),
    )
    observer_platform_width, observer_platform_depth = validate_size_2(observer_platform_size, "observer_platform_size")
    if observer_platform_width < 1 or observer_platform_depth < 1:
        raise ValueError(f"{scene_id}: observer_platform_size must contain positive dimensions.")
    observer_platform_min = Vec3(
        observer_support.x - (observer_platform_width - 1) // 2,
        observer_support.y,
        observer_support.z - (observer_platform_depth - 1) // 2,
    )
    observer_platform_max = Vec3(
        observer_platform_min.x + observer_platform_width - 1,
        observer_support.y,
        observer_platform_min.z + observer_platform_depth - 1,
    )
    gold_path_horizontal_distance = min(abs(gold_min.x - path_x1), abs(gold_max.x - path_x0)) if side_path_enabled else None
    if side_path_enabled and gold_path_horizontal_distance < 8:
        raise ValueError(f"{scene_id}: gold region must stay at least 8 blocks from the side path.")

    if side_path_enabled:
        if side_path_side == "left":
            barrier_lines = [
                fill_cmd(Vec3(platform_min.x + path_width, platform_y + 1, platform_max.z + 1), Vec3(platform_max.x, platform_y + 1, platform_max.z + 1), fence_block),
                fill_cmd(Vec3(path_x1 + 1, platform_y + 1, path_min.z), Vec3(path_x1 + 1, platform_y + 1, path_max.z), fence_block),
            ]
        else:
            barrier_lines = [
                fill_cmd(Vec3(platform_min.x, platform_y + 1, platform_max.z + 1), Vec3(platform_max.x - path_width, platform_y + 1, platform_max.z + 1), fence_block),
                fill_cmd(Vec3(path_x0 - 1, platform_y + 1, path_min.z), Vec3(path_x0 - 1, platform_y + 1, path_max.z), fence_block),
            ]
        barrier_lines.extend(
            [
                fill_cmd(Vec3(path_x0, platform_y + 1, path_max.z + 1), Vec3(path_x1, platform_y + 1, path_max.z + 1), fence_block),
                setblock_cmd(Vec3(path_x1 + 1 if side_path_side == "left" else path_x0 - 1, platform_y + 1, path_max.z + 1), fence_block),
            ]
        )
        path_lines = [fill_cmd(path_min, path_max, platform_block)]
    else:
        barrier_lines = [
            fill_cmd(Vec3(platform_min.x, platform_y + 1, platform_max.z + 1), Vec3(platform_max.x, platform_y + 1, platform_max.z + 1), fence_block)
        ]
        path_lines = []

    setup_lines = list(common["setup_lines"])
    setup_lines.extend(
        [
            fill_cmd(platform_min.shift(dy=-1), platform_max.shift(dy=-1), platform_underlight_block),
            fill_cmd(platform_min, platform_max, platform_block),
            *path_lines,
            *barrier_lines,
            fill_cmd(gold_min, gold_max, gold_block),
            fill_cmd(observer_platform_min, observer_platform_max, observer_support_block),
        ]
    )
    placed_decorations = add_decorations(spec, common, setup_lines)

    return finalize_scene(
        common,
        namespace,
        "high_platform_gold_guidance",
        setup_lines,
        [f"# No command blocks are needed for scene: {scene_id}"],
        [f"# No tick logic is needed for scene: {scene_id}"],
        list(common["clear_lines"]),
        {
            "interior_height": height - 2,
            "platform_region": [platform_min.x, platform_min.y, platform_min.z, platform_max.x, platform_max.y, platform_max.z],
            "adjacent_wall_region": [ox, oy + 1, oz, x1, y1 - 1, oz],
            "platform_wall_gap": 0,
            "platform_width": platform_width,
            "platform_underlight_region": [platform_min.x, platform_min.y - 1, platform_min.z, platform_max.x, platform_max.y - 1, platform_max.z],
            "platform_underlight_block": platform_underlight_block,
            "platform_walk_y": platform_y + 1,
            "elevated_path_region": [path_min.x, path_min.y, path_min.z, path_max.x, path_max.y, path_max.z] if side_path_enabled else None,
            "side_path_enabled": side_path_enabled,
            "side_path_side": side_path_side,
            "side_path_length": side_path_length,
            "side_path_width": path_width,
            "gold_region_candidates": [
                [region_min.x, region_min.y, region_min.z, region_max.x, region_max.y, region_max.z]
                for region_min, region_max in gold_region_candidates
            ],
            "gold_candidate_index": gold_candidate_index,
            "gold_region": [gold_min.x, gold_min.y, gold_min.z, gold_max.x, gold_max.y, gold_max.z],
            "colored_region_block": gold_block,
            "target_region": [target_min.x, target_min.y, target_min.z, target_max.x, target_max.y, target_max.z],
            "gold_side_path_horizontal_distance": gold_path_horizontal_distance,
            "agent_a_start_pos": [agent_a_spawn.x + 0.5, agent_a_spawn.y, agent_a_spawn.z + 0.5],
            "agent_a_start_rotation": [180.0, 0.0],
            "agent_a_start_region": "elevated_platform",
            "agent_a_direction": int(spec.get("agent_a_direction", 1)),
            "agent_b_start_pos": agent_b_start_pos,
            "agent_b_start_rotation": [float(observer_rotation[0]), float(observer_rotation[1])],
            "agent_b_start_region": "fixed_central_observation_position",
            "agent_b_observer_support_pos": [observer_support.x, observer_support.y, observer_support.z],
            "agent_b_observer_support_block": observer_support_block,
            "agent_b_observer_platform_region": [observer_platform_min.x, observer_platform_min.y, observer_platform_min.z, observer_platform_max.x, observer_platform_max.y, observer_platform_max.z],
            "agent_b_observer_platform_size": [observer_platform_width, observer_platform_depth],
            "agent_b_visibility": "full_scene_information",
            "decorations": placed_decorations,
            "decoration_count": len(placed_decorations),
            "failure_y_below": platform_y + 1,
            "difficulty": spec.get("difficulty"),
            "difficulty_zh": spec.get("difficulty_zh"),
            "difficulty_constraints": spec.get("difficulty_constraints"),
        },
    )


def build_maze_command_guidance_scene(spec: Dict[str, Any], namespace: str) -> Dict[str, Any]:
    common = prepare_common(spec)
    scene_id = common["scene_id"]
    ox, oy, oz = common["origin"].x, common["origin"].y, common["origin"].z
    x1, y1, z1 = common["bounds_max"].x, common["bounds_max"].y, common["bounds_max"].z
    width, height, depth = common["room_size"]

    maze_wall_block = str(spec.get("maze_wall_block", "minecraft:gray_concrete"))
    maze_wall_base_block = str(spec.get("maze_wall_base_block", maze_wall_block))
    maze_middle_layer_block = str(spec.get("maze_middle_layer_block", "minecraft:air"))
    wall_light_block = str(spec.get("wall_light_block", "minecraft:glowstone"))
    goal_block = str(spec.get("goal_block", "minecraft:emerald_block"))
    start_block = str(spec.get("start_block", common["floor_block"]))
    maze_size = int(spec.get("maze_size", 15))
    maze_wall_height = int(spec.get("maze_wall_height", 3))
    maze_path_width = int(spec.get("maze_path_width", 2))
    wall_light_height = int(spec.get("wall_light_height", 7))
    maze_seed = int(spec.get("maze_seed", 3107))
    route_points_raw = spec.get("route_points_local")
    branch_rects_raw = spec.get("branch_rects_local", [])
    target_walkable_area = spec.get("target_walkable_area")

    if height != 20:
        raise ValueError(f"{scene_id}: house height must be exactly 20 blocks.")
    if maze_size != 15 or maze_size % 2 == 0:
        raise ValueError(f"{scene_id}: maze_size must be the odd value 15.")
    if maze_wall_height not in {2, 3}:
        raise ValueError(f"{scene_id}: maze walls must be 2 or 3 blocks high.")
    if maze_path_width != 2:
        raise ValueError(f"{scene_id}: maze paths must be exactly 2 blocks wide.")
    if wall_light_height != 7:
        raise ValueError(f"{scene_id}: wall light ring must be exactly 7 blocks above the floor.")
    if width < maze_size + 6 or depth < maze_size + 6:
        raise ValueError(f"{scene_id}: room is too small for the requested maze.")
    if not isinstance(route_points_raw, list) or len(route_points_raw) not in {2, 3}:
        raise ValueError(f"{scene_id}: route_points_local must contain 2 or 3 [x, z] points.")
    if not isinstance(branch_rects_raw, list):
        raise ValueError(f"{scene_id}: branch_rects_local must be a list.")
    if target_walkable_area is not None and not isinstance(target_walkable_area, int):
        raise ValueError(f"{scene_id}: target_walkable_area must be an int.")

    route_points: List[Tuple[int, int]] = []
    local_min = 1
    local_max = maze_size - maze_path_width - 1
    for point in route_points_raw:
        values = list(point) if isinstance(point, list) else []
        if len(values) != 2 or not all(isinstance(value, int) for value in values):
            raise ValueError(f"{scene_id}: each route point must be [int, int].")
        local_x, local_z = values
        if not (local_min <= local_x <= local_max and local_min <= local_z <= local_max):
            raise ValueError(f"{scene_id}: route point {point} is outside the maze interior.")
        route_points.append((local_x, local_z))

    route_turn_count = 0
    for first, second in zip(route_points, route_points[1:]):
        if first[0] != second[0] and first[1] != second[1]:
            raise ValueError(f"{scene_id}: each route segment must be axis-aligned.")
    if len(route_points) == 2:
        route_turn_count = 0
    else:
        first_delta = (route_points[1][0] - route_points[0][0], route_points[1][1] - route_points[0][1])
        second_delta = (route_points[2][0] - route_points[1][0], route_points[2][1] - route_points[1][1])
        if first_delta[0] == 0 and second_delta[0] == 0:
            raise ValueError(f"{scene_id}: three-point route must contain one turn.")
        if first_delta[1] == 0 and second_delta[1] == 0:
            raise ValueError(f"{scene_id}: three-point route must contain one turn.")
        route_turn_count = 1

    maze_x0 = ox + (width - maze_size) // 2
    maze_z0 = oz + (depth - maze_size) // 2
    maze_x1 = maze_x0 + maze_size - 1
    maze_z1 = maze_z0 + maze_size - 1
    maze_min = Vec3(maze_x0, oy + 1, maze_z0)
    maze_max = Vec3(maze_x1, oy + maze_wall_height, maze_z1)

    carved_local = set()

    def carve_rect(local_x0: int, local_z0: int, local_x1: int, local_z1: int) -> None:
        for local_x in range(local_x0, local_x1 + 1):
            for local_z in range(local_z0, local_z1 + 1):
                carved_local.add((local_x, local_z))

    for first, second in zip(route_points, route_points[1:]):
        if first[0] == second[0]:
            carve_rect(first[0], min(first[1], second[1]), first[0] + maze_path_width - 1, max(first[1], second[1]) + maze_path_width - 1)
        else:
            carve_rect(min(first[0], second[0]), first[1], max(first[0], second[0]) + maze_path_width - 1, first[1] + maze_path_width - 1)

    branch_rects: List[List[int]] = []
    for rect in branch_rects_raw:
        values = list(rect) if isinstance(rect, list) else []
        if len(values) != 4 or not all(isinstance(value, int) for value in values):
            raise ValueError(f"{scene_id}: each branch rect must be [x0, z0, x1, z1].")
        local_x0, local_z0, local_x1, local_z1 = values
        if local_x0 > local_x1 or local_z0 > local_z1:
            raise ValueError(f"{scene_id}: branch rect min must be <= max.")
        if not (local_min <= local_x0 <= local_x1 <= local_max + maze_path_width - 1):
            raise ValueError(f"{scene_id}: branch rect x range is outside the maze interior.")
        if not (local_min <= local_z0 <= local_z1 <= local_max + maze_path_width - 1):
            raise ValueError(f"{scene_id}: branch rect z range is outside the maze interior.")
        carve_rect(local_x0, local_z0, local_x1, local_z1)
        branch_rects.append([local_x0, local_z0, local_x1, local_z1])

    walkable_area = len(carved_local)
    if target_walkable_area is not None and walkable_area != target_walkable_area:
        raise ValueError(f"{scene_id}: walkable area is {walkable_area}, expected {target_walkable_area}.")

    start_local = route_points[0]
    goal_local = route_points[-1]
    start_min = Vec3(maze_x0 + start_local[0], oy + 1, maze_z0 + start_local[1])
    start_max = Vec3(start_min.x + maze_path_width - 1, oy + 1, start_min.z + maze_path_width - 1)
    goal_min = Vec3(maze_x0 + goal_local[0], oy + 1, maze_z0 + goal_local[1])
    goal_max = Vec3(goal_min.x + maze_path_width - 1, oy + 1, goal_min.z + maze_path_width - 1)
    start_floor_min = start_min.shift(dy=-1)
    start_floor_max = start_max.shift(dy=-1)
    goal_floor_min = goal_min.shift(dy=-1)
    goal_floor_max = goal_max.shift(dy=-1)

    agent_a_spawn = Vec3(start_min.x, oy + 1, start_min.z)
    agent_b_spawn = Vec3(ox + width // 2, y1 - 1, oz + depth // 2)
    light_y = oy + wall_light_height
    start_center = [start_min.x + 0.5, float(oy + 1), start_min.z + 0.5]
    goal_center = [goal_min.x + 0.5, float(oy + 1), goal_min.z + 0.5]
    first_step = route_points[1]
    first_step_world = [maze_x0 + first_step[0] + 0.5, float(oy + 1), maze_z0 + first_step[1] + 0.5]
    route_distance = round(math.hypot(goal_center[0] - start_center[0], goal_center[2] - start_center[2]), 3)

    def yaw_toward(start: Sequence[float], target: Sequence[float]) -> float:
        return round(math.degrees(math.atan2(-(target[0] - start[0]), target[2] - start[2])), 1)

    setup_lines = list(common["setup_lines"])
    setup_lines.extend(
        [
            fill_cmd(Vec3(ox, light_y, oz), Vec3(x1, light_y, oz), wall_light_block),
            fill_cmd(Vec3(ox, light_y, z1), Vec3(x1, light_y, z1), wall_light_block),
            fill_cmd(Vec3(ox, light_y, oz + 1), Vec3(ox, light_y, z1 - 1), wall_light_block),
            fill_cmd(Vec3(x1, light_y, oz + 1), Vec3(x1, light_y, z1 - 1), wall_light_block),
            fill_cmd(maze_min, maze_max, maze_wall_block),
            fill_cmd(Vec3(maze_x0, oy + 1, maze_z0), Vec3(maze_x1, oy + 1, maze_z1), maze_wall_base_block),
        ]
    )
    if maze_middle_layer_block not in {"minecraft:air", "minecraft:wall_torch"}:
        setup_lines.append(fill_cmd(Vec3(maze_x0, oy + 2, maze_z0), Vec3(maze_x1, oy + 2, maze_z1), maze_middle_layer_block))
    for local_x, local_z in sorted(carved_local):
        passage_min = Vec3(maze_x0 + local_x, oy + 1, maze_z0 + local_z)
        passage_max = Vec3(passage_min.x, oy + maze_wall_height, passage_min.z)
        setup_lines.append(fill_cmd(passage_min, passage_max, "minecraft:air"))
    if maze_middle_layer_block == "minecraft:wall_torch":
        torch_y = oy + 2
        for local_x, local_z in sorted(carved_local):
            torch_pos = Vec3(maze_x0 + local_x, torch_y, maze_z0 + local_z)
            for delta_x, delta_z, facing in ((-1, 0, "east"), (1, 0, "west"), (0, -1, "south"), (0, 1, "north")):
                neighbor = (local_x + delta_x, local_z + delta_z)
                if 0 <= neighbor[0] < maze_size and 0 <= neighbor[1] < maze_size and neighbor not in carved_local:
                    setup_lines.append(setblock_cmd(torch_pos, f"minecraft:wall_torch[facing={facing}]"))
                    break
    setup_lines.extend(
        [
            fill_cmd(start_floor_min, start_floor_max, start_block),
            fill_cmd(goal_floor_min, goal_floor_max, goal_block),
        ]
    )
    placed_decorations = add_decorations(spec, common, setup_lines)

    return finalize_scene(
        common,
        namespace,
        "maze_command_guidance",
        setup_lines,
        [f"# No command blocks are needed for scene: {scene_id}"],
        [f"# No tick logic is needed for scene: {scene_id}"],
        list(common["clear_lines"]),
        {
            "house_height": height,
            "interior_height": height - 2,
            "wall_light_height": wall_light_height,
            "wall_light_y": light_y,
            "maze_region": [maze_min.x, maze_min.y, maze_min.z, maze_max.x, maze_max.y, maze_max.z],
            "maze_size": [maze_size, maze_wall_height, maze_size],
            "maze_path_width": maze_path_width,
            "maze_wall_block": maze_wall_block,
            "maze_wall_base_block": maze_wall_base_block,
            "maze_wall_base_y": oy + 1,
            "maze_middle_layer_y": oy + 2,
            "maze_middle_layer_block": maze_middle_layer_block,
            "maze_middle_layer_lighting": "none" if maze_middle_layer_block == "minecraft:air" else ("wall_torches" if maze_middle_layer_block == "minecraft:wall_torch" else "solid_layer"),
            "maze_seed": maze_seed,
            "maze_route_points_local": [[x, z] for x, z in route_points],
            "maze_route_points_world": [[maze_x0 + x + 0.5, float(oy + 1), maze_z0 + z + 0.5] for x, z in route_points],
            "maze_branch_rects_local": branch_rects,
            "maze_walkable_area": walkable_area,
            "target_walkable_area": target_walkable_area,
            "route_turn_count": route_turn_count,
            "route_straight_line_distance": route_distance,
            "maze_start_region": [start_min.x, start_min.y, start_min.z, start_max.x, start_max.y, start_max.z],
            "maze_goal_region": [goal_min.x, goal_min.y, goal_min.z, goal_max.x, goal_max.y, goal_max.z],
            "goal_region": [goal_min.x, goal_min.y, goal_min.z, goal_max.x, goal_max.y, goal_max.z],
            "goal_floor_region": [goal_floor_min.x, goal_floor_min.y, goal_floor_min.z, goal_floor_max.x, goal_floor_max.y, goal_floor_max.z],
            "target_region": [goal_min.x, goal_min.y, goal_min.z, goal_max.x, goal_max.y, goal_max.z],
            "observation_platform": None,
            "observer_mode": "flying_top_center",
            "agent_a_start_pos": [agent_a_spawn.x + 0.5, agent_a_spawn.y, agent_a_spawn.z + 0.5],
            "agent_a_start_rotation": [yaw_toward(start_center, first_step_world), 0.0],
            "agent_b_start_pos": [agent_b_spawn.x + 0.5, agent_b_spawn.y, agent_b_spawn.z + 0.5],
            "agent_b_start_rotation": [180.0, 90.0],
            "agent_b_start_region": "flying_top_center_observer",
            "decorations": placed_decorations,
            "decoration_count": len(placed_decorations),
            "difficulty": spec.get("difficulty"),
            "difficulty_zh": spec.get("difficulty_zh"),
            "difficulty_constraints": spec.get("difficulty_constraints"),
        },
    )


def build_heavy_object_dual_drag_scene(spec: Dict[str, Any], namespace: str) -> Dict[str, Any]:
    common = prepare_common(spec)
    scene_id = common["scene_id"]
    ox, oy, oz = common["origin"].x, common["origin"].y, common["origin"].z
    x1, y1, z1 = common["bounds_max"].x, common["bounds_max"].y, common["bounds_max"].z
    width, height, depth = common["room_size"]

    heavy_object_block = str(spec.get("heavy_object_block", "minecraft:ancient_debris"))
    target_outline_block = str(spec.get("target_outline_block", "minecraft:yellow_concrete"))
    drag_pad_block = str(spec.get("drag_pad_block", "minecraft:stone_pressure_plate"))
    drag_pad_state = str(spec.get("drag_pad_active_state", "powered=true"))
    moved_object_block = str(spec.get("moved_object_block", heavy_object_block))

    object_size = validate_size(spec.get("heavy_object_size", [3, 2, 3]), "heavy_object_size")
    target_offset = get_required_int(spec, "target_offset")

    obj_w, obj_h, obj_d = object_size
    object_min = Vec3(ox + (width - obj_w) // 2, oy + 1, oz + 2)
    object_max = Vec3(object_min.x + obj_w - 1, object_min.y + obj_h - 1, object_min.z + obj_d - 1)
    moved_min = object_min.shift(dz=target_offset)
    moved_max = object_max.shift(dz=target_offset)
    if moved_max.z >= z1 - 1:
        raise ValueError(f"{scene_id}: target_offset pushes the heavy object outside the room.")
    if obj_h >= height - 1:
        raise ValueError(f"{scene_id}: heavy_object_size is too tall for the room.")

    left_pad = Vec3(object_min.x - 1, oy + 1, object_min.z + obj_d // 2)
    right_pad = Vec3(object_max.x + 1, oy + 1, object_min.z + obj_d // 2)
    if left_pad.x <= ox or right_pad.x >= x1:
        raise ValueError(f"{scene_id}: room is too narrow for dual drag pads.")

    setup_lines = list(common["setup_lines"])
    setup_lines.extend(
        fill_outline(moved_min.shift(dy=-1), moved_max, target_outline_block)
    )
    setup_lines.extend(
        [
            fill_cmd(object_min, object_max, heavy_object_block),
            fill_cmd(moved_min, moved_max, "minecraft:air"),
            setblock_cmd(left_pad.shift(dy=-1), common["floor_block"]),
            setblock_cmd(right_pad.shift(dy=-1), common["floor_block"]),
            setblock_cmd(left_pad, drag_pad_block),
            setblock_cmd(right_pad, drag_pad_block),
            "",
            "# Command blocks that require both agents to drag at the same time.",
            f"function {namespace}:{scene_id}/place_command_blocks",
        ]
    )

    active_pad_block = f"{drag_pad_block}[{drag_pad_state}]"
    both_pressed = f"if block {left_pad.to_cmd()} {active_pad_block} if block {right_pad.to_cmd()} {active_pad_block}"
    left_not_pressed = f"unless block {left_pad.to_cmd()} {active_pad_block}"
    left_only_pressed = f"if block {left_pad.to_cmd()} {active_pad_block} unless block {right_pad.to_cmd()} {active_pad_block}"
    move_start_clear = fill_cmd(object_min, object_max, "minecraft:air")
    move_target_fill = fill_cmd(moved_min, moved_max, moved_object_block)
    reset_start_fill = fill_cmd(object_min, object_max, heavy_object_block)
    reset_target_clear = fill_cmd(moved_min, moved_max, "minecraft:air")

    command_base = common["command_base"]
    place_command_blocks_lines = [
        f"# Place command blocks for scene: {scene_id}",
        (
            f'setblock {command_base.to_cmd()} minecraft:repeating_command_block[facing=east]'
            f'{{auto:1b,Command:"execute {both_pressed} run {move_start_clear}"}}'
        ),
        (
            f'setblock {command_base.shift(dx=1).to_cmd()} minecraft:repeating_command_block[facing=east]'
            f'{{auto:1b,Command:"execute {both_pressed} run {move_target_fill}"}}'
        ),
        (
            f'setblock {command_base.shift(dx=2).to_cmd()} minecraft:repeating_command_block[facing=east]'
            f'{{auto:1b,Command:"execute {left_not_pressed} run {reset_start_fill}"}}'
        ),
        (
            f'setblock {command_base.shift(dx=3).to_cmd()} minecraft:repeating_command_block[facing=east]'
            f'{{auto:1b,Command:"execute {left_not_pressed} run {reset_target_clear}"}}'
        ),
        (
            f'setblock {command_base.shift(dx=4).to_cmd()} minecraft:repeating_command_block[facing=east]'
            f'{{auto:1b,Command:"execute {left_only_pressed} run {reset_start_fill}"}}'
        ),
        (
            f'setblock {command_base.shift(dx=5).to_cmd()} minecraft:repeating_command_block[facing=east]'
            f'{{auto:1b,Command:"execute {left_only_pressed} run {reset_target_clear}"}}'
        ),
    ]
    tick_lines = [
        f"# Tick logic for scene: {scene_id}",
        f"execute {both_pressed} run {move_start_clear}",
        f"execute {both_pressed} run {move_target_fill}",
        f"execute {left_not_pressed} run {reset_start_fill}",
        f"execute {left_not_pressed} run {reset_target_clear}",
        f"execute {left_only_pressed} run {reset_start_fill}",
        f"execute {left_only_pressed} run {reset_target_clear}",
    ]
    clear_lines = list(common["clear_lines"])
    clear_lines.append(fill_cmd(command_base, command_base.shift(dx=5), "minecraft:air"))

    return finalize_scene(
        common,
        namespace,
        "heavy_object_dual_drag",
        setup_lines,
        place_command_blocks_lines,
        tick_lines,
        clear_lines,
        {
            "heavy_object_start": [object_min.x, object_min.y, object_min.z, object_max.x, object_max.y, object_max.z],
            "heavy_object_target": [moved_min.x, moved_min.y, moved_min.z, moved_max.x, moved_max.y, moved_max.z],
            "drag_pad_positions": [
                [left_pad.x, left_pad.y, left_pad.z],
                [right_pad.x, right_pad.y, right_pad.z],
            ],
        },
    )


def build_lift_time_dependency_scene(spec: Dict[str, Any], namespace: str) -> Dict[str, Any]:
    common = prepare_common(spec)
    scene_id = common["scene_id"]
    ox, oy, oz = common["origin"].x, common["origin"].y, common["origin"].z
    x1, _, z1 = common["bounds_max"].x, common["bounds_max"].y, common["bounds_max"].z
    width, _, depth = common["room_size"]

    split_axis = str(spec.get("split_axis", "z")).lower()
    if split_axis not in {"x", "z"}:
        raise ValueError(f"{scene_id}: split_axis must be 'x' or 'z'.")

    source_floor_block = str(spec.get("source_floor_block", "minecraft:calcite"))
    target_floor_block = str(spec.get("target_floor_block", "minecraft:red_wool"))

    if split_axis == "z":
        split_coord = oz + depth // 2
        source_floor_min = Vec3(ox, oy, oz)
        source_floor_max = Vec3(x1, oy, split_coord - 1)
        target_floor_min = Vec3(ox, oy, split_coord)
        target_floor_max = Vec3(x1, oy, z1)
        source_zone_min = Vec3(ox + 1, oy + 1, oz + 1)
        source_zone_max = Vec3(x1 - 1, oy + 1, split_coord - 1)
        target_zone_min = Vec3(ox + 1, oy + 1, split_coord)
        target_zone_max = Vec3(x1 - 1, oy + 1, z1 - 1)
    else:
        split_coord = ox + width // 2
        source_floor_min = Vec3(ox, oy, oz)
        source_floor_max = Vec3(split_coord - 1, oy, z1)
        target_floor_min = Vec3(split_coord, oy, oz)
        target_floor_max = Vec3(x1, oy, z1)
        source_zone_min = Vec3(ox + 1, oy + 1, oz + 1)
        source_zone_max = Vec3(split_coord - 1, oy + 1, z1 - 1)
        target_zone_min = Vec3(split_coord, oy + 1, oz + 1)
        target_zone_max = Vec3(x1 - 1, oy + 1, z1 - 1)

    if source_zone_min.x > source_zone_max.x or source_zone_min.z > source_zone_max.z:
        raise ValueError(f"{scene_id}: source zone is too small for lift_time_dependency.")
    if target_zone_min.x > target_zone_max.x or target_zone_min.z > target_zone_max.z:
        raise ValueError(f"{scene_id}: target zone is too small for lift_time_dependency.")

    object_spawn = Vec3(
        (source_zone_min.x + source_zone_max.x) // 2,
        oy + 1,
        (source_zone_min.z + source_zone_max.z) // 2,
    )
    object_goal = Vec3(
        (target_zone_min.x + target_zone_max.x) // 2,
        oy + 1,
        (target_zone_min.z + target_zone_max.z) // 2,
    )

    setup_lines = list(common["setup_lines"])
    setup_lines.extend(
        [
            fill_cmd(source_floor_min, source_floor_max, source_floor_block),
            fill_cmd(target_floor_min, target_floor_max, target_floor_block),
        ]
    )

    place_command_blocks_lines = [
        f"# No command blocks are needed for scene: {scene_id}",
    ]
    tick_lines = [
        f"# No tick logic is needed for scene: {scene_id}",
    ]
    clear_lines = list(common["clear_lines"])

    return finalize_scene(
        common,
        namespace,
        "lift_time_dependency",
        setup_lines,
        place_command_blocks_lines,
        tick_lines,
        clear_lines,
        {
            "control_mode": "external_mod_binding",
            "split_axis": split_axis,
            "source_floor_block": source_floor_block,
            "target_floor_block": target_floor_block,
            "source_floor_region": [
                source_floor_min.x,
                source_floor_min.y,
                source_floor_min.z,
                source_floor_max.x,
                source_floor_max.y,
                source_floor_max.z,
            ],
            "target_floor_region": [
                target_floor_min.x,
                target_floor_min.y,
                target_floor_min.z,
                target_floor_max.x,
                target_floor_max.y,
                target_floor_max.z,
            ],
            "source_zone": [
                source_zone_min.x,
                source_zone_min.y,
                source_zone_min.z,
                source_zone_max.x,
                source_zone_max.y,
                source_zone_max.z,
            ],
            "target_zone": [
                target_zone_min.x,
                target_zone_min.y,
                target_zone_min.z,
                target_zone_max.x,
                target_zone_max.y,
                target_zone_max.z,
            ],
            "object_spawn_pos": [object_spawn.x, object_spawn.y, object_spawn.z],
            "object_goal_pos": [object_goal.x, object_goal.y, object_goal.z],
        },
    )


def build_scene(spec: Dict[str, Any], namespace: str) -> Dict[str, Any]:
    task_template = str(spec.get("task_template", "elevator_hold_door"))
    if task_template == "elevator_hold_door":
        return build_elevator_scene(spec, namespace)
    if task_template == "pressure_path_reveal":
        return build_pressure_path_reveal_scene(spec, namespace)
    if task_template == "middle_wall_opening":
        return build_middle_wall_opening_scene(spec, namespace)
    if task_template == "reverse_parking_opening":
        return build_reverse_parking_opening_scene(spec, namespace)
    if task_template == "truck_reverse_guidance":
        return build_truck_reverse_guidance_scene(spec, namespace)
    if task_template == "truck_driver":
        return build_truck_driver_scene(spec, namespace)
    if task_template == "high_platform_gold_guidance":
        return build_high_platform_gold_guidance_scene(spec, namespace)
    if task_template == "maze_command_guidance":
        return build_maze_command_guidance_scene(spec, namespace)
    if task_template == "heavy_object_dual_drag":
        return build_heavy_object_dual_drag_scene(spec, namespace)
    if task_template == "lift_time_dependency":
        return build_lift_time_dependency_scene(spec, namespace)
    raise ValueError(f"Unsupported task_template: {task_template}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate batch multi-agent Minecraft scenes.")
    parser.add_argument(
        "--spec",
        default="task_families/time_lock/scene_specs/elevator_time_dependency_batch.json",
        help="Path to the scene spec JSON list.",
    )
    parser.add_argument(
        "--out",
        default="generated",
        help="Output root directory for generated mcfunction files.",
    )
    parser.add_argument(
        "--namespace",
        default=DEFAULT_NAMESPACE,
        help="Datapack namespace for generated functions.",
    )
    parser.add_argument(
        "--pack-name",
        default=DEFAULT_PACK_NAME,
        help="Folder name used under the generated datapacks directory.",
    )
    parser.add_argument(
        "--pack-format",
        type=int,
        default=DEFAULT_PACK_FORMAT,
        help="Datapack pack_format written into pack.mcmeta.",
    )
    parser.add_argument(
        "--scene-gap",
        type=int,
        default=DEFAULT_SCENE_GAP,
        help="Gap in blocks inserted between generated scenes along the X axis.",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    spec_path = (base_dir / args.spec).resolve() if not Path(args.spec).is_absolute() else Path(args.spec)
    out_root = (base_dir / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    datapack_root = out_root / "datapacks" / sanitize_name(args.pack_name)

    if out_root.exists():
        shutil.rmtree(out_root)

    specs = layout_specs_non_overlapping(expand_specs(load_specs(spec_path)), gap=args.scene_gap)
    summaries: List[Dict[str, Any]] = []
    batch_setup_lines = ["# Auto-generated batch setup"]
    batch_clear_lines = ["# Auto-generated batch clear"]

    for spec in specs:
        scene = build_scene(spec, namespace=args.namespace)
        scene_dir = Path(scene["scene_id"])
        write_function_file(datapack_root, args.namespace, scene_dir / "setup.mcfunction", scene["setup"])
        write_function_file(
            datapack_root,
            args.namespace,
            scene_dir / "place_command_blocks.mcfunction",
            scene["place_command_blocks"],
        )
        write_function_file(datapack_root, args.namespace, scene_dir / "tick.mcfunction", scene["tick"])
        write_function_file(datapack_root, args.namespace, scene_dir / "clear.mcfunction", scene["clear"])
        summaries.append(scene["summary"])
        summary = scene["summary"]
        origin_x, _, origin_z = summary["origin"]
        width, _, depth = summary["room_size"]
        backing = int(summary.get("wall_backing_thickness", 0))
        load_x0 = origin_x - backing
        load_z0 = origin_z - backing
        load_x1 = origin_x + width - 1 + backing
        load_z1 = origin_z + depth - 1 + backing
        batch_setup_lines.extend(
            [
                f"forceload add {load_x0} {load_z0} {load_x1} {load_z1}",
                f"function {args.namespace}:{scene['scene_id']}/setup",
                f"forceload remove {load_x0} {load_z0} {load_x1} {load_z1}",
            ]
        )
        batch_clear_lines.extend(
            [
                f"forceload add {load_x0} {load_z0} {load_x1} {load_z1}",
                f"function {args.namespace}:{scene['scene_id']}/clear",
                f"forceload remove {load_x0} {load_z0} {load_x1} {load_z1}",
            ]
        )

    manifest = {
        "namespace": args.namespace,
        "datapack_name": sanitize_name(args.pack_name),
        "datapack_root": relativize_path(datapack_root, base_dir),
        "source_spec": relativize_path(spec_path, base_dir),
        "scene_count": len(summaries),
        "scenes": summaries,
    }

    pack_meta = {
        "pack": {
            "description": "Multi-agent Minecraft scene pack generated by multiagent/scene",
            "pack_format": args.pack_format,
            "supported_formats": DEFAULT_SUPPORTED_FORMATS,
        }
    }

    write_function_file(datapack_root, args.namespace, Path("setup_all.mcfunction"), "\n".join(batch_setup_lines) + "\n")
    write_function_file(datapack_root, args.namespace, Path("clear_all.mcfunction"), "\n".join(batch_clear_lines) + "\n")
    write_text(out_root / "scene_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    write_text(datapack_root / "pack.mcmeta", json.dumps(pack_meta, ensure_ascii=False, indent=2) + "\n")

    print(f"Generated {len(summaries)} scenes into {out_root}")


if __name__ == "__main__":
    main()
