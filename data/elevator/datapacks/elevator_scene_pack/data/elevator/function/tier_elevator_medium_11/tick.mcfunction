# Tick logic for scene: tier_elevator_medium_11
execute if block 760 -58 7 minecraft:oak_pressure_plate[powered=true] run fill 761 -58 12 762 -56 12 minecraft:air
execute if block 760 -58 8 minecraft:oak_pressure_plate[powered=true] run fill 761 -58 12 762 -56 12 minecraft:air
execute if block 760 -58 9 minecraft:oak_pressure_plate[powered=true] run fill 761 -58 12 762 -56 12 minecraft:air
execute if block 761 -58 7 minecraft:oak_pressure_plate[powered=true] run fill 761 -58 12 762 -56 12 minecraft:air
execute if block 761 -58 8 minecraft:oak_pressure_plate[powered=true] run fill 761 -58 12 762 -56 12 minecraft:air
execute if block 761 -58 9 minecraft:oak_pressure_plate[powered=true] run fill 761 -58 12 762 -56 12 minecraft:air
execute if block 762 -58 7 minecraft:oak_pressure_plate[powered=true] run fill 761 -58 12 762 -56 12 minecraft:air
execute if block 762 -58 8 minecraft:oak_pressure_plate[powered=true] run fill 761 -58 12 762 -56 12 minecraft:air
execute if block 762 -58 9 minecraft:oak_pressure_plate[powered=true] run fill 761 -58 12 762 -56 12 minecraft:air
execute unless block 760 -58 7 minecraft:oak_pressure_plate[powered=true] unless block 760 -58 8 minecraft:oak_pressure_plate[powered=true] unless block 760 -58 9 minecraft:oak_pressure_plate[powered=true] unless block 761 -58 7 minecraft:oak_pressure_plate[powered=true] unless block 761 -58 8 minecraft:oak_pressure_plate[powered=true] unless block 761 -58 9 minecraft:oak_pressure_plate[powered=true] unless block 762 -58 7 minecraft:oak_pressure_plate[powered=true] unless block 762 -58 8 minecraft:oak_pressure_plate[powered=true] unless block 762 -58 9 minecraft:oak_pressure_plate[powered=true] run fill 761 -58 12 762 -56 12 minecraft:light_gray_concrete
