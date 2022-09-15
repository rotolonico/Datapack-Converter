from utils.world_loader import get_blocks_from_coordinates
from utils.datapack_writer import write_datapack

import re
from enum import Enum
import json
import argparse


class facings(Enum):
    east = 'east',
    south = 'south',
    west = 'west',
    north = 'north',
    up = 'up',
    down = 'down'


all_blocks = {}
chains = {}


def get_block_facing(block):
    return facings[block["properties"]["facing"].value]


def get_opposite_block_facing(block):
    f = get_block_facing(block)
    if f == facings.east:
        return facings.west
    if f == facings.west:
        return facings.east
    if f == facings.north:
        return facings.south
    if f == facings.south:
        return facings.north
    if f == facings.up:
        return facings.down
    if f == facings.down:
        return facings.up


def is_command_block_auto(block):
    return "1" in str(block["nbt"]["auto"])


def is_command_block_conditional(block):
    return str(block["properties"]["conditional"].value) == "true"


def find_command_name(block, fallback_name):
    for f in facings:
        if f == 'up' or f == 'down':
            continue

        possible_sign = get_next_block_from_facing(block, f)
        if "wall_sign" not in possible_sign["id"] or get_block_facing(possible_sign) != f:
            continue
        return get_text_from_sign(possible_sign)

    possible_sign = get_next_block_from_facing(block, facings.up)
    if "sign" not in possible_sign["id"] or "wall_sign" in possible_sign["id"]:
        return str(fallback_name)
    return get_text_from_sign(possible_sign)


def is_command_block_relied_on(block):
    for f in facings:
        possible_conditional = get_next_block_from_facing(block, f)
        if is_command_block(possible_conditional) and is_command_block_conditional(
                possible_conditional) and get_block_facing(possible_conditional) == f:
            return True
    return False


def command_block_conditioner(block):
    if not is_command_block_conditional(block):
        return ""

    conditioner = get_previous_block(block)
    if not is_command_block(conditioner):
        return ""
    return conditioner["xyz"]


def command_block_successful(block):
    return block["nbt"]["SuccessCount"].value > 0


def get_text_from_sign(sign):
    text = ""
    for t in range(1, 5):
        line = str(json.loads(str(sign["nbt"]["Text" + str(t)]))["text"])
        if line == "":
            continue
        text += " " + line

    return text.strip()


def find_chains(blocks):
    global all_blocks

    all_blocks = blocks
    iCount = 0
    rCount = 0
    for b in blocks:
        block = blocks[b]
        if block is None:
            continue
        if block["id"] == "command_block":
            chain_id = "i" + str(iCount)
            chain = find_chain_from_block(block, chain_id)

            if chain[block["xyz"]]["has_name"]:
                name = check_for_blacklisted_words(chain[block["xyz"]]["name"].lower(), chain_id)
                display_name = chain[block["xyz"]]["display_name"]
            else:
                name = chain_id
                display_name = chain_id

            chains[len(chains)] = {
                "id": chain_id,
                "name": name,
                "display_name": display_name,
                "has_name": chain_id != name,
                "chain": chain,
                "is_repeating": False
            }
            iCount += 1

        if block["id"] == "repeating_command_block":
            chain_id = "r" + str(rCount)
            chain = find_chain_from_block(block, chain_id)

            if chain[block["xyz"]]["has_name"]:
                name = check_for_blacklisted_words(chain[block["xyz"]]["name"].lower(), chain_id)
                display_name = chain[block["xyz"]]["display_name"]
            else:
                name = chain_id
                display_name = chain_id

            chains[len(chains)] = {
                "id": chain_id,
                "name": name,
                "display_name": display_name,
                "has_name": chain_id != name,
                "chain": chain,
                "is_repeating": True
            }
            rCount += 1

    write_datapack(args.world_path, chains, "map_name" if args.n is None else args.n, args.f, args.d, all_blocks,
                   args.r, args.s)


# Find a chain from the initial block by checking nearby chain blocks with the correct facing
def find_chain_from_block(initial_block, chain_id):
    chain = {}
    current_block = initial_block

    while True:
        command_id = chain_id + "_" + str(len(chain))
        name = find_command_name(current_block, command_id)
        chain[current_block["xyz"]] = {
            "id": command_id,
            "name": name.replace(" ", "_"),
            "display_name": name,
            "has_name": name != command_id,
            "command": current_block["nbt"]["Command"].value,
            "is_auto": is_command_block_auto(current_block),
            # if a conditional command relies on this command
            "is_relied_on": is_command_block_relied_on(current_block),
            "is_conditional": is_command_block_conditional(current_block),
            "conditioned_by": command_block_conditioner(current_block),
            "is_success": command_block_successful(current_block),
            "block_id": current_block["id"]
        }

        current_block = get_next_block(current_block)

        if not is_chain_command_block(current_block) or current_block["xyz"] in chain:
            break

    return chain


def get_previous_block(block):
    return get_next_block_from_facing(block, get_opposite_block_facing(block))


def get_next_block(block):
    return get_next_block_from_facing(block, get_block_facing(block))


def get_next_block_from_facing(block, facing):
    try:
        return all_blocks[
            sum_coordinates(block["xyz"], get_orientation_from_facing(facing))]
    except Exception as e:
        print("WARNING: " + str(e))
        return {
            "id": "air"
        }


def sum_coordinates(c1, c2):
    return tuple(map(sum, zip(c1, c2)))


def get_orientation_from_facing(facing):
    if facing == facings.east:
        return 1, 0, 0
    if facing == facings.west:
        return -1, 0, 0
    if facing == facings.north:
        return 0, 0, -1
    if facing == facings.south:
        return 0, 0, 1
    if facing == facings.up:
        return 0, 1, 0
    if facing == facings.down:
        return 0, -1, 0
    return 0, 0, 0


def is_command_block(block):
    return block is not None and (block["id"] == "command_block" or block["id"] == "repeating_command_block" or block[
        "id"] == "chain_command_block")


def is_chain_command_block(block):
    return block is not None and block["id"] == "chain_command_block"


def is_non_chain_command_block(block):
    return block is not None and (block["id"] == "command_block" or block["id"] == "repeating_command_block")


def check_for_blacklisted_words(name, fallback_name):
    if name == "init" or name == "tick" or name == "load":
        return fallback_name
    if "activate_" in name or "deactivate_" in name:
        return fallback_name
    if not re.match("^[a-z0-9._-]+$", name):
        return fallback_name

    return name


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts command blocks in a Minecraft world into a datapack')

    parser.add_argument('world_path', metavar='world_path', type=str,
                        help='Path of the Minecraft world')
    parser.add_argument('x1', metavar='x1', type=int, help='X coordinate of the first corner of the area to convert')
    parser.add_argument('y1', metavar='y1', type=int, help='Y coordinate of the first corner of the area to convert')
    parser.add_argument('z1', metavar='z1', type=int, help='Z coordinate of the first corner of the area to convert')
    parser.add_argument('x2', metavar='x2', type=int, help='X coordinate of the second corner of the area to convert')
    parser.add_argument('y2', metavar='y2', type=int, help='Y coordinate of the second corner of the area to convert')
    parser.add_argument('z2', metavar='z2', type=int, help='Z coordinate of the second corner of the area to convert')

    parser.add_argument('-n', '-name', type=str,
                        help='Datapack name. \'converted_datapack\' by default')
    parser.add_argument('-f', '-force', action='store_true',
                        help='Overwrite existing datapack with the same name. False by default')
    parser.add_argument('-d', '-delete-commands', action='store_true',
                        help='Automatically delete the command blocks converted from the world. False by default')
    parser.add_argument('-r', '-randomize-functions', action='store_true',
                        help='Assign a random name to all functions generated and remove comments')
    parser.add_argument('-s', '-silent-warnings', action='store_true',
                        help='Hide warnings')

    args = parser.parse_args()

    if args.n is not None and not re.match("^[a-z0-9._-]+$", args.n):
        print("Datapack name is invalid. Only a-z 0-9 ._- characters are allowed!")
        exit(0)

    min_x = min(args.x1, args.x2)
    min_y = min(args.y1, args.y2)
    min_z = min(args.z1, args.z2)
    max_x = max(args.x1, args.x2)
    max_y = max(args.y1, args.y2)
    max_z = max(args.z1, args.z2)

    blocks = get_blocks_from_coordinates(args.world_path, min_x, min_y, min_z, max_x, max_y, max_z)
    find_chains(blocks)
