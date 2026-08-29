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
    "easy": {"zh": "简单", "count": 100, "turn_count": 0, "distance": [4.5, 6.5], "walkable_area": 16},
    "medium": {"zh": "中等", "count": 100, "turn_count": 1, "distance": [3.5, 6.5], "walkable_area": 26},
    "hard": {"zh": "困难", "count": 100, "turn_count": 1, "distance": [4.5, 7.5], "walkable_area": 36},
}


def carved_cells(route, branch_rects):
    cells = set()
    for first, second in zip(route, route[1:]):
        if first[0] == second[0]:
            for x in range(first[0], first[0] + 2):
                for z in range(min(first[1], second[1]), max(first[1], second[1]) + 2):
                    cells.add((x, z))
        else:
            for x in range(min(first[0], second[0]), max(first[0], second[0]) + 2):
                for z in range(first[1], first[1] + 2):
                    cells.add((x, z))
    for x0, z0, x1, z1 in branch_rects:
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                cells.add((x, z))
    return cells


def route_remains_connected(cells, blocked, start_cells, goal_cells):
    available = cells - blocked
    frontier = [cell for cell in start_cells if cell in available]
    visited = set(frontier)
    while frontier:
        x, z = frontier.pop()
        for neighbor in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if neighbor in available and neighbor not in visited:
                visited.add(neighbor)
                frontier.append(neighbor)
    return bool(visited & goal_cells)


def decorations_for(difficulty, index, route, branch_rects):
    rng = random.Random(f"maze-decor-v2:{difficulty}:{index}")
    cells = carved_cells(route, branch_rects)
    start = route[0]
    goal = route[-1]
    start_cells = {(start[0] + dx, start[1] + dz) for dx in range(2) for dz in range(2)}
    goal_cells = {(goal[0] + dx, goal[1] + dz) for dx in range(2) for dz in range(2)}
    candidates = list(cells - start_cells - goal_cells)
    rng.shuffle(candidates)
    selected = set()
    target_count = rng.choice((3, 4))
    for candidate in candidates:
        if route_remains_connected(cells, selected | {candidate}, start_cells, goal_cells):
            selected.add(candidate)
            if len(selected) == target_count:
                break
    if len(selected) < 3:
        raise ValueError(f"Cannot place 3 connected-safe decorations for {difficulty}/{index}.")
    return [
        {
            "block": rng.choice(DECORATION_BLOCKS),
            "relative_pos": [4 + x, 4 + z],
            "relative_y": 1,
        }
        for x, z in sorted(selected)
    ]

ROUTES = {
    "easy": [
        [[2, 2], [8, 2]],
        [[3, 3], [3, 9]],
        [[5, 2], [11, 2]],
        [[2, 5], [8, 5]],
        [[9, 3], [9, 9]],
        [[4, 10], [10, 10]],
        [[11, 4], [5, 4]],
        [[2, 11], [8, 11]],
        [[7, 2], [7, 8]],
        [[12, 9], [6, 9]],
    ],
    "medium": [
        [[2, 2], [6, 2], [6, 6]],
        [[3, 10], [3, 6], [7, 6]],
        [[10, 3], [6, 3], [6, 7]],
        [[4, 4], [8, 4], [8, 8]],
        [[9, 9], [9, 5], [5, 5]],
        [[2, 8], [6, 8], [6, 4]],
        [[7, 2], [7, 6], [11, 6]],
        [[12, 10], [8, 10], [8, 6]],
        [[5, 11], [5, 7], [9, 7]],
        [[11, 5], [7, 5], [7, 9]],
    ],
    "hard": [
        [[2, 2], [8, 2], [8, 6]],
        [[3, 11], [3, 5], [7, 5]],
        [[12, 3], [6, 3], [6, 7]],
        [[4, 4], [10, 4], [10, 8]],
        [[10, 11], [10, 6], [5, 6]],
        [[2, 9], [7, 9], [7, 4]],
        [[8, 2], [8, 7], [12, 7]],
        [[12, 10], [7, 10], [7, 5]],
        [[4, 11], [4, 6], [9, 6]],
        [[10, 4], [5, 4], [5, 9]],
    ],
}

BRANCH_RECTS = {
    "easy": [
        [], [], [], [], [], [], [], [], [], [],
    ],
    "medium": [
        [[8, 2, 10, 3]],
        [[3, 3, 4, 5]],
        [[3, 3, 5, 4]],
        [[10, 4, 12, 5]],
        [[11, 5, 13, 6]],
        [[8, 8, 10, 9]],
        [[7, 8, 8, 10]],
        [[5, 10, 7, 11]],
        [[5, 4, 6, 6]],
        [[11, 7, 12, 9]],
    ],
    "hard": [
        [[10, 2, 13, 3], [10, 4, 11, 5]],
        [[3, 2, 5, 4], [6, 3, 8, 3]],
        [[4, 3, 5, 6], [4, 7, 5, 8]],
        [[6, 6, 9, 7], [6, 8, 7, 9]],
        [[5, 8, 9, 9], [8, 10, 9, 10]],
        [[4, 6, 6, 8], [2, 8, 3, 8], [6, 5, 6, 5]],
        [[10, 2, 13, 3], [10, 4, 11, 6]],
        [[4, 8, 6, 11]],
        [[6, 8, 8, 9], [10, 8, 12, 9]],
        [[7, 6, 9, 9]],
    ],
}


def make_corridor_branches(route, target_area):
    cells = set()
    width = 2

    def carve_rect(x0, z0, x1, z1, target):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                target.add((x, z))

    for first, second in zip(route, route[1:]):
        if first[0] == second[0]:
            carve_rect(first[0], min(first[1], second[1]), first[0] + width - 1, max(first[1], second[1]) + width - 1, cells)
        else:
            carve_rect(min(first[0], second[0]), first[1], max(first[0], second[0]) + width - 1, first[1] + width - 1, cells)

    def has_open_3x3(candidate_cells):
        return any(
            all((x + dx, z + dz) in candidate_cells for dx in range(3) for dz in range(3))
            for x in range(13)
            for z in range(13)
        )

    needed = target_area - len(cells)
    if needed < 0 or needed % 2:
        raise ValueError(f"Cannot make 2-wide branches for route {route}: need {needed} cells.")

    branches = []
    while needed > 0:
        best = None
        for x in range(1, 14):
            for z in range(1, 15):
                for rect in ((x, z, x + 1, z), (x, z, x, z + 1)):
                    x0, z0, x1, z1 = rect
                    if x1 > 14 or z1 > 14:
                        continue
                    rect_cells = {(rx, rz) for rx in range(x0, x1 + 1) for rz in range(z0, z1 + 1)}
                    if rect_cells & cells:
                        continue
                    adjacent = any(
                        (rx + dx, rz + dz) in cells
                        for rx, rz in rect_cells
                        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    )
                    if not adjacent:
                        continue
                    if has_open_3x3(cells | rect_cells):
                        continue
                    best = rect
                    break
                if best is not None:
                    break
            if best is not None:
                break
        if best is None:
            raise ValueError(f"Cannot place remaining 2-wide branch for route {route}.")
        branches.append(list(best))
        carve_rect(*best, cells)
        needed -= 2
    return branches


def main():
    specs = []
    for difficulty in ("easy", "medium", "hard"):
        tier = TIERS[difficulty]
        for index, color in enumerate(SCENE_COLORS, 1):
            route = ROUTES[difficulty][(index - 1) % len(ROUTES[difficulty])]
            branch_rects = make_corridor_branches(route, tier["walkable_area"])
            specs.append(
                {
                    "id": f"maze_{difficulty}_{index:02d}",
                    "task_template": "maze_command_guidance",
                    "difficulty": difficulty,
                    "difficulty_zh": tier["zh"],
                    "difficulty_constraints": tier,
                    "origin": [3800, -58, 0],
                    "room_size": [23, 20, 23],
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
                    "wall_light_block": "minecraft:glowstone",
                    "wall_light_height": 7,
                    "maze_size": 15,
                    "maze_wall_height": 3,
                    "maze_path_width": 2,
                    "maze_wall_block": "minecraft:light_gray_concrete",
                    "maze_wall_base_block": "minecraft:glowstone",
                    "maze_middle_layer_block": "minecraft:air",
                    "target_walkable_area": tier["walkable_area"],
                    "goal_block": f"minecraft:{color}",
                    "start_block": "minecraft:white_concrete",
                    "maze_seed": 9100 + index,
                    "route_points_local": route,
                    "branch_rects_local": branch_rects,
                    "decorations": decorations_for(difficulty, index, route, branch_rects),
                }
            )

    output = Path(__file__).resolve().parents[1] / "scene_specs" / "maze_decorated_45_scenes.json"
    output.write_text(json.dumps(specs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(specs)} maze scene specs to {output}")


if __name__ == "__main__":
    main()
