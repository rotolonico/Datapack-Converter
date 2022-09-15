import anvil
import math
import os


def get_blocks_from_coordinates(world_path, min_x, min_y, min_z, max_x, max_y, max_z):
    chunk_ids = _get_chunk_ids_from_coordinates(min_x, max_x, min_z, max_z)
    chunks = _get_chunks(chunk_ids, world_path)
    blocks = _get_blocks(chunks, min_x, min_y, min_z, max_x, max_y, max_z)
    return blocks


def _get_chunk_ids_from_coordinates(min_x, max_x, min_z, max_z):
    chunks = []
    min_c = _get_chunk_id_from_coordinate(min_x, min_z)
    max_c = _get_chunk_id_from_coordinate(max_x, max_z)

    for x in range(max_c[0] - min_c[0] + 1):
        for z in range(max_c[1] - min_c[1] + 1):
            chunks.append((min_c[0] + x, min_c[1] + z))

    return chunks


def _get_chunk_id_from_coordinate(x, z):
    return math.floor(x / 16), math.floor(z / 16)


def _get_region_id_from_chunk_id(c):
    return "r." + str(c[0] >> 5) + "." + str(c[1] >> 5) + ".mca"


def _get_chunks(chunk_ids, world_path):
    chunks = {}
    for chunk_id in chunk_ids:
        try:
            chunks[chunk_id] = _get_chunk(chunk_id, world_path)
        except Exception as e:
            print("Something went wrong loading chunk " + str(chunk_id) + ": " + str(e))
            chunks[chunk_id] = None

    return chunks


def _get_chunk(chunk_id, world_path):
    return anvil.Chunk.from_region(
        os.path.join(os.path.join(world_path, "region"), _get_region_id_from_chunk_id(chunk_id)), chunk_id[0],
        chunk_id[1])


def _get_blocks(chunks, min_x, min_y, min_z, max_x, max_y, max_z):
    blocks = {}
    total_blocks = (max_x - min_x + 1) * (max_y - min_y + 1) * (max_z - min_z + 1)

    for x in range(max_x - min_x + 1):
        for y in range(max_y - min_y + 1):
            for z in range(max_z - min_z + 1):
                print("Loading blocks " + str(len(blocks)).zfill(len(str(total_blocks))) + "/" + str(total_blocks), end='\r')

                current_x = min_x + x
                current_y = min_y + y
                current_z = min_z + z

                blocks[(current_x, current_y, current_z)] = _get_block(
                    chunks[_get_chunk_id_from_coordinate(current_x, current_z)], current_x,
                    current_y, current_z)

    return blocks


def _get_block(chunk, x, y, z):
    if chunk is None:
        return None
    block = chunk.get_block(x % 16, y, z % 16)
    nbt = chunk.get_tile_entity(x, y, z)
    return {
        "id": block.id,
        "properties": block.properties,
        "nbt": nbt,
        "xyz": (x,y,z)
    }
