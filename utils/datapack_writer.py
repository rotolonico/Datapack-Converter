import os
import shutil
import random

world_path = ""
datapack_name = ""
datapack_path = ""
functions_path = ""
chains = {}
all_commands = {}
all_blocks = {}
randomise = False
hide_warnings = False
dimension = ""

warnings_message = ""
any_warnings = False

merge_alternatives = [
    "data merge block {} {} {} {{auto:0b}}",
    "data merge block {} {} {} {{auto:1b}}",
    "data merge block {} {} {} {{auto:0}}",
    "data merge block {} {} {} {{auto:1}}",
    "data merge block {} {} {} {{auto:false}}",
    "data merge block {} {} {} {{auto:true}}",
]


def write_datapack(world_save_path, chains_to_convert, dp_name, force, delete_cmds, all_loaded_blocks, r,
                   s, d):
    global world_path
    global datapack_path
    global datapack_name
    global functions_path
    global chains
    global all_blocks
    global randomise
    global hide_warnings
    global dimension

    world_path = world_save_path
    datapacks_path = os.path.join(world_path, "datapacks")
    datapack_name = dp_name
    chains = chains_to_convert
    all_blocks = all_loaded_blocks
    randomise = r
    hide_warnings = s
    dimension = d

    if not os.path.exists(datapacks_path):
        os.makedirs(datapacks_path)

    datapack_path = os.path.join(datapacks_path, datapack_name)

    print_chains()

    if os.path.exists(datapack_path):
        if not force:
            print("\nERROR: Datapack named " + datapack_name + " already exists! Aborting.")
            exit(0)
        else:
            shutil.rmtree(datapack_path)

    shutil.copytree(os.path.join("utils", "converted_datapack"), datapack_path)

    functions_path = os.path.join(datapack_path, "data", datapack_name, "functions")

    if datapack_name != "converted_datapack":
        os.makedirs(os.path.join(datapack_path, "data", datapack_name))

        os.rename(os.path.join(datapack_path, "data", "converted_datapack"),
                  os.path.join(datapack_path, "data", datapack_name))

        load_path = os.path.join(datapack_path, "data", "minecraft", "tags", "functions", "load.json")
        tick_path = os.path.join(datapack_path, "data", "minecraft", "tags", "functions", "tick.json")

        replace_string_in_file(load_path, "converted_datapack", datapack_name)
        replace_string_in_file(tick_path, "converted_datapack", datapack_name)

        tick_function_path = os.path.join(functions_path, "tick.mcfunction")

        replace_string_in_file(tick_function_path, "converted_datapack", datapack_name)

    store_init_data()

    store_commands()

    call_commands()

    if delete_cmds:
        delete_command_blocks()

    if any_warnings:
        add_warnings()

    print("")
    print("Done! Open the world to finalise the conversion")
    print("If you missed the finalisation text in-game or need to see it again, you can run the following commands:")
    print("- /data remove storage dp_conv:init \"init\"")


def print_chains():
    if len(chains) == 0:
        print("No commands found! Make sure the coordinates inserted are correct.")
        exit(0)

    print("Writing datapack with the following chains at " + datapack_path)
    for chain in chains:
        print_chain(chains[chain])


def print_chain(chain):
    print("")
    if chain["has_name"]:
        print("- CHAIN " + chain["id"] + " (" + chain["display_name"] + ")")
    else:
        print("- CHAIN " + chain["id"])

    for c in chain["chain"]:
        command = chain["chain"][c]
        print(command["id"] + " | " + command["command"])


def store_init_data():
    initial_data_commands = "\n# Initial states of the command blocks (storing if they started out active/inactive, successful/unsuccessful)\n"

    # We go through every command and check if it was initially needs redstone or always active etc...
    # and add this data to the storage
    for chain in chains:
        commands = chains[chain]["chain"]
        for c in commands:
            command = commands[c]
            all_commands[c] = command
            initial_data_commands += 'data merge storage dp_conv:{} {{"{}_auto":{}}}\n'.format(datapack_name,
                                                                                               command["id"],
                                                                                               "1b" if command[
                                                                                                   "is_auto"] else "0b")
            if command["is_relied_on"]:
                initial_data_commands += 'data merge storage dp_conv:{} {{"{}_success":{}}}\n'.format(datapack_name,
                                                                                                      command["id"],
                                                                                                      "1b" if command[
                                                                                                          "is_success"] else "0b")
            if command["block_id"] == "command_block":
                initial_data_commands += 'data merge storage dp_conv:{} {{"{}_run":{}}}\n'.format(datapack_name,
                                                                                                  command["id"],
                                                                                                  "1b" if command[
                                                                                                      "is_auto"] else "0b")
    init_function = open(os.path.join(functions_path, "init.mcfunction"), 'a')
    init_function.write(initial_data_commands)


def store_commands():
    unique = set()
    for chain in chains:

        # If -r argument is set, randomise all chain names
        if randomise:
            chains[chain]["name"] = generate_random_unique_string(unique)

        commands = chains[chain]["chain"]
        new_function = open(os.path.join(functions_path, chains[chain]["name"] + ".mcfunction"), 'w')
        for c in commands:
            command = commands[c]
            new_command = command["command"]

            # Removing / since it's not allowed in datapacks
            new_command = new_command.strip("/")

            # If the commands are not in the overworld, we have to execute all the commands in their dimension
            if dimension != "overworld":
                new_command = "execute in minecraft:{} run {}".format(dimension, new_command)

            # Checking if the command is a 'data merge block x y z {auto:B} type
            # If it's the case we have to replace it with the storage command
            activates_command = False
            toggles_command = False
            possible_coords = []

            if " {auto:" in new_command:
                s = new_command.split('data merge block ')
                if len(s) >= 2:
                    s2 = s[1].split(" {auto:")
                    if len(s2) >= 2:
                        s3 = s2[0].split(" ")
                        if len(s3) == 3:
                            possible_coords = s3
                            toggles_command = True
                            if s2[1][0] == "t" or s2[1][0] == "1":
                                activates_command = True

            absolute_coords = []
            for c_index in range(len(possible_coords)):
                coord = possible_coords[c_index]
                if not coord.lstrip("-").isdigit():
                    if coord[0] == "~":
                        coord = coord.lstrip("~")
                        if len(coord) == 0:
                            coord = "0"

                        absolute_coords.append(str(int(c[c_index]) + int(coord)))
                    else:
                        toggles_command = False
                        break
                else:
                    absolute_coords.append(coord)

            if toggles_command:
                coords = (int(absolute_coords[0]), int(absolute_coords[1]), int(absolute_coords[2]))
                if coords in all_commands:
                    cmd_id = all_commands[coords]["id"]
                    function_name = "{}_{}".format("activate" if activates_command else "deactivate", cmd_id)
                    # If the command is already activated/deactivated, we have to make the command not succeed
                    # (that's why the unless clause is there)
                    command_to_replace = "execute unless data storage dp_conv:{} {{\"{}_auto\":{}}} run function {}:{}".format(
                        datapack_name, cmd_id, "1b" if activates_command else "0b", datapack_name, function_name)
                    for a in merge_alternatives:
                        new_command = new_command.replace(a.format(possible_coords[0], possible_coords[1],
                                                                   possible_coords[2]), command_to_replace)

                    with open(os.path.join(functions_path, function_name + ".mcfunction"), 'w') as f:
                        f.write('data merge storage dp_conv:{} {{"{}_auto":{}}}'.format(datapack_name,
                                                                                        cmd_id,
                                                                                        "1b" if activates_command else "0b"))
                        if activates_command:
                            f.write(
                                '\ndata merge storage dp_conv:{} {{"{}_success":"temp"}}'.format(datapack_name, cmd_id))
                            f.write(
                                '\ndata merge storage dp_conv:{} {{"{}_success":0b}}'.format(datapack_name, cmd_id))
                        else:
                            f.write('\ndata merge storage dp_conv:{} {{"{}_run":"temp"}}'.format(datapack_name,
                                                                                                 cmd_id))
                            f.write('\ndata merge storage dp_conv:{} {{"{}_run":{}}}'.format(datapack_name,
                                                                                             cmd_id,
                                                                                             "1b" if activates_command else "0b"))

            # The command has to be active before executing it
            new_command = "execute if data storage dp_conv:{} {{{}_auto:1b}} run {}".format(datapack_name,
                                                                                            command["id"], new_command)

            # If the command is conditional, make sure it only fires if the command it is 'conditioned by' has fired successfully
            if command["is_conditional"] and command["conditioned_by"] in all_commands:
                new_command = "execute if data storage dp_conv:{} {{{}_success:1b}} run {}".format(datapack_name,
                                                                                                   all_commands[command[
                                                                                                       "conditioned_by"]][
                                                                                                       "id"],
                                                                                                   new_command)

            # If the command conditions another command, it has to store its success in storage
            if command["is_relied_on"]:
                new_command = "execute store success storage dp_conv:{} {}_success byte 1 run {}".format(datapack_name,
                                                                                                         command["id"],
                                                                                                         new_command)

            command["command"] = new_command

            # Add comments to the commands if they have a name or a warning
            if not randomise and command["has_name"]:
                new_function.write("# " + command["display_name"] + "\n")
            if not hide_warnings and not toggles_command and check_warnings(new_command, chains[chain]["name"]):
                new_function.write("# !WARNING!\n")
            new_function.write(new_command + "\n")


def call_commands():
    call_commands_code = "\n# Calling commands\n"
    for c in chains:
        chain = chains[c]

        # The chain has to be active before calling it
        active_prefix = "execute if data storage dp_conv:{} {{{}_0_auto:1b}} run".format(datapack_name,
                                                                                         chain["id"])

        # If the command is repeating, call it every tick. If it's impulse, call it only when its run state is false
        # and set its run state to true as soon as it is run (it will be set back to false when it gets deactivated)
        if chain["is_repeating"]:
            call_commands_code += "{} function {}:{}\n".format(active_prefix, datapack_name, chain["name"])
        else:
            call_commands_code += "{} execute if data storage dp_conv:{} {{{}_0_run:0b}} run function {}:{}\n".format(
                active_prefix,
                datapack_name, chain["id"], datapack_name, chain["name"])
            call_commands_code += "{} data merge storage dp_conv:{} {{{}_0_run:1b}}\n".format(active_prefix,
                                                                                              datapack_name,
                                                                                              chain["id"])

    # We store the command success state so conditional commands know when to run.
    # Repeating commands will have their success state reset at the end of the tick
    # Commands also have their success state reset when they get activated
    for c in all_commands:
        cmd = all_commands[c]
        if "r" in cmd["id"]:
            active_prefix = "execute if data storage dp_conv:{} {{{}_auto:1b}} run".format(datapack_name,
                                                                                           cmd["id"])

            call_commands_code += "{} data merge storage dp_conv:{} {{{}_success:0b}}\n".format(active_prefix,
                                                                                                datapack_name,
                                                                                                cmd["id"])

    tick_function = open(os.path.join(functions_path, "tick.mcfunction"), 'a')
    tick_function.write(call_commands_code)


def delete_command_blocks():
    # We have to fill every command individually to air because the area might be too big to fill all at once
    delete_blocks_commands = "\n# Deleting command blocks (script was executed with -d argument)\n"
    for chain in chains:
        commands = chains[chain]["chain"]

        # If the command blocks are not in the overworld, we have to delete them in their dimension
        dimension_prefix = ""
        if dimension != "overworld":
            dimension_prefix = "execute in minecraft:{} run ".format(dimension)

        for c in commands:
            delete_blocks_commands += "{}fill {} {} {} {} {} {} air replace #signs\n".format(dimension_prefix, c[0] - 1,
                                                                                             c[1] - 1, c[2] - 1,
                                                                                             c[0] + 1, c[1] + 1,
                                                                                             c[2] + 1)
        for c in commands:
            delete_blocks_commands += "{}fill {} {} {} {} {} {} air replace {}\n".format(dimension_prefix, c[0] - 1,
                                                                                         c[1] - 1, c[2] - 1,
                                                                                         c[0] + 1, c[1] + 1, c[2] + 1,
                                                                                         commands[c]["block_id"])

    init_function = open(os.path.join(functions_path, "init.mcfunction"), 'a')
    init_function.write(delete_blocks_commands)


def replace_string_in_file(file_path, string, replacement):
    with open(file_path, 'r') as file:
        filedata = file.read()

    filedata = filedata.replace(string, replacement)

    with open(file_path, 'w') as file:
        file.write(filedata)


def check_warnings(command, chain_name):
    global warnings_message
    global any_warnings
    is_warning = False

    split_command = command.split(" ")

    # If there is relative positioning and no 'at', the position is relative to the command block, which is a potential
    # problem.
    if "at" not in split_command and "~" in command:
        is_warning = True
    else:
        # Also, if positioning is absolute, and it is included in the blocks loaded (all_blocks), some commands could
        # be affecting the command blocks themselves, which is also a problem
        for c in range(len(split_command) - 2):
            found_coords = True
            for i in range(3):
                if not split_command[c + i].lstrip("-").isdigit():
                    found_coords = False
                    break
            if found_coords:
                if (int(split_command[c]), int(split_command[c + 1]), int(split_command[c + 2])) in all_blocks:
                    is_warning = True
                    break
                c += 2

    if is_warning:
        any_warnings = True
        warnings_message += "- " + command + " in " + chain_name + "\n"
    return is_warning


def add_warnings():
    # Shows the warning message and adds the warnings to warning.txt
    warnings_load_prepend = '# Warnings triggered\ndata merge storage dp_conv:init {"warnings":1b}\n'
    with open(os.path.join(functions_path, "load.mcfunction"), 'r+') as file:
        content = file.read()
        file.seek(0)
        file.write(warnings_load_prepend + content)
    warnings_prepend = 'Warnings can also happen if the area selected includes part of the map that commands are legitimately affecting. \nThis tool can properly convert only commands modified using \"/data merge block X Y Z {auto:B}\". Any other way of triggering commands (redstone included) is not supported and should be patched manually.\n\nHere\'s a list of possible troublesome commands (they have been annotated with # !WARNING! in the datapack):\n\n'
    warnings_path = os.path.join(datapack_path, "warnings.txt")
    replace_string_in_file(os.path.join(functions_path, "init.mcfunction"), "PATH_PLACEHOLDER", warnings_path)
    with open(warnings_path, 'w') as f:
        f.write(warnings_prepend + warnings_message)


def generate_random_unique_string(unique):
    chars = "abcdefghijklmnopqrstuvwxyz1234567890"
    while True:
        value = "".join(random.choice(chars) for _ in range(10))
        if value not in unique:
            unique.add(value)
            return value
