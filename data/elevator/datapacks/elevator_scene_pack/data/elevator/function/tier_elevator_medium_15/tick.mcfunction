# Tick logic for scene: tier_elevator_medium_15
execute if block 878 -58 7 minecraft:stone_pressure_plate[powered=true] run fill 879 -58 12 880 -56 12 minecraft:air
execute if block 878 -58 8 minecraft:stone_pressure_plate[powered=true] run fill 879 -58 12 880 -56 12 minecraft:air
execute if block 878 -58 9 minecraft:stone_pressure_plate[powered=true] run fill 879 -58 12 880 -56 12 minecraft:air
execute if block 879 -58 7 minecraft:stone_pressure_plate[powered=true] run fill 879 -58 12 880 -56 12 minecraft:air
execute if block 879 -58 8 minecraft:stone_pressure_plate[powered=true] run fill 879 -58 12 880 -56 12 minecraft:air
execute if block 879 -58 9 minecraft:stone_pressure_plate[powered=true] run fill 879 -58 12 880 -56 12 minecraft:air
execute if block 880 -58 7 minecraft:stone_pressure_plate[powered=true] run fill 879 -58 12 880 -56 12 minecraft:air
execute if block 880 -58 8 minecraft:stone_pressure_plate[powered=true] run fill 879 -58 12 880 -56 12 minecraft:air
execute if block 880 -58 9 minecraft:stone_pressure_plate[powered=true] run fill 879 -58 12 880 -56 12 minecraft:air
execute unless block 878 -58 7 minecraft:stone_pressure_plate[powered=true] unless block 878 -58 8 minecraft:stone_pressure_plate[powered=true] unless block 878 -58 9 minecraft:stone_pressure_plate[powered=true] unless block 879 -58 7 minecraft:stone_pressure_plate[powered=true] unless block 879 -58 8 minecraft:stone_pressure_plate[powered=true] unless block 879 -58 9 minecraft:stone_pressure_plate[powered=true] unless block 880 -58 7 minecraft:stone_pressure_plate[powered=true] unless block 880 -58 8 minecraft:stone_pressure_plate[powered=true] unless block 880 -58 9 minecraft:stone_pressure_plate[powered=true] run fill 879 -58 12 880 -56 12 minecraft:light_blue_concrete
