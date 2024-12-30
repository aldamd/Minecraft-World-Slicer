import json

with open("blocks.json", "r") as r:
  blocks = json.load(r)

lower_x = 180
upper_x = 340
lower_z = 323
upper_z = 474
lower_y = 80

y_offset = 0
y_coord = y_offset + lower_y

rows = []
for z_coord in range(lower_z, upper_z + 1):
  row = []
  for x_coord in range(lower_x, upper_x + 1):
    row.append(f'{blocks[f"{x_coord}, {z_coord}, {y_coord}"]:25s}')
  rows.append(row)

content = "\n".join([" | ".join(i) for i in rows])
    
with open("layer.txt", "w") as w:
  w.write(content)

#TODO show how much material is needed in a given layer