# GiiKER SUPERCUBE Library
A simple python library to interact with the BLE (Bluetooth Low Energy) interface of GiiKER SUPERCUBE smart rubiks cubes.
It was created by reverse engineerning the GiiKER SUPERCUBE Android app (to be precise, the Lua code contained inside the Unity assets which are part of the APK).

## Features
- Cube discovery (see `scan.py`)
- Cube info (battery / firmware version / number of total moves / ...)
- State decoding (position and rotation of each individual cubelet, see `state.py`)
- Real time move callbacks (called when a move is made on the rubiks cube, see `move_handler.py`)

## Demo Script
The repository ships with a demo script, which provides a CLI interface to interact with a GiiKER SUPERCUBE.
Ensure that your cube is within range of connectivity, and that it is disconnected before executing the script.

The following commands are available (the first letter of each command can be used instead of typing out the full command):
- `help`: Outputs a list of available commands
- `quit`: Exits the demo, disconnecting the cube
- `info`: Outputs information about the cube, like the current battery level, number of total moves made, firmware version, etc
- `moves`: Outputs moves as they're made in real time
- `view`: Opens a live, 3D view of the cube, made using pyglet (use number keys to reorient the cube)
- `timer`: Allows to measure the time it takes to solve the cube
- `debug`: Toggles debug logging

## TODO
- Firmware Update mechanism (if one exists)
- On-Cube timer/counter