import asyncio, logging, typing, bleak, uuid, enum, dataclasses, struct
from . import log, cmd, rw_handler, move_handler

@dataclasses.dataclass
class BatteryInfo:
    class ChargeState(enum.Enum):
        NOT_CHARGING = 0x03
        CHARGING = 0x02
        FULLY_CHARGED = 0x01

    level: int
    charge_state: ChargeState

    def __str__(self): return f"{self.level}% {self.charge_state.name}"

class CubeDevice:
    BLE_NAME_PREFIXES = ["Gi", "Hi-G-12DRL" "Hi-G-123XE"]

    ble_device: bleak.BLEDevice
    ble_client: bleak.BleakClient

    rw_handler: rw_handler.RWHandler
    move_handler: move_handler.MoveHandler

    fw_ver: int
    data_ver: int
    cube_type: int
    color_type: int

    def __init__(self, dev: bleak.BLEDevice, ad_data: bleak.AdvertisementData):
        self.ble_device = dev
        self.ble_client = None

        #Create handlers
        self.rw_handler = rw_handler.RWHandler(self)
        self.move_handler = move_handler.MoveHandler(self)

        #Parse the advertisement data
        self.fw_ver = 0
        self.data_ver = -1
        self.cube_type = 3
        self.color_type = 1

        if dev.name.startswith("Gi") and len(ad_data.manufacturer_data) >= 12:
            self.data_ver = int(ad_data.manufacturer_data[8])
            if self.data_ver == 0 or self.data_ver == 2:
                self.fw_ver = int(ad_data.manufacturer_data[9])
                self.cube_type = int(ad_data.manufacturer_data[10])
                self.color_type = int(ad_data.manufacturer_data[11])
        elif dev.name.startswith("Hi-G-12DRL"):
            self.data_ver = 0
            self.color_type = 2
        elif dev.name.startswith("Hi-G-123XE"):
            self.data_ver = 0
            self.cube_type = 2
            self.color_type = 1

    async def connect(self):
        if self.ble_client != None: return

        #Create a client and connect to it
        self.ble_client = bleak.BleakClient(self.ble_device, self._on_disconnect, timeout=25.0)
        await self.ble_client.connect()

        #Connect handlers
        await self.rw_handler.connect()
        await self.move_handler.connect()

        log.LOGGER.log(logging.INFO, f"Connected to GiiKER cube {self}")

    async def disconnect(self):
        if self.ble_client == None: return

        #Disconnect the client
        await self.ble_client.disconnect()

    def _on_disconnect(self, client):
        if not self.ble_client: return
        self.ble_client = None

        log.LOGGER.log(logging.INFO, f"Disconnected from GiiKER cube {self}")

    async def query_uid(self) -> bytes:
        uid = (await self.rw_handler.send_rw_command(bytes([cmd.CMD_GET_UID])))[1:7]
        log.LOGGER.log(logging.DEBUG, f"[{self}] UID: {uid.hex()}")
        return uid

    async def query_sw_ver(self) -> int:
        sw_ver = (await self.rw_handler.send_rw_command(bytes([cmd.CMD_GET_SOFTWARE_VERSION])))[1]
        log.LOGGER.log(logging.DEBUG, f"[{self}] SW ver: {sw_ver:02x}")
        return sw_ver

    async def query_battery(self) -> BatteryInfo:
        resp = await self.rw_handler.send_rw_command(bytes([cmd.CMD_GET_BATTERY]))
        level, charge_state = resp[1], BatteryInfo.ChargeState(resp[2])

        #Clamp the battery level
        if charge_state == BatteryInfo.ChargeState.NOT_CHARGING: level = min(level, 100)
        elif charge_state == BatteryInfo.ChargeState.CHARGING: level = min(level, 99)
        elif charge_state == BatteryInfo.ChargeState.FULLY_CHARGED: level = 100

        info = BatteryInfo(level, charge_state)
        log.LOGGER.log(logging.DEBUG, f"[{self}] battery: {info}")
        return info

    async def query_num_moves(self) -> int:
        steps = struct.unpack(">I", (await self.rw_handler.send_rw_command(bytes([cmd.CMD_GET_ALL_STEP])))[1:5])[0]
        log.LOGGER.log(logging.DEBUG, f"[{self}] #moves: {steps}")
        return steps

    def __str__(self): return str(self.ble_device)
