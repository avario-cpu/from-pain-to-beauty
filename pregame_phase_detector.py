import atexit
import os

import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim
import asyncio
import my_classes as my
import single_instance
import terminal_window_manager_v4 as twm
import denied_slots_db_handler as denied_sdh
import slots_db_handler as sdh
import websockets
from websockets import WebSocketException, ConnectionClosedError
import constants
import logging
import time


class PregameState:

    def __init__(self):
        self.hero_pick = False
        self.starting_buy = False
        self.versus_screen = False
        self.in_game = False


HERO_PICK_CAPTURE_AREA = {"left": 790, "top": 140, "width": 340, "height": 40}
HERO_PICK_TEMPLATE_PATH = "opencv/dota_choose_your_hero_message.jpg"
START_BUY_CAPTURE_AREA = {"left": 880, "top": 70, "width": 160, "height": 30}
START_BUY_TEMPLATE_PATH = "opencv/dota_strategy_time_message.jpg"
IN_GAME_CAPTURE_AREA = {"left": 1820, "top": 1020, "width": 80, "height": 60}
IN_GAME_TEMPLATE_PATH = "opencv/dota_deliver_items_icon.jpg"
SECONDARY_WINDOWS = [my.SecondaryWindow("opencv_hero_pick_scanner", 350, 100)]
SCRIPT_NAME = constants.SCRIPT_NAME_SUFFIX + os.path.splitext(
    os.path.basename(__file__))[0] if __name__ == "__main__" else __name__
# suffix added to avoid window naming conflicts with cli manager
STREAMERBOT_WS_URL = "ws://127.0.0.1:50001/"

secondary_windows_have_spawned = asyncio.Event()
mute_main_loop_print_feedback = asyncio.Event()
stop_loop = asyncio.Event()

logger = logging.getLogger(SCRIPT_NAME)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(f'temp/logs/{SCRIPT_NAME}.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


def exit_countdown():
    """Give a bit of time to read terminal exit statements"""
    for seconds in reversed(range(1, 5)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    exit()


async def establish_ws_connection():
    try:
        ws = await websockets.connect(STREAMERBOT_WS_URL)
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
    logger.info("Starting run_socket_server")
    server = await asyncio.start_server(handle_socket_client, 'localhost',
                                        constants.SUBPROCESSES[SCRIPT_NAME])
    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")
    logger.info(f"Serving on {addr}")

    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        print("Socket server task was cancelled. Stopping server")
    finally:
        server.close()
        await server.wait_closed()
        print("Server closed")


async def capture_window(area):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


async def compare_images(image_a, image_b):
    return ssim(image_a, image_b)


async def send_json_requests(ws, json_file_paths: str | list[str]):
    if isinstance(json_file_paths, str):
        json_file_paths = [json_file_paths]

    for json_file in json_file_paths:
        try:
            with open(json_file, 'r') as file:
                await ws.send(file.read())
            response = await ws.recv()
            logger.info(f"WebSocket response: {response}")
        except ConnectionClosedError as e:
            logger.error(f"WebSocket connection closed: {e}")
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")


async def send_streamerbot_ws_request(ws, game_state):
    if game_state.in_game:
        await send_json_requests(
            ws, "streamerbot_ws_requests/switch_to_meta_scene.json")
    elif game_state.versus_screen:
        await send_json_requests(
            ws, "streamerbot_ws_requests/dslr_hide_for_VS_screen.json")
    elif game_state.starting_buy:
        await send_json_requests(
            ws, "streamerbot_ws_requests/dslr_move_for_starting_buy.json")
    elif game_state.hero_pick:
        await send_json_requests(
            ws, ["streamerbot_ws_requests/dslr_move_for_hero_pick.json",
                 "streamerbot_ws_requests/switch_to_game_start_scene.json"])


async def detect_pregame_phase(ws):
    game_sate = PregameState()
    template = cv.imread(HERO_PICK_TEMPLATE_PATH, cv.IMREAD_GRAYSCALE)
    capture_area = HERO_PICK_CAPTURE_AREA

    while not stop_loop.is_set():
        frame = await capture_window(capture_area)
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        match_value = await compare_images(gray_frame, template)
        cv.imshow(SECONDARY_WINDOWS[0].name, gray_frame)
        secondary_windows_have_spawned.set()

        if cv.waitKey(1) == ord("q"):
            break
        if not mute_main_loop_print_feedback.is_set():
            print(f"SSIM: {match_value:.6f}", end="\r")
        if match_value >= 0.8 and not game_sate.hero_pick:
            game_sate.hero_pick = True
            print("Hey! You're picking :)")
            capture_area = START_BUY_CAPTURE_AREA
            template = cv.imread(START_BUY_TEMPLATE_PATH, cv.IMREAD_GRAYSCALE)
            await send_streamerbot_ws_request(ws, game_sate)

        elif match_value >= 0.8 and not game_sate.starting_buy:
            game_sate.starting_buy = True
            print("Oh, now this is the starting buy !")
            await send_streamerbot_ws_request(ws, game_sate)

        elif (match_value <= 0.8
              and game_sate.hero_pick
              and game_sate.starting_buy
              and not game_sate.versus_screen):
            game_sate.versus_screen = True
            print("Hey look, you're in VS screen :)")
            capture_area = IN_GAME_CAPTURE_AREA
            template = cv.imread(IN_GAME_TEMPLATE_PATH, cv.IMREAD_GRAYSCALE)
            await send_streamerbot_ws_request(ws, game_sate)

        elif (match_value >= 0.8
              and game_sate.versus_screen
              and not game_sate.in_game):
            game_sate.in_game = True
            print("Woah ! You're in game now !")
            await send_streamerbot_ws_request(ws, game_sate)
            print("Okay, finished. Leaving the script now :)")
            break

        await asyncio.sleep(0.01)


async def main():
    if single_instance.lock_exists(SCRIPT_NAME):
        slot = twm.manage_window(twm.WinType.DENIED, SCRIPT_NAME)
        atexit.register(denied_sdh.free_slot, slot)
        print("\n>>> Lock file is present: exiting... <<<")
    else:
        slot = twm.manage_window(twm.WinType.ACCEPTED,
                                 SCRIPT_NAME, SECONDARY_WINDOWS)
        single_instance.create_lock_file(SCRIPT_NAME)
        atexit.register(single_instance.remove_lock, SCRIPT_NAME)
        atexit.register(sdh.free_slot_named, SCRIPT_NAME)
        socket_server_task = asyncio.create_task(run_socket_server())
        mute_main_loop_print_feedback.set()

        ws = None
        try:
            ws = await establish_ws_connection()
            main_task = asyncio.create_task(detect_pregame_phase(ws))
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
    exit_countdown()
