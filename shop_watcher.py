import asyncio
import atexit
import logging
import time

import cv2 as cv
import mss
import numpy as np
import websockets
from skimage.metrics import structural_similarity as ssim
from websockets import WebSocketException

import denied_slots_db_handler as denied_sdh
import my_classes as my
import single_instance
import slots_db_handler as sdh
import terminal_window_manager_v4 as twm
import constants

# Configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - '
                           '%(message)s',
                    filename="temp/logs/shop_watcher.log")
logger = logging.getLogger(__name__)

SCREEN_CAPTURE_AREA = {"left": 1883, "top": 50, "width": 37, "height": 35}
TEMPLATE_IMAGE_PATH = 'opencv/dota_shop_top_right_icon.jpg'
WEBSOCKET_URL = "ws://127.0.0.1:8080/"
SCRIPT_NAME = "dota2_shop_watcher"
SECONDARY_WINDOWS = [my.SecondaryWindow("opencv_shop_scanner", 100, 100)]

secondary_windows_have_spawned = asyncio.Event()
mute_main_loop_print_feedback = asyncio.Event()
stop_loop = asyncio.Event()


def exit_countdown():
    """Give a bit of time to read terminal exit statements"""
    for seconds in reversed(range(1, 6)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    exit()


async def establish_ws_connection():
    try:
        ws = await websockets.connect(WEBSOCKET_URL)
        logger.info(f"Established connection: {ws}")
        return ws
    except WebSocketException as e:
        logger.debug(f"Websocket error: {e}")
    except OSError as e:
        logger.debug(f"OS error: {e}")
    return None


async def handle_socket_client(reader, writer):
    while True:
        data = await reader.read(1024)
        if not data:
            print("Socket client disconnected")
            break
        message = data.decode()
        if message == constants.STOP_SUBPROCESS_MESSAGE:
            stop_loop.set()
        print(f"Received: {message}")
        writer.write(b"ACK from WebSocket server")
        await writer.drain()
    writer.close()


async def run_socket_server():
    server = await asyncio.start_server(handle_socket_client, 'localhost',
                                        9999)
    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")

    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        print("Socket server task was cancelled. Stopping server")
    finally:
        server.close()
        await server.wait_closed()
        print("Server closed")


async def send_json_request(ws, json_file_path):
    with open(json_file_path, 'r') as file:
        await ws.send(file.read())
    response = await ws.recv()
    logger.info(f"WebSocket response: {response}")


async def capture_window(area):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


async def compare_images(image_a, image_b):
    return ssim(image_a, image_b)


async def react_to_shop(ws, state):
    print(f"Shop just {state}")
    if state == "opened" and ws:
        await send_json_request(
            ws, "streamerbot_ws_requests/hide_dslr.json")
    elif state == "closed" and ws:
        await send_json_request(
            ws, "streamerbot_ws_requests/show_dslr.json")


async def scan_for_shop_and_notify(ws):
    shop_is_currently_open = False
    template = cv.imread(TEMPLATE_IMAGE_PATH, cv.IMREAD_GRAYSCALE)

    while not stop_loop.is_set():
        frame = await capture_window(SCREEN_CAPTURE_AREA)
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        match_value = await compare_images(gray_frame, template)
        cv.imshow(SECONDARY_WINDOWS[0].name, gray_frame)
        secondary_windows_have_spawned.set()

        if cv.waitKey(1) == ord("q"):
            break
        if not mute_main_loop_print_feedback.is_set():
            print(f"SSIM: {match_value:.6f}", end="\r")

        if match_value >= 0.8 and not shop_is_currently_open:
            shop_is_currently_open = True
            await react_to_shop(ws, "opened")
        elif match_value < 0.8 and shop_is_currently_open:
            shop_is_currently_open = False
            await react_to_shop(ws, "closed")
        await asyncio.sleep(0)
    if ws:
        await ws.close()
        cv.destroyAllWindows()
    print('loop terminated')


async def main():
    """If there are no single instance lock file, start the Dota2 shop_watcher
     module. Reposition the terminal right at launch."""
    if single_instance.lock_exists():
        slot = twm.manage_window(twm.WinType.DENIED, SCRIPT_NAME)
        atexit.register(denied_sdh.free_slot, slot)
        print("\n>>> Lock file is present: exiting... <<<")

    else:
        slot = twm.manage_window(twm.WinType.ACCEPTED,
                                 SCRIPT_NAME, SECONDARY_WINDOWS)

        single_instance.create_lock_file()
        atexit.register(single_instance.remove_lock)
        atexit.register(sdh.free_slot_named, SCRIPT_NAME)
        socket_server_task = asyncio.create_task(run_socket_server())
        mute_main_loop_print_feedback.set()  # avoid ugly lines due to caret
        # replacement print

        ws = None
        try:
            ws = await establish_ws_connection()
            main_task = asyncio.create_task(scan_for_shop_and_notify(ws))
            await secondary_windows_have_spawned.wait()
            twm.manage_secondary_windows(slot, SECONDARY_WINDOWS)
            mute_main_loop_print_feedback.clear()
            await main_task
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
        finally:
            socket_server_task.cancel()
            await socket_server_task
            cv.destroyAllWindows()
            if ws:
                await ws.close()


if __name__ == "__main__":
    asyncio.run(main())
    input('enter to q')
