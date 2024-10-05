import json
import threading
from datetime import datetime
from typing import Any, List

# from controller.controller_device import ControllerDevice
from database.actions import switch_device

from helpers.data_models import Device

from services.scheduled_device import get_scheduled_device_status
from services.socket import SocketEvents, SocketManager


def set_interval(func, sec):
    def wrapper():
        set_interval(func, sec)  # Schedule the next call
        func()  # Call the function

    t = threading.Timer(sec, wrapper)
    t.start()
    return t


class ScheduleDeviceAssistant():

    scheduled_devices: List[Device] = []
    controller_device: Any
    socket_manager: SocketManager

    timer: threading.Timer | None = None

    def __init__(self, controller_device: Any, socket_manager: SocketManager):
        scheduled_devices = controller_device.get_scheduled_devices()
        scheduled_devices = scheduled_devices if scheduled_devices is not None else []
        self.scheduled_devices = scheduled_devices
        self.controller_device = controller_device
        self.socket_manager = socket_manager

    def start_scheduled_devices_watch(self):
        if self.timer is not None:
            self.timer.cancel()
        self.timer = set_interval(self.switch_scheduled_devices, 60)

    async def switch_scheduled_devices(self):
        today = datetime.now().strftime("%a")
        for device in self.scheduled_devices:
            if today.lower() in device.days_scheduled.lower() if device.days_scheduled is not None else "":
                is_on = get_scheduled_device_status(
                    device.start_time if device.start_time is not None else "", device.off_time if device.off_time is not None else "")
                if is_on != device.status:
                    device.status = is_on
                    try:
                        self.controller_device.switch_device(
                            device.device_id, is_on)
                        broadcast_data = {
                            "event": SocketEvents.SCHEDULED_SWITCH_DEVICE,
                            "user_id": f"{device.scheduled_by}|-|Schedule Assistant",
                            "message": f"Schedule Assistant turned {'on' if is_on else 'off'} {device.device_name}.",
                            "data": {"deviceId": device.device_id, "state": is_on}
                        }
                        await self.socket_manager.broadcast(json.dumps(broadcast_data))
                        switch_device(device.device_id, device.status, is_on,
                                      f"{device.scheduled_by}|-|Schedule Assistant")
                    except Exception as e:
                        print(
                            f"[Schedule Assistant] : Switch scheduled device failed. {e}")

    def schedule_device(self, device: Device):
        self.remove_scheduled_device(device.device_id)
        self.scheduled_devices.append(device)
        self.start_scheduled_devices_watch()

    def get_scheduled_device(self, device_id: str):
        for device in self.scheduled_devices:
            if device.device_id == device_id:
                return device

    def remove_scheduled_device(self, device_id: str):
        device = self.get_scheduled_device(device_id)
        if device is not None:
            self.scheduled_devices.remove(device)
            self.start_scheduled_devices_watch()
