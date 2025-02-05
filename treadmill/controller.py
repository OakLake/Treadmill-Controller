import asyncio

# OpCodes
SPEED_OP_CODE = 0x02
START_OP_CODE = 0x07
STOP_PAUSE_OP_CODE = 0x08


STOP_HEX = 0x01
PAUSE_HEX = 0x02


class TreadmillController:

    def __init__(self, client, control_point_uuid: str, data_point_uuid: str):
        self.client = client
        self.control_point_uuid = control_point_uuid
        self.data_point_uuid = data_point_uuid
        self.stop_event = asyncio.Event()

    async def _write_command(self, command):
        try:
            response = await self.client.write_gatt_char(
                self.control_point_uuid, command, response=True
            )
            print(
                f"Written command '{command.hex}' to treadmill. Response: '{response}'"
            )
        except Exception:
            print(f"FAILED to write command '{command}'")

    async def start(self):
        command = bytearray([START_OP_CODE])
        self._write_command(command)

    async def pause(self):
        command = bytearray([STOP_PAUSE_OP_CODE, PAUSE_HEX])
        self._write_command(command)

    async def stop(self):
        command = bytearray([STOP_PAUSE_OP_CODE, STOP_HEX])
        self.stop_event.set()
        self._write_command(command)

    async def set_speed(self, speed_mps: float):
        speed_bytes = int(speed_mps * 100).to_bytes(2, byteorder="little")
        command = bytearray([SPEED_OP_CODE]) + speed_bytes
        self._write_command(command)

    @staticmethod
    async def _notification_handler(_, data: bytearray):
        metrics = {
            "speed": int.from_bytes(data[2:4], "little") / 100,
            "distance_m": int.from_bytes(data[4:11], "little"),
            "calories": int.from_bytes(data[11:13], "little"),
            "time_s": int.from_bytes(data[17:19], "little"),
        }

        metrics = ", ".join([f"{name}: {value}" for name, value in metrics.items()])
        print(metrics)

    async def subscribe(self):
        await self.client.start_notify(self.data_point_uuid, self._notification_handler)
        print("Subscribed to notifications.")

        try:
            while not self.stop_event.is_set() and await self.client.is_connected():
                await asyncio.sleep(1)
        finally:
            await self.client.stop_notify(self.data_point_uuid)
            print("Stopped subscription.")


if __name__ == "__main__":
    from bleak import BleakClient

    treadmill_address = ""
    data_point_uuid = "00002acd-0000-1000-8000-00805f9b34fb"
    control_point_uuid = "00002ad9-0000-1000-8000-00805f9b34fb"

    async def main():
        async with BleakClient(treadmill_address) as client:
            controller = TreadmillController(
                client, control_point_uuid, data_point_uuid
            )
            await asyncio.gather(controller.subscribe(), controller.start())

    asyncio.run(main())
