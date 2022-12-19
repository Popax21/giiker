import asyncio, logging, typing, bleak, uuid
from . import log
from .cube import CubeDevice

def scan_for_cube_devices(cube_discover_cb: typing.Callable[[CubeDevice], typing.Optional[typing.Awaitable[None]]]) -> bleak.BleakScanner:
    cubeAddrs = set()
    cubeLock = asyncio.Lock()

    async def ble_discover_cb(dev: bleak.BLEDevice, ad_data: bleak.AdvertisementData):
        async with cubeLock:
            #Check if the cube address is known
            if dev.address in cubeAddrs: return

            #Check if the device is a GiiKER cube
            if not any(str(dev.name).startswith(p) for p in CubeDevice.BLE_NAME_PREFIXES): return

            #Create a new cube device and pass it to the discover callback
            cube = CubeDevice(dev, ad_data)
            cubeAddrs.add(dev.address)
            task = cube_discover_cb(cube)
            if task: await task

    #Create a new BLE scanner
    return bleak.BleakScanner(ble_discover_cb)

async def scan_for_cube() -> CubeDevice:
    #Create a scanner
    foundCube = None
    foundCubeEvt = asyncio.Event()

    def discover_cb(cube: CubeDevice):
        nonlocal foundCube
        log.LOGGER.log(logging.INFO, f"Discovered GiiKER cube {cube}")
        foundCube = cube
        foundCubeEvt.set()

    scanner = scan_for_cube_devices(discover_cb)

    #Run the scan until we discover a cube
    async with scanner: await foundCubeEvt.wait()

    return foundCube