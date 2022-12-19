import asyncio, aioconsole, logging, giiker, argparse, time
from view import CubeView

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
args = parser.parse_args()

if args.debug: giiker.LOGGER.setLevel(logging.DEBUG)

async def solve_timer(cube: giiker.CubeDevice):
    #Wait  for the cube to be scrambled
    while True:
        await aioconsole.ainput("Scramble the cube, then press enter")
        if not cube.move_handler.cur_state.is_solved: break

    #Start the timer
    start_time: float = None
    solved_time: float = None

    start_evt, solve_evt = asyncio.Event(), asyncio.Event()
    def move_cb(state: giiker.CubeState, move: giiker.Move):
        nonlocal start_time, solved_time

        #Handle start condition
        if not start_time:
            start_time = time.time()
            start_evt.set()

        #Handle solve condition
        if state.is_solved:
            solved_time = time.time()
            solve_evt.set()

    await cube.move_handler.register_handler(move_cb)
    try:
        #Wait for a move to be made
        print("Timer starts once a move is made", end=" "*10 + "\r")
        await start_evt.wait()

        #Wait for the cube to be solved
        print("Waiting for the cube to be solved..." + " "*10)
        while not solve_evt.is_set():
            #Print the current time
            t = time.time() - start_time
            print(f"Current time: {int(t / 60)}m {int(t % 60):02d}s {int((t * 1000) % 1000):03d}ms", end=" "*10 + "\r")

            await asyncio.sleep(0.053)
    finally: await cube.move_handler.unregister_handler(move_cb)

    #Output final time
    t = solved_time - start_time
    print(f"Solve time: {int(t / 60)}m {int(t % 60):02d}s {int((t * 1000) % 1000):03d}ms" + " "*10)

async def command_loop(cube: giiker.CubeDevice):
    #Main command loop
    view : CubeView = None
    try:
        while True:
            cmd = (await aioconsole.ainput("> ")).strip().lower()
            if cmd == "h" or cmd == "help":
                print("(h)elp:  Shows this help text")
                print("(q)uit:  Exits the demo")
                print("(i)nfo:  Shows information about the connected cube")
                print("(m)oves: Shows moves being made in real time")
                print("(v)iew:  Opens a 3D view of the cube which updates in real time")
                print("(t)imer: Starts a timer for measuring the time it takes to solve the cube")
                print("(d)ebug: Toggles debug logging")
            elif cmd == "q" or cmd == "quit":
                print("Exiting...")
                break
            elif cmd == "i" or cmd == "info":
                print(f"FW ver:     {cube.fw_ver}")
                print(f"data ver:   {cube.data_ver}")
                print(f"cube type:  {cube.cube_type}")
                print(f"color type: {cube.color_type}")
                print(f"SW ver:     {(await cube.query_sw_ver()):02x}")
                print(f"UID:        {(await cube.query_uid()).hex()}")
                print(f"battery:    {await cube.query_battery()}")
                print(f"#moves:     {await cube.query_num_moves()}")
            elif cmd == "m" or cmd == "moves":
                def move_cb(state: giiker.CubeState, move: giiker.Move):
                    print(f"MOVE | {state} | {move}")

                await cube.move_handler.register_handler(move_cb)
                await aioconsole.ainput("Press ENTER to stop\n")
                await cube.move_handler.unregister_handler(move_cb)
            elif cmd == "v" or cmd == "view":
                if not view or view.has_exit:
                    def view_move_cb(state: giiker.CubeState, move: giiker.Move):
                        if view: view.cube.update_state(state, move)
                    await cube.move_handler.register_handler(view_move_cb)

                    view, _ = await CubeView.run_thread(lambda: asyncio.ensure_future(cube.move_handler.unregister_handler(view_move_cb)))
                    view.cube.update_state(cube.move_handler.cur_state, None)
            elif cmd == "t" or cmd == "timer":
                await solve_timer(cube)
            elif cmd == "d" or cmd == "debug":
                if giiker.LOGGER.level != logging.DEBUG:
                    giiker.LOGGER.setLevel(logging.DEBUG)
                    print("Enabled debug logging")
                else:
                    giiker.LOGGER.setLevel(logging.INFO)
                    print("Disabled debug logging")
            else: print("Unknown command")
    finally:
        if view: view.close_threadsafe()

async def main():
    #Scan for a cube
    print("Scanning for cube...")
    cube = await giiker.scan_for_cube()
    print(f"Found cube: {cube}")

    #Connect to the cube
    await cube.connect()
    try:
        #Print cube info
        print("Connected to cube:")
        print(f"    FW ver:     {cube.fw_ver}")
        print(f"    data ver:   {cube.data_ver}")
        print(f"    cube type:  {cube.cube_type}")
        print(f"    color type: {cube.color_type}")
        print(f"    SW ver:     {(await cube.query_sw_ver()):02x}")
        print(f"    UID:        {(await cube.query_uid()).hex()}")
        print(f"    battery:    {await cube.query_battery()}")
        print(f"    #moves:     {await cube.query_num_moves()}")

        if cube.cube_type != 3:
            print("Non-3x3 cubes are not supported at the moment")
            return

        await command_loop(cube)
    finally:
        #Disconnect from the cube
        await cube.disconnect()

asyncio.run(main())