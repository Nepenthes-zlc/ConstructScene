# Tick logic for scene: tier_elevator_hard_02
execute if block 942 -58 4 minecraft:oak_pressure_plate[powered=true] run fill 941 -58 11 942 -56 11 minecraft:air
execute if block 942 -58 5 minecraft:oak_pressure_plate[powered=true] run fill 941 -58 11 942 -56 11 minecraft:air
execute if block 942 -58 6 minecraft:oak_pressure_plate[powered=true] run fill 941 -58 11 942 -56 11 minecraft:air
execute if block 943 -58 4 minecraft:oak_pressure_plate[powered=true] run fill 941 -58 11 942 -56 11 minecraft:air
execute if block 943 -58 5 minecraft:oak_pressure_plate[powered=true] run fill 941 -58 11 942 -56 11 minecraft:air
execute if block 943 -58 6 minecraft:oak_pressure_plate[powered=true] run fill 941 -58 11 942 -56 11 minecraft:air
execute if block 944 -58 4 minecraft:oak_pressure_plate[powered=true] run fill 941 -58 11 942 -56 11 minecraft:air
execute if block 944 -58 5 minecraft:oak_pressure_plate[powered=true] run fill 941 -58 11 942 -56 11 minecraft:air
execute if block 944 -58 6 minecraft:oak_pressure_plate[powered=true] run fill 941 -58 11 942 -56 11 minecraft:air
execute unless block 942 -58 4 minecraft:oak_pressure_plate[powered=true] unless block 942 -58 5 minecraft:oak_pressure_plate[powered=true] unless block 942 -58 6 minecraft:oak_pressure_plate[powered=true] unless block 943 -58 4 minecraft:oak_pressure_plate[powered=true] unless block 943 -58 5 minecraft:oak_pressure_plate[powered=true] unless block 943 -58 6 minecraft:oak_pressure_plate[powered=true] unless block 944 -58 4 minecraft:oak_pressure_plate[powered=true] unless block 944 -58 5 minecraft:oak_pressure_plate[powered=true] unless block 944 -58 6 minecraft:oak_pressure_plate[powered=true] run fill 941 -58 11 942 -56 11 minecraft:gray_concrete
