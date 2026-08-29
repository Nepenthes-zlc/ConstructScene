# Tick logic for scene: tier_elevator_hard_01
execute if block 910 -58 6 minecraft:stone_pressure_plate[powered=true] run fill 910 -58 12 911 -56 12 minecraft:air
execute if block 910 -58 7 minecraft:stone_pressure_plate[powered=true] run fill 910 -58 12 911 -56 12 minecraft:air
execute if block 910 -58 8 minecraft:stone_pressure_plate[powered=true] run fill 910 -58 12 911 -56 12 minecraft:air
execute if block 911 -58 6 minecraft:stone_pressure_plate[powered=true] run fill 910 -58 12 911 -56 12 minecraft:air
execute if block 911 -58 7 minecraft:stone_pressure_plate[powered=true] run fill 910 -58 12 911 -56 12 minecraft:air
execute if block 911 -58 8 minecraft:stone_pressure_plate[powered=true] run fill 910 -58 12 911 -56 12 minecraft:air
execute if block 912 -58 6 minecraft:stone_pressure_plate[powered=true] run fill 910 -58 12 911 -56 12 minecraft:air
execute if block 912 -58 7 minecraft:stone_pressure_plate[powered=true] run fill 910 -58 12 911 -56 12 minecraft:air
execute if block 912 -58 8 minecraft:stone_pressure_plate[powered=true] run fill 910 -58 12 911 -56 12 minecraft:air
execute unless block 910 -58 6 minecraft:stone_pressure_plate[powered=true] unless block 910 -58 7 minecraft:stone_pressure_plate[powered=true] unless block 910 -58 8 minecraft:stone_pressure_plate[powered=true] unless block 911 -58 6 minecraft:stone_pressure_plate[powered=true] unless block 911 -58 7 minecraft:stone_pressure_plate[powered=true] unless block 911 -58 8 minecraft:stone_pressure_plate[powered=true] unless block 912 -58 6 minecraft:stone_pressure_plate[powered=true] unless block 912 -58 7 minecraft:stone_pressure_plate[powered=true] unless block 912 -58 8 minecraft:stone_pressure_plate[powered=true] run fill 910 -58 12 911 -56 12 minecraft:light_gray_concrete
