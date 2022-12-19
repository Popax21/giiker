import asyncio, logging, typing, bleak, uuid
from . import log, cmd

class RWHandler:
    BLE_CHARACT_REQ = uuid.UUID("0000aaac-0000-1000-8000-00805f9b34fb")
    BLE_CHARACT_RESP = uuid.UUID("0000aaab-0000-1000-8000-00805f9b34fb")

    cube: 'CubeDevice'

    _rw_cmd_lock: asyncio.Lock
    _recv_queue: typing.Mapping[int, asyncio.Queue[asyncio.Future]]

    def __init__(self, cube: 'CubeDevice'):
        self.cube = cube

        #Setup receive queues
        self._rw_cmd_lock = asyncio.Lock()
        self._recv_queue = { cmd: asyncio.Queue() for cmd in cmd.CMDS }

    async def connect(self):
        #Register response characteristic callback
        await self.cube.ble_client.start_notify(RWHandler.BLE_CHARACT_RESP, self._resp_cb)

    async def send_rw_command(self, req : bytes) -> bytes:
        fut = asyncio.Future()
        async with self._rw_cmd_lock:
            cmd = req[0]
            log.LOGGER.log(logging.DEBUG, f"[{self.cube}] req  -> {req.hex()}")

            #Queue us for response handling, and send the request
            await self._recv_queue[cmd].put(fut)
            await self.cube.ble_client.write_gatt_char(RWHandler.BLE_CHARACT_REQ, req)

        return await fut

    async def _resp_cb(self, charact: bleak.BleakGATTCharacteristic, resp: bytes):
        async with self._rw_cmd_lock:
            cmd = resp[0]
            if cmd not in self._recv_queue:
                log.LOGGER.log(logging.DEBUG, f"[{self.cube}] Received unexpected response for command 0x{cmd:x}: {resp.hex()}")
                return

            if self._recv_queue[cmd].empty(): return

            #Complete the future
            log.LOGGER.log(logging.DEBUG, f"[{self.cube}] resp <- {resp.hex()}")
            fut : asyncio.Future[bytes] = await self._recv_queue[cmd].get()
            fut.set_result(resp)