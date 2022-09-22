# Datapack-Converter

Convert Minecraft command block chains to a datapack!

## Installation

- Clone/Download the repo
- Open a command line at the folder
- Run `pip3 install -r requirements.txt`
- You are all set!

## How to use

- Run `python3 datapack_converter.py "world_path" x1 y1 z1 x2 y2 z2`

- Positional arguments:
    - **world_path:** Path of the Minecraft world
    - **x1:** X coordinate of the first corner of the area to convert
    - **y1:** Y coordinate of the first corner of the area to convert
    - **z1:** Z coordinate of the first corner of the area to convert
    - **x2:** X coordinate of the second corner of the area to convert
    - **y2:** Y coordinate of the second corner of the area to convert
    - **z2:** Z coordinate of the second corner of the area to convert
- Optional arguments:
    - **-h, --help:** show this help message and exit
    - **-n N, -name N:** Datapack name. 'converted_datapack' by default
    - **-f, -force:** Overwrite existing datapack with the same name. False by default
    - **-d, -delete-commands:**  Automatically delete the command blocks converted from the world. False by default
    - **-r, -randomize-functions:** Assign a random name to all functions generated and remove comments
    - **-dim, -dimension:** The dimension the area to convert is in. Possible values are 'overworld', 'the_nether' or '
      the_end'. Overworld by default
    - **-se, -strip-execute:** Removes all 'run execute' syntax from the datapack to increase readability. 'execute A
      run execute B run C' becomes 'execute A B run C'. False by default

## How it works

- Blocks selected are loaded in from regions using
  the [anvil-new Python library](https://github.com/Intergalactyc/anvil-new)
- For every impulse or repeating command block, it iteratively finds the entire chain
- For every command block, it checks if there's a sign attached to it and, if that is the case, it makes that become the
  function name (or a function comment, if it's a chain command)
- Auto/Conditional properties are handled by storing each command success and active state into storage
- The converter can only handle activating chains using the syntax `data merge block X Y Z {auto:B}`. Any other syntax (
  like, at example, setting a redstone block or modifying the conditional state of commands) is not supported.
- The converter will throw warnings if it detects that command blocks are dynamically altering the area selected (and
  not using the `data merge block` syntax) as this could lead to unexpected behaviour (like, at example, setting a
  command block to air), which is not supported.

## Watch it in action

Check out [this video](https://youtu.be/249syz1gths) that showcases the tool by converting a few unfair maps and better
explains how it works!

## Thanks

- Thanks to matcool for the [original anvil-parser library](https://github.com/matcool/anvil-parser) for loading
  Minecraft regions in Python
- Thanks to Intergalactyc for [updating the library](https://github.com/Intergalactyc/anvil-new) for Minecraft 1.18+ 

## Looking for the opposite conversion?
Check out the [Commands-Converter](https://github.com/rotolonico/Commands-Converter)