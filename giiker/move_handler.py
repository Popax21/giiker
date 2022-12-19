import asyncio, logging, typing, bleak, uuid, enum, math
from . import log, state

class Move(enum.Enum):
    Fr = 0x23
    F = 0x21
    Br = 0x43
    B = 0x41
    Rr = 0x33
    R = 0x31
    Lr = 0x53
    L = 0x51
    Dr = 0x63
    D = 0x61
    Ur = 0x13
    U = 0x11
    F2 = 0x29
    Fr2 = 0x28
    B2 = 0x49
    Br2 = 0x48
    U2 = 0x19
    Ur2 = 0x18
    D2 = 0x69
    Dr2 = 0x68
    L2 = 0x59
    Lr2 = 0x58
    R2 = 0x39
    Rr2 = 0x38

    @property
    def face(self) -> state.Face: return state.Face[self.name[0:1]]
    @property
    def is_ccw(self) -> bool: return 'r' in self.name
    @property
    def is_double_rot(self) -> bool: return '2' in self.name

    @property
    def angle(self) -> float: return (-1 if self.is_ccw else +1) * (2 if self.is_double_rot else 1) * math.pi / 2

    @property
    def rot_matrix(self) -> typing.List[typing.List[int]]:
        dx, dy, dz = self.face.direction
        s = -1 if (self.is_ccw ^ (dx < 0 or dy < 0 or dz < 0)) else +1
        if dx != 0:
            return [
                [ 1,  0,  0],
                [ 0,  0, -s],
                [ 0, +s,  0]
            ]
        elif dy != 0:
            return [
                [ 0,  0, +s],
                [ 0,  1,  0],
                [ -s, 0,  0]
            ]
        elif dz != 0:
            return [
                [ 0, -s,  0],
                [ +s, 0,  0],
                [ 0,  0,  1]
            ]
        else: assert False

    def __str__(self): return self.name.replace('r', '\'')

class MoveHandler:
    BLE_CHARACT = uuid.UUID("0000aadc-0000-1000-8000-00805f9b34fb")

    cube: 'CubeDevice'
    cur_state: state.CubeState

    _lock: asyncio.Lock()
    _handlers: typing.List[typing.Callable[[state.CubeState, Move], None]]

    def __init__(self, cube: 'CubeDevice'):
        self.cube = cube
        self.cur_state = None

        self._lock = asyncio.Lock()
        self._handlers = []

    async def connect(self):
        #Register move callback
        state_evt = asyncio.Event()
        def move_cb(st, mv): state_evt.set()
        await self.register_handler(move_cb)

        #Register characteristic callback
        await self.cube.ble_client.start_notify(MoveHandler.BLE_CHARACT, self._recv_cb)

        #Wait for first state update
        await state_evt.wait()
        await self.unregister_handler(move_cb)

    async def register_handler(self, cb: typing.Callable[[state.CubeState, Move], None]):
        async with self._lock: self._handlers.append(cb)

    async def unregister_handler(self, cb: typing.Callable[[state.CubeState, Move], None]):
        async with self._lock: self._handlers.remove(cb)

    async def _recv_cb(self, charact: bleak.BleakGATTCharacteristic, resp: bytes):
        #Decode cube state
        st = state.CubeState.decode_state(resp[0:16])
        move = Move(resp[16])
        log.LOGGER.log(logging.DEBUG, f"[{self.cube}] move | {resp.hex()} {move:3s} -> {st}")

        #Invoke handlers
        async with self._lock: 
            self.cur_state = st
            for h in self._handlers: h(st, move)