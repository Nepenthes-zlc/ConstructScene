# Tick logic for scene: tier_elevator_hard_11
execute if block 1210 -58 6 minecraft:oak_pressure_plate[powered=true] run fill 1211 -58 12 1212 -56 12 minecraft:air
execute if block 1210 -58 7 minecraft:oak_pressure_plate[powered=true] run fill 1211 -58 12 1212 -56 12 minecraft:air
execute if block 1210 -58 8 minecraft:oak_pressure_plate[powered=true] run fill 1211 -58 12 1212 -56 12 minecraft:air
execute if block 1211 -58 6 minecraft:oak_pressure_plate[powered=true] run fill 1211 -58 12 1212 -56 12 minecraft:air
execute if block 1211 -58 7 minecraft:oak_pressure_plate[powered=true] run fill 1211 -58 12 1212 -56 12 minecraft:air
execute if block 1211 -58 8 minecraft:oak_pressure_plate[powered=true] run fill 1211 -58 12 1212 -56 12 minecraft:air
execute if block 1212 -58 6 minecraft:oak_pressure_plate[powered=true] run fill 1211 -58 12 1212 -56 12 minecraft:air
execute if block 1212 -58 7 minecraft:oak_pressure_plate[powered=true] run fill 1211 -58 12 1212 -56 12 minecraft:air
execute if block 1212 -58 8 minecraft:oak_pressure_plate[powered=true] run fill 1211 -58 12 1212 -56 12 minecraft:air
execute unless block 1210 -58 6 minecraft:oak_pressure_plate[powered=true] unless block 1210 -58 7 minecraft:oak_pressure_plate[powered=true] unless block 1210 -58 8 minecraft:oak_pressure_plate[powered=true] unless block 1211 -58 6 minecraft:oak_pressure_plate[powered=true] unless block 1211 -58 7 minecraft:oak_pressure_plate[powered=true] unless block 1211 -58 8 minecraft:oak_pressure_plate[powered=true] unless block 1212 -58 6 minecraft:oak_pressure_plate[powered=true] unless block 1212 -58 7 minecraft:oak_pressure_plate[powered=true] unless block 1212 -58 8 minecraft:oak_pressure_plate[powered=true] run fill 1211 -58 12 1212 -56 12 minecraft:light_gray_concrete
