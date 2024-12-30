import json
from math import floor
import os
from glob import glob
import anvil
from PIL import Image, ImageDraw

# %%

class WorldScanner:
  def __init__(self, upper_x, lower_x, upper_z, lower_z, upper_y, lower_y, region_files):
    self.__lower_x = lower_x
    self.__upper_x = upper_x
    self.__lower_z = lower_z
    self.__upper_z = upper_z
    self.__upper_y = upper_y
    self.__lower_y = lower_y
    self.__region_files = region_files

    self.blocks = None
    self.__read_json()

    self.layer_enumerations = None

  def __read_json(self):
    filedir = os.path.abspath(os.path.dirname(__file__))
    json_dir = os.path.join(filedir, "blocks.json")
    if os.path.exists(json_dir):
      with open(json_dir, "r") as r:
        self.blocks = json.load(r)
  
  def __write_json(self):
    with open("blocks.json", "w") as w:
      json.dump(self.blocks, w, indent=1)
    
    with open("enumeration.json", "w") as w:
      json.dump(self.enumerated_blocks, w, indent=1)

  def __validate_region_files(self):
    if os.path.basename(self.__region_files) == "region":
      mca_files = glob(os.path.join(self.__region_files, "*.mca"))
      if mca_files:
        return
    else:
      self.__region_files = os.path.join(self.__region_files, "region")
      if os.path.exists(self.__region_files):
        mca_files = glob(os.path.join(self.__region_files, "*.mca"))
        if mca_files:
          return
    raise Exception(f"Invalid input region_file: {self.__region_files}")

  @staticmethod
  def __chunk_divide(coord: int):
    #CHUNK SIZE is 16 blocks
    return floor(coord / 16)
  
  @staticmethod
  def __region_divide(chunk: int):
    #REGION SIZE is 32 chunks
    return floor(chunk / 32)

  def __parameterize(self):
    lower_x_chunk = self.__chunk_divide(self.__lower_x)
    upper_x_chunk = self.__chunk_divide(self.__upper_x)
    lower_z_chunk = self.__chunk_divide(self.__lower_z)
    upper_z_chunk = self.__chunk_divide(self.__upper_z)

    x_chunk_range = list(range(lower_x_chunk, upper_x_chunk + 1))
    z_chunk_range = list(range(lower_z_chunk, upper_z_chunk + 1))

    lower_x_region = self.__region_divide(lower_x_chunk)
    upper_x_region = self.__region_divide(upper_x_chunk)
    lower_z_region = self.__region_divide(lower_z_chunk)
    upper_z_region = self.__region_divide(upper_z_chunk)

    x_region_range = list(range(lower_x_region, upper_x_region + 1))
    z_region_range = list(range(lower_z_region, upper_z_region + 1))

    regions = {}
    for x in x_region_range:
      for z in z_region_range:
        regions[(x, z)] = anvil.Region.from_file(os.path.join(self.__region_files, f"r.{x}.{z}.mca"))

    chunks = {}
    for x_chunk in x_chunk_range:
      offset_x_chunk = x_chunk
      if abs(x_chunk) >= 32:
        offset_x_chunk = x_chunk % 32
      for z_chunk in z_chunk_range:
        offset_z_chunk = z_chunk
        region_x = floor(x_chunk / 32)
        region_z = floor(z_chunk / 32)
        if abs(z_chunk) >= 32:
          offset_z_chunk = z_chunk % 32
        region = regions[(region_x, region_z)]
        chunks[((region_x, region_z), x_chunk, z_chunk)] = anvil.Chunk.from_region(region, offset_x_chunk, offset_z_chunk)

    self.__lower_x_chunk = lower_x_chunk
    self.__upper_x_chunk = upper_x_chunk
    self.__lower_z_chunk = lower_z_chunk
    self.__upper_z_chunk = upper_z_chunk

    self.regions = regions
    self.chunks = chunks
  
  def __scan_blocks(self):
    blocks = {}
    enumerated_blocks = {}
    for y_coord in range(self.__lower_y, self.__upper_y + 1):
      for z_chunk in range(self.__lower_z_chunk, self.__upper_z_chunk + 1):
        z_region = self.__region_divide(z_chunk)
        for z_coord in range(16):
          global_z_coord = z_chunk * 16 + z_coord
          if global_z_coord > self.__upper_z or global_z_coord < self.__lower_z: continue
          for x_chunk in range(self.__lower_x_chunk, self.__upper_x_chunk + 1):
            x_region = self.__region_divide(x_chunk)
            chunk = self.chunks[(x_region, z_region), x_chunk, z_chunk]
            for x_coord in range(16):
              global_x_coord = x_chunk * 16 + x_coord
              if global_x_coord > self.__upper_x or global_x_coord < self.__lower_x: continue
              block_id = chunk.get_block(x_coord, y_coord, z_coord).id
              blocks[f"{global_x_coord}, {global_z_coord}, {y_coord}"] = block_id
              print(f"found {(global_x_coord, global_z_coord, y_coord)}")
              if block_id == "air":
                continue
              elif block_id in enumerated_blocks:
                enumerated_blocks[block_id] += 1
              else:
                enumerated_blocks[block_id] = 1
    
    self.blocks = blocks
    self.enumerated_blocks = {k: v for k, v in sorted(enumerated_blocks.items(), key=lambda item: item[1], reverse=True)}
  
  def scan_world(self):
    if self.blocks:
      print("blocks.json file already exists, are you sure you want to re-scan the world?")
      user_input = input("[Y/n] >> ").strip().lower()
      if "n" in user_input:
        exit()

    self.__validate_region_files()
    self.__parameterize()
    self.__scan_blocks()
    self.__write_json()
  
  def __check_hollow(self, block, x, z, y_offset):
    y = self.__lower_y + y_offset
    try:
      block_zenith = self.blocks[f"{x}, {z}, {y + 1}"]
      block_nadir = self.blocks[f"{x}, {z}, {y - 1}"]
      block_above = self.blocks[f"{x}, {z + 1}, {y}"]
      block_below = self.blocks[f"{x}, {z - 1}, {y}"]
      block_right = self.blocks[f"{x + 1}, {z}, {y}"]
      block_left = self.blocks[f"{x - 1}, {z}, {y}"]
    except KeyError:
      return block
    
    for adjacent_block in [block_zenith, block_nadir, block_above, block_below, block_right, block_left]:
      if adjacent_block in ["air", "water", "short_grass"]: return block
    
    return "air"


  def print_layer(self, y_offset, hollow_flag=False):
    if not self.blocks:
      raise FileNotFoundError("blocks.json not found. Please run the scan_world method before you run the print_layer method")
    filedir = os.path.abspath(os.path.dirname(__file__))
    if not os.path.exists(os.path.join(filedir, "textures", "block")):
      raise FileNotFoundError("Minecraft block textures directory required for the print_layer function")
    
    if (self.__lower_y + y_offset) > self.__upper_y:
      print(f"Input y_offset of {y_offset} exceeds the maximum y_value of {self.__upper_y}")
      return 0

    texturesf = os.listdir("textures/block")
    x_range = self.__upper_x - self.__lower_x
    z_range = self.__upper_z - self.__lower_z
    img = Image.new('RGBA', (x_range*16, z_range*16), "WHITE")

    enumerations = {}
    textures = {}
    for z in range(self.__lower_z, self.__upper_z + 1):
      for x in range(self.__lower_x, self.__upper_x + 1):
        try:
          block = self.blocks[f"{x}, {z}, {self.__lower_y + y_offset}"]
        except KeyError:
          raise KeyError(f"Invalid y_coordinate: {self.__lower_y + y_offset}")

        if hollow_flag:
          block = self.__check_hollow(block, x, z, y_offset)

        if f"{block}.png" in texturesf:
          if block not in textures:
            textures[block] = Image.open(f"textures/block/{block}.png")
            enumerations[block] = 1
          img.paste(textures[block], box=((x - self.__lower_x)*16, (z - self.__lower_z)*16))
          enumerations[block] += 1
        else:
          if block not in textures:
            textures[block] = None
            print(f"No texture found for {block}")

    #draw gridlines
    draw = ImageDraw.Draw(img)

    step_count = 32 #every 5 blocks
    y_start = 0
    y_end = img.height
    step_size = int(img.width / step_count)
    for x in range(0, img.width, step_size):
      line = ((x, y_start), (x, y_end))
      draw.line(line, fill=128, width=5)
    
    x_start = 0
    x_end = img.width
    for y in range(0, img.height, step_size):
      line = ((x_start, y), (x_end, y))
      draw.line(line, fill=128, width=5)
    
    step_count = 32 * 5#every 5 blocks
    y_start = 0
    y_end = img.height
    step_size = int(img.width / step_count)
    for x in range(0, img.width, step_size):
      line = ((x, y_start), (x, y_end))
      draw.line(line, fill=128)
    
    x_start = 0
    x_end = img.width
    for y in range(0, img.height, step_size):
      line = ((x_start, y), (x_end, y))
      draw.line(line, fill=128)
    
    enumerations = {k: v for k, v in sorted(enumerations.items(), key=lambda item: item[1], reverse=True)}
    img.show()

    self.layer_enumerations = enumerations

    return 1


if __name__ == "__main__":
  region_files = r"C:\Users\dalda\curseforge\minecraft\Instances\annual fabric\saves\Abandoned_City\region"
  kwargs = {"upper_x": 340, "lower_x": 180, "upper_z": 474, "lower_z": 323, "upper_y": 152, "lower_y": 108,
            "region_files": region_files}

  ws = WorldScanner(**kwargs)

  max_offset = kwargs["upper_y"] - kwargs["lower_y"]
  cur_layer = 0

  # for i in range(100):
  #   if not ws.print_layer(i, hollow_flag=False): break

  ws.print_layer(cur_layer, hollow_flag=True)

  if ws.layer_enumerations:
    layer_enumerations = ws.layer_enumerations

  print()

  #rotate each pic 3 times