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
import single_instance
import slots_db_handler as sdh
import terminal_window_manager_v3 as twm_v3
import constants


class SecondaryWindow:
    def __init__(self, name, width, height):
        self.name = name
        self.width = width
        self.height = height


# Configuration
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S',
                    filename="temp/logs/shop_watcher.log")

SCREEN_CAPTURE_AREA = {"left": 1883, "top": 50, "width": 37, "height": 35}
TEMPLATE_IMAGE_PATH = 'opencv/dota_shop_top_right_icon.jpg'
WEBSOCKET_URL = "ws://127.0.0.1:8080/"
SCRIPT_NAME = "dota2_shop_watcher"
SECONDARY_WINDOWS = [SecondaryWindow("opencv_shop_scanner", 100, 100)]

secondary_windows_have_spawned = asyncio.Event()
mute_main_loop_print_feedback = asyncio.Event()
stop_loop = asyncio.Event()


def exit_countdown():
    """Give a bit of time to read terminal exit statements"""
    for seconds in reversed(range(1, 6)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    exit()


async def capture_window(area):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


async def compare_images(image_a, image_b):
    return ssim(image_a, image_b)


async def send_json_request(ws, json_file_path):
    with open(json_file_path, 'r') as file:
        await ws.send(file.read())
    response = await ws.recv()
    logging.info(f"WebSocket response: {response}")


async def establish_ws_connection():
    try:
        ws = await websockets.connect(WEBSOCKET_URL)
        logging.info(f"Established connection: {ws}")
        return ws
    except WebSocketException as e:
        logging.debug(f"Websocket error: {e}")
    except OSError as e:
        logging.debug(f"OS error: {e}")
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
            print("Shop just opened")
            if ws:
                await send_json_request(
                    ws, "streamerbot_ws_requests/hide_dslr.json")
        elif match_value < 0.8 and shop_is_currently_open:
            shop_is_currently_open = False
            print("Shop just closed")
            if ws:
                await send_json_request(
                    ws, "streamerbot_ws_requests/show_dslr.json")
        await asyncio.sleep(0)
    if ws:
        await ws.close()
        cv.destroyAllWindows()
    print('loop terminated')


async def main():
    """If there are no single instance lock file, start the Dota2 shop_watcher
     module. At launch, reposition immediately the terminal providing feedback
    regarding its execution. Shortly after, reposition the secondary window
    which the module spawns. This is all done in an asynchronous way thanks
    to a database providing information used for the window positions"""
    if single_instance.lock_exists():
        slot = twm_v3.handle_window(twm_v3.WindowType.DENIED_SCRIPT,
                                    SCRIPT_NAME)
        atexit.register(denied_sdh.free_slot, slot)
        print("\n>>> Lock file is present: exiting... <<<")

    else:
        slot = twm_v3.handle_window(twm_v3.WindowType.ACCEPTED_SCRIPT,
                                    SCRIPT_NAME, SECONDARY_WINDOW_NAMES)

        single_instance.create_lock_file()
        atexit.register(single_instance.remove_lock)
        atexit.register(sdh.free_slot_named, SCRIPT_NAME)
        socket_server_task = asyncio.create_task(run_socket_server())
        mute_main_loop_print_feedback.set()

        ws = None
        try:
            ws = await establish_ws_connection()
            main_task = asyncio.create_task(scan_for_shop_and_notify(ws))
            await secondary_windows_have_spawned.wait()
            twm_v3.adjust_secondary_windows(slot, SECONDARY_WINDOW_NAMES)
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
    logging.info("START")
    asyncio.run(main())
    input('enter to q')
