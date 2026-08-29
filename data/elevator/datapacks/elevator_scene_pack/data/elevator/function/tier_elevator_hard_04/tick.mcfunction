# Tick logic for scene: tier_elevator_hard_04
execute if block 1001 -58 4 minecraft:acacia_pressure_plate[powered=true] run fill 1000 -58 11 1001 -56 11 minecraft:air
execute if block 1001 -58 5 minecraft:acacia_pressure_plate[powered=true] run fill 1000 -58 11 1001 -56 11 minecraft:air
execute if block 1001 -58 6 minecraft:acacia_pressure_plate[powered=true] run fill 1000 -58 11 1001 -56 11 minecraft:air
execute if block 1002 -58 4 minecraft:acacia_pressure_plate[powered=true] run fill 1000 -58 11 1001 -56 11 minecraft:air
execute if block 1002 -58 5 minecraft:acacia_pressure_plate[powered=true] run fill 1000 -58 11 1001 -56 11 minecraft:air
execute if block 1002 -58 6 minecraft:acacia_pressure_plate[powered=true] run fill 1000 -58 11 1001 -56 11 minecraft:air
execute if block 1003 -58 4 minecraft:acacia_pressure_plate[powered=true] run fill 1000 -58 11 1001 -56 11 minecraft:air
execute if block 1003 -58 5 minecraft:acacia_pressure_plate[powered=true] run fill 1000 -58 11 1001 -56 11 minecraft:air
execute if block 1003 -58 6 minecraft:acacia_pressure_plate[powered=true] run fill 1000 -58 11 1001 -56 11 minecraft:air
execute unless block 1001 -58 4 minecraft:acacia_pressure_plate[powered=true] unless block 1001 -58 5 minecraft:acacia_pressure_plate[powered=true] unless block 1001 -58 6 minecraft:acacia_pressure_plate[powered=true] unless block 1002 -58 4 minecraft:acacia_pressure_plate[powered=true] unless block 1002 -58 5 minecraft:acacia_pressure_plate[powered=true] unless block 1002 -58 6 minecraft:acacia_pressure_plate[powered=true] unless block 1003 -58 4 minecraft:acacia_pressure_plate[powered=true] unless block 1003 -58 5 minecraft:acacia_pressure_plate[powered=true] unless block 1003 -58 6 minecraft:acacia_pressure_plate[powered=true] run fill 1000 -58 11 1001 -56 11 minecraft:brown_concrete
