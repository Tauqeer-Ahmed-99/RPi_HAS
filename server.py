from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from sqlalchemy.exc import SQLAlchemyError

from controller.controller_device import ControllerDevice

from database.actions import add_user, get_user, get_access, create_room, remove_room, create_device, switch_device, configure_device, remove_device, get_house_data

from helpers.request_models import is_valid_request, AddRoomRequest, RemoveRoomRequest, AddDeviceRequest, SwitchDeviceRequest, ConfigureDeviceRequest, RemoveDeviceRequest, ResponseStatusCodes

from services.sys_init import SystemInitializer
from services.schedule import ScheduleDeviceAssistant
from services.scheduled_device import get_scheduled_device_status


sys = SystemInitializer()


app = FastAPI()


controller_device = ControllerDevice()


scheduled_devices = controller_device.get_scheduled_devices()
scheduled_devices = scheduled_devices if scheduled_devices is not None else []
schedule_assistant = ScheduleDeviceAssistant(scheduled_devices)


@app.get("/get-house-member", status_code=status.HTTP_200_OK)
def get_house_member(userId: str):
    if not is_valid_request([userId]):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": "Please provide userId."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    house_member = get_user(userId)

    if isinstance(house_member, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": house_member._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if house_member is None:
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": f"House member with id '{userId}' not found."
            },
            status_code=status.HTTP_404_NOT_FOUND
        )

    return JSONResponse(
        content={
            "status": "success",
            "status_code": ResponseStatusCodes.REQUEST_FULLFILLED,
            "message": f"House member with id '{userId}' found.",
            "data": house_member.to_dict()
        },
        status_code=status.HTTP_200_OK
    )


@app.post("/house-login", status_code=status.HTTP_201_CREATED)
def house_login(userId: str, password: str):
    if not is_valid_request([userId, password]):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": "Please provide userId and password."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    is_authenticated = sys.house_login(password)

    if is_authenticated is None:
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.HOUSE_NOT_INITIALIZED,
                "message": "House is not initialized."
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    if not is_authenticated:
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_CREDS,
                "message": "Password was wrong."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    house_member = add_user(userId)

    if isinstance(house_member, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": house_member._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return JSONResponse(
        content={
            "status": "success",
            "status_code": ResponseStatusCodes.USER_LOGGEDIN,
            "message": f"Logged into the house and user with id '{userId}' added as a member.",
            "data": house_member.to_dict()
        },
        status_code=status.HTTP_201_CREATED
    )


@app.get("/get-house", status_code=status.HTTP_200_OK)
def get_house_details(userId: str):
    if not is_valid_request([userId]):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": "Please provide userId, userName, houseId and roomName."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    user = get_user(userId)

    if isinstance(user, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": user._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if user is None:
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": f"User with id '{userId}' not found."
            },
            status_code=status.HTTP_404_NOT_FOUND
        )

    is_authenticated = get_access(userId)

    if isinstance(is_authenticated, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": is_authenticated._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if not is_authenticated:
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_REQUEST,
                "message": f"{userId} is not authorized to perform this operation."
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

    house_data = get_house_data()

    if isinstance(house_data, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": house_data._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return JSONResponse(
        content={
            "status": "success",
            "status_code": ResponseStatusCodes.REQUEST_FULLFILLED,
            "message": "House data retrieved successfully.",
            "data": house_data.to_dict()
        },
        status_code=status.HTTP_200_OK
    )


@app.post("/add-room", status_code=status.HTTP_201_CREATED)
def add_room(request_body: AddRoomRequest):

    if not is_valid_request([request_body.userId, request_body.userName, request_body.houseId, request_body.roomName]):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": "Please provide userId, userName, houseId and roomName."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    is_authenticated = get_access(request_body.userId)

    if isinstance(is_authenticated, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": is_authenticated._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if not is_authenticated:
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_REQUEST,
                "message": f"{request_body.userName} is not authorized to perform this operation."
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

    room = create_room(request_body.roomName, request_body.houseId)

    if isinstance(room, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": room._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    controller_device.add_room(room)

    return JSONResponse(
        content={
            "status": "success",
            "status_code": ResponseStatusCodes.REQUEST_FULLFILLED,
            "message": "Room created successfully.",
            "data": room.to_dict()
        },
        status_code=status.HTTP_201_CREATED
    )


@app.delete("/remove-room", status_code=status.HTTP_200_OK)
def delete_room(request_body: RemoveRoomRequest):

    if not is_valid_request([request_body.userId, request_body.userName, request_body.houseId, request_body.roomId]):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": "Please provide userId, userName, houseId and roomId."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    is_authenticated = get_access(request_body.userId)

    if isinstance(is_authenticated, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": is_authenticated._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if not is_authenticated:
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_REQUEST,
                "message": f"{request_body.userName} is not authorized to perform this operation."
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

    delete_count = remove_room(request_body.roomId)

    if isinstance(delete_count, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": delete_count._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    controller_device.remove_room(request_body.roomId)

    return JSONResponse(
        content={
            "status": "success",
            "status_code": ResponseStatusCodes.REQUEST_FULLFILLED,
            "message": f"{delete_count} Room(s) deleted successfully.",
        },
        status_code=status.HTTP_201_CREATED
    )


@app.post("/add-device", status_code=status.HTTP_201_CREATED)
def add_device(request_body: AddDeviceRequest):

    if not is_valid_request([request_body.userId and request_body.userName and request_body.houseId and request_body.roomId and request_body.pinNumber and request_body.deviceName]):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": "Please provide userId, userName, houseId, roomId, pinNumber and deviceName."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    is_authenticated = get_access(request_body.userId)

    if isinstance(is_authenticated, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": is_authenticated._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if not is_authenticated:
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_REQUEST,
                "message": f"{request_body.userName} is not authorized to perform this operation."
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

    device = create_device(request_body.deviceName,
                           request_body.pinNumber, request_body.roomId)

    if isinstance(device, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": device._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    controller_device.add_device(device)

    return JSONResponse(
        content={
            "status": "success",
            "status_code": ResponseStatusCodes.REQUEST_FULLFILLED,
            "message": "Device created successfully.",
            "data": device.to_dict()
        },
        status_code=status.HTTP_201_CREATED
    )


@app.patch("/switch-device", status_code=status.HTTP_202_ACCEPTED)
def toggle_device(request_body: SwitchDeviceRequest):

    if not is_valid_request([request_body.userId, request_body.userName, request_body.houseId, request_body.deviceId, request_body.statusFrom, request_body.statusTo]):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": "Please provide userId, userName, houseId, deviceId, statusFrom and statusTo."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    is_authenticated = get_access(request_body.userId)

    if isinstance(is_authenticated, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": is_authenticated._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if not is_authenticated:
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_REQUEST,
                "message": f"{request_body.userName} is not authorized to perform this operation."
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

    controller_device.switch_device(
        request_body.deviceId, request_body.statusTo)
    update_count = switch_device(request_body.deviceId,
                                 request_body.statusFrom, request_body.statusTo, request_body.userId)

    if isinstance(update_count, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": update_count._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    _state = "on" if request_body.statusTo else "off"

    return JSONResponse(
        content={
            "status": "success",
            "status_code": ResponseStatusCodes.REQUEST_FULLFILLED,
            "message": "Device Switched successfully.",
            "data": f"{update_count} device(s) swicthed {_state}"
        },
        status_code=status.HTTP_201_CREATED
    )


@app.put("/configure-device", status_code=status.HTTP_202_ACCEPTED)
def config_device(request_body: ConfigureDeviceRequest):

    if not is_valid_request([request_body.houseId, request_body.userId, request_body.userName, request_body.deviceId, request_body.deviceName, request_body.pinNumber, request_body.status, request_body.isScheduled]):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": "Please provide houseId, userId, userName, deviceId, deviceName, pinNumber, status and isScheduled."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    is_authenticated = get_access(request_body.userId)

    if isinstance(is_authenticated, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": is_authenticated._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if not is_authenticated:
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_REQUEST,
                "message": f"{request_body.userName} is not authorized to perform this operation."
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

    updated_device_count = configure_device(request_body.deviceId,
                                            request_body.deviceName, request_body.pinNumber, request_body.status, request_body.isScheduled, request_body.daysScheduled, request_body.startTime, request_body.offTime, request_body.userId)

    if isinstance(updated_device_count, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": updated_device_count._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    device = controller_device.get_device(request_body.deviceId)

    if device is not None:
        controller_device.remove_device(device.device_id)

        is_on = get_scheduled_device_status(
            request_body.startTime, request_body.offTime)

        device.device_name = request_body.deviceName
        device.pin_number = request_body.pinNumber
        device.is_scheduled = request_body.isScheduled
        device.days_scheduled = request_body.daysScheduled if request_body.isScheduled else ""
        device.start_time = request_body.startTime if request_body.isScheduled else ""
        device.off_time = request_body.offTime if request_body.isScheduled else ""
        device.status = is_on if request_body.isScheduled else device.status
        device.scheduled_by = request_body.userId
        device.output_device = None

        controller_device.add_device(device)
        new_device = controller_device.get_device(device.device_id)

        if new_device is not None:
            if request_body.isScheduled:
                schedule_assistant.schedule_device(new_device)
            else:
                schedule_assistant.remove_scheduled_device(
                    new_device.device_id)

    return JSONResponse(
        content={
            "status": "success",
            "status_code": ResponseStatusCodes.REQUEST_FULLFILLED,
            "message": "Device Configured successfully.",
            "data": f"{updated_device_count} Device(s) configured."
        },
        status_code=status.HTTP_201_CREATED
    )


@app.delete("/remove-device", status_code=status.HTTP_200_OK)
def delete_device(request_body: RemoveDeviceRequest):

    if not is_valid_request([request_body.userId, request_body.userName, request_body.houseId, request_body.roomId, request_body.deviceId]):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_DATA,
                "message": "Please provide userId, userName, houseId, roomId and deviceId."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    is_authenticated = get_access(request_body.userId)

    if isinstance(is_authenticated, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": is_authenticated._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if not is_authenticated:
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.INVALID_REQUEST,
                "message": f"{request_body.userName} is not authorized to perform this operation."
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

    delete_count = remove_device(request_body.deviceId)

    if isinstance(delete_count, SQLAlchemyError):
        return JSONResponse(
            content={
                "status": "error",
                "status_code": ResponseStatusCodes.SERVER_ERROR,
                "message": delete_count._message()
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    controller_device.remove_device(request_body.deviceId)

    return JSONResponse(
        content={
            "status": "success",
            "status_code": ResponseStatusCodes.REQUEST_FULLFILLED,
            "message": f"{delete_count} Device(s) deleted successfully.",
        },
        status_code=status.HTTP_201_CREATED
    )
