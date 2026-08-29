import argparse
from pathlib import Path
import json, math, random, shutil

BASE = Path(__file__).resolve().parents[3]
OUT = BASE / "final_data" / "bridge"
PACK = OUT / "datapacks" / "bridge_scene_pack"
NS = "bridge"
SEED = 719

TIERS = {
    "easy": {"zh":"简单", "count":34, "bridge_width":4, "bridge_length":4, "edge_max":2},
    "medium": {"zh":"中等", "count":33, "bridge_width":3, "bridge_length":5, "edge_max":2},
    "hard": {"zh":"困难", "count":33, "bridge_width":2, "bridge_length":6, "edge_max":2},
}
COLORS = ["red_concrete","orange_concrete","yellow_concrete","lime_concrete","cyan_concrete","blue_concrete","magenta_concrete","purple_concrete","green_concrete","pink_concrete"]

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip()+"\n", encoding="utf-8")

def fill(a,b,block):
    return f"fill {a[0]} {a[1]} {a[2]} {b[0]} {b[1]} {b[2]} {block}"

def region_center(r):
    return [(r[0]+r[3])/2+0.0, float(r[1]), (r[2]+r[5])/2+0.0]

def yaw_toward(start, target, jitter=12.0, rng=None):
    yaw = math.degrees(math.atan2(-(target[0]-start[0]), target[2]-start[2]))
    if rng:
        yaw += rng.uniform(-jitter, jitter)
    yaw = (yaw + 180) % 360 - 180
    return [round(yaw,1), 0.0]

def point(cell,y): return [cell[0]+0.5, float(y), cell[1]+0.5]

def make_scene(difficulty, idx):
    tier = TIERS[difficulty]
    ox = idx * 36
    oz = {"easy": 1200, "medium": 1260, "hard": 1320}[difficulty]
    oy = -57
    room_w, room_d, room_h = 22, 24, 8
    bw, bl = tier["bridge_width"], tier["bridge_length"]
    x0, x1 = ox, ox + room_w - 1
    z0, z1 = oz, oz + room_d - 1
    cx0 = ox + (room_w - bw)//2
    cx1 = cx0 + bw - 1
    bridge_z0 = oz + 10
    bridge_z1 = bridge_z0 + bl - 1
    left_wall_x0, left_wall_x1 = x0 + 1, cx0 - 1
    right_wall_x0, right_wall_x1 = cx1 + 1, x1 - 1
    near_region = [x0+1, oy, z0+1, x1-1, oy, bridge_z0-1]
    far_region = [x0+1, oy, bridge_z1+1, x1-1, oy, z1-1]
    bridge_region = [cx0, oy, bridge_z0, cx1, oy, bridge_z1]
    left_wall_region = [left_wall_x0, oy, bridge_z0, left_wall_x1, oy+2, bridge_z1]
    right_wall_region = [right_wall_x0, oy, bridge_z0, right_wall_x1, oy+2, bridge_z1]
    color = COLORS[(idx-1)%10]
    scene_id = f"tier_bridge_{difficulty}_{idx:02d}"
    cmds = [
        f"# Scene: {scene_id}",
        fill([x0,oy-1,z0],[x1,oy-1,z1],"minecraft:white_concrete"),
        fill([x0,oy,z0],[x1,oy+room_h-1,z1],"minecraft:air"),
        fill([x0,oy,z0],[x1,oy+room_h-1,z0],"minecraft:white_concrete"),
        fill([x0,oy,z1],[x1,oy+room_h-1,z1],"minecraft:white_concrete"),
        fill([x0,oy,z0],[x0,oy+room_h-1,z1],"minecraft:white_concrete"),
        fill([x1,oy,z0],[x1,oy+room_h-1,z1],"minecraft:white_concrete"),
        fill([x0,oy+room_h-1,z0],[x1,oy+room_h-1,z1],"minecraft:white_concrete"),
        fill([x0+3,oy+room_h-1,z0+3],[x1-3,oy+room_h-1,z1-3],"minecraft:glowstone"),
        fill([cx0,oy-1,bridge_z0],[cx1,oy-1,bridge_z1],f"minecraft:{color}"),
        fill([left_wall_x0,oy,bridge_z0],[left_wall_x1,oy+2,bridge_z1],"minecraft:gray_concrete"),
        fill([right_wall_x0,oy,bridge_z0],[right_wall_x1,oy+2,bridge_z1],"minecraft:gray_concrete"),
    ]
    clear = [
        f"# Clear scene: {scene_id}",
        fill([x0-1,oy-2,z0-1],[x1+1,oy+room_h,z1+1],"minecraft:air"),
    ]
    rel = Path(scene_id)
    write(PACK/"data"/NS/"function"/rel/"setup.mcfunction", "\n".join(cmds))
    write(PACK/"data"/NS/"function"/rel/"clear.mcfunction", "\n".join(clear))
    # plural compatibility
    write(PACK/"data"/NS/"functions"/rel/"setup.mcfunction", "\n".join(cmds))
    write(PACK/"data"/NS/"functions"/rel/"clear.mcfunction", "\n".join(clear))
    return {
        "scene_id": scene_id,
        "namespace": NS,
        "task_template": "bridge",
        "origin": [ox, oy, oz],
        "room_size": [room_w, room_h, room_d],
        "setup_function": f"{NS}:{scene_id}/setup",
        "clear_function": f"{NS}:{scene_id}/clear",
        "bridge_width": bw,
        "bridge_length": bl,
        "bridge_block": f"minecraft:{color}",
        "bridge_region": bridge_region,
        "left_wall_region": left_wall_region,
        "right_wall_region": right_wall_region,
        "near_bank_region": near_region,
        "far_bank_region": far_region,
        "goal_region": [x0+1, oy, bridge_z1+1, x1-1, oy, z1-1],
        "wall_height_beside_bridge": 3,
        "difficulty": difficulty,
        "difficulty_zh": tier["zh"],
        "difficulty_constraints": tier,
    }

def per_scene_counts(total):
    q,r=divmod(total,10)
    return [q+(1 if i<r else 0) for i in range(10)]

def build_task(scene, rng, task_id):
    br=scene["bridge_region"]
    near=scene["near_bank_region"]
    goal=scene["goal_region"]
    y=br[1]
    edge_max=scene["difficulty_constraints"]["edge_max"]
    candidates=[]
    for x in range(br[0], br[3]+1):
        for z in range(br[2]-edge_max, br[2]):
            if near[0] <= x <= near[3] and near[2] <= z <= near[5]:
                candidates.append((x,z))
    if len(candidates)<2:
        raise RuntimeError(scene["scene_id"]+" no candidates")
    a_cell,b_cell=rng.sample(candidates,2)
    a_start=point(a_cell,y)
    b_start=point(b_cell,y)
    target=[(br[0]+br[3])/2+0.5,float(y),float(br[2])+0.5]
    return {
        "id": task_id,
        "scene_id": scene["scene_id"],
        "task_template": "bridge",
        "scene_setup_function": scene["setup_function"],
        "scene_clear_function": scene["clear_function"],
        "task_description": "Player A and Player B must both cross the colored bridge corridor and reach the opposite bank.",
        "success_condition_logic": "all",
        "failure_condition_logic": "any",
        "players": {
            "player_a": {"role":"bridge_crosser", "start_pos":a_start, "start_rotation":yaw_toward(a_start,target,10,rng), "goal":{"type":"reach_region", "target_pos":region_center(goal), "target_region":goal, "bridge_region":scene["bridge_region"], "description":"Cross the bridge and reach the opposite bank."}},
            "player_b": {"role":"bridge_crosser", "start_pos":b_start, "start_rotation":yaw_toward(b_start,target,10,rng), "goal":{"type":"reach_region", "target_pos":region_center(goal), "target_region":goal, "bridge_region":scene["bridge_region"], "description":"Cross the bridge and reach the opposite bank."}},
        },
        "success_conditions": [
            {"type":"player_in_region", "player":"player_a", "target_region":goal, "description":"Player A has reached the opposite bank."},
            {"type":"player_in_region", "player":"player_b", "target_region":goal, "description":"Player B has reached the opposite bank."},
        ],
        "failure_conditions": [
            {"type":"player_below_y", "player":"player_a", "y_below":y, "comparison":"less_than", "description":"Player A has fallen below the bridge floor level."},
            {"type":"player_below_y", "player":"player_b", "y_below":y, "comparison":"less_than", "description":"Player B has fallen below the bridge floor level."},
        ],
        "difficulty": scene["difficulty"],
        "difficulty_zh": scene["difficulty_zh"],
        "difficulty_constraints": scene["difficulty_constraints"],
        "spawn_metrics": {"player_a_bank_edge_distance": br[2]-a_cell[1], "player_b_bank_edge_distance": br[2]-b_cell[1]},
    }

def main():
    global OUT, PACK
    parser = argparse.ArgumentParser(description="Generate the complete Bridge dataset.")
    parser.add_argument(
        "--out",
        default=str(BASE / "final_data" / "bridge"),
        help="Output directory for the manifest, tasks, and datapack.",
    )
    args = parser.parse_args()
    OUT = Path(args.out).resolve()
    PACK = OUT / "datapacks" / "bridge_scene_pack"
    if OUT.exists(): shutil.rmtree(OUT)
    write(PACK/"pack.mcmeta", json.dumps({"pack":{"pack_format":48,"supported_formats":{"min_inclusive":34,"max_inclusive":61},"description":"Bridge crossing scene pack"}}, ensure_ascii=False))
    scenes=[]
    for diff in ["easy","medium","hard"]:
        for i in range(1,11):
            scenes.append(make_scene(diff,i))
    try:
        datapack_root = str(PACK.relative_to(BASE))
        manifest_path = str((OUT / "scene_manifest.json").relative_to(BASE))
    except ValueError:
        datapack_root = str(PACK)
        manifest_path = str(OUT / "scene_manifest.json")
    manifest={"namespace":NS,"datapack_name":"bridge_scene_pack","datapack_root":datapack_root,"source_spec":"task_families/bridge/scripts/generate_bridge_dataset.py","scene_count":len(scenes),"scenes":scenes}
    write(OUT/"scene_manifest.json", json.dumps(manifest,ensure_ascii=False,indent=2))
    rng=random.Random(SEED)
    tasks=[]; tid=0
    for diff in ["easy","medium","hard"]:
        diff_scenes=[s for s in scenes if s["difficulty"]==diff]
        for scene,count in zip(diff_scenes, per_scene_counts(TIERS[diff]["count"])):
            for _ in range(count):
                tasks.append(build_task(scene,rng,tid)); tid+=1
    payload={"dataset_name":"bridge","manifest_path":manifest_path,"namespace":NS,"task_count":len(tasks),"scene_count":len(scenes),"seed":SEED,"tasks":tasks}
    write(OUT/"generated_tasks.json", json.dumps(payload,ensure_ascii=False,indent=2))
    print(f"Generated {len(scenes)} scenes and {len(tasks)} tasks into {OUT}")

if __name__ == "__main__": main()

