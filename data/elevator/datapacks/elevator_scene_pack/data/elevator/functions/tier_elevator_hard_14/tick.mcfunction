# Tick logic for scene: tier_elevator_hard_14
execute if block 1301 -58 4 minecraft:mangrove_pressure_plate[powered=true] run fill 1301 -58 11 1302 -56 11 minecraft:air
execute if block 1301 -58 5 minecraft:mangrove_pressure_plate[powered=true] run fill 1301 -58 11 1302 -56 11 minecraft:air
execute if block 1301 -58 6 minecraft:mangrove_pressure_plate[powered=true] run fill 1301 -58 11 1302 -56 11 minecraft:air
execute if block 1302 -58 4 minecraft:mangrove_pressure_plate[powered=true] run fill 1301 -58 11 1302 -56 11 minecraft:air
execute if block 1302 -58 5 minecraft:mangrove_pressure_plate[powered=true] run fill 1301 -58 11 1302 -56 11 minecraft:air
execute if block 1302 -58 6 minecraft:mangrove_pressure_plate[powered=true] run fill 1301 -58 11 1302 -56 11 minecraft:air
execute if block 1303 -58 4 minecraft:mangrove_pressure_plate[powered=true] run fill 1301 -58 11 1302 -56 11 minecraft:air
execute if block 1303 -58 5 minecraft:mangrove_pressure_plate[powered=true] run fill 1301 -58 11 1302 -56 11 minecraft:air
execute if block 1303 -58 6 minecraft:mangrove_pressure_plate[powered=true] run fill 1301 -58 11 1302 -56 11 minecraft:air
execute unless block 1301 -58 4 minecraft:mangrove_pressure_plate[powered=true] unless block 1301 -58 5 minecraft:mangrove_pressure_plate[powered=true] unless block 1301 -58 6 minecraft:mangrove_pressure_plate[powered=true] unless block 1302 -58 4 minecraft:mangrove_pressure_plate[powered=true] unless block 1302 -58 5 minecraft:mangrove_pressure_plate[powered=true] unless block 1302 -58 6 minecraft:mangrove_pressure_plate[powered=true] unless block 1303 -58 4 minecraft:mangrove_pressure_plate[powered=true] unless block 1303 -58 5 minecraft:mangrove_pressure_plate[powered=true] unless block 1303 -58 6 minecraft:mangrove_pressure_plate[powered=true] run fill 1301 -58 11 1302 -56 11 minecraft:brown_concrete
