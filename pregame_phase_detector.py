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
from enum import Enum, auto


class PreGamePhases:

    def __init__(self):
        self.finding_game = False
        self.hero_pick = False
        self.starting_buy = False
        self.versus_screen = False
        self.in_game = False


class Interruption(Enum):
    TAB_OUT = auto()
    GAME_CANCELED = auto()
    DRAFT_SCREEN_SWAP = auto()
    EXIT = auto()
    SETTINGS_SCREEN = auto()


PICK_PHASE_AREA = {"left": 880, "top": 70, "width": 160, "height": 30}
STARTING_BUY_AREA = {"left": 860, "top": 120, "width": 400, "height": 30}
IN_GAME_AREA = {"left": 1820, "top": 1020, "width": 80, "height": 60}
DOTA_SETTINGS_AREA = {"left": 60, "top": 10, "width": 40, "height": 40}
SEARCH_GAME_BUTTON_AREA = {"left": 1525, "top": 1005, "width": 340,
                           "height": 55}

ALL_PICK_TEMPLATE = "opencv/all_pick.jpg"
STRATEGY_TIME_TEMPLATE = "opencv/strategy_time.jpg"
STARTING_BUY_TEMPLATE = "opencv/strategy-loadout-world-guides.jpg"
IN_GAME_TEMPLATE = "opencv/deliver_items_icon.jpg"
SETTINGS_WHEEL_TEMPLATE = "opencv/settings_wheel.jpg"
PLAY_DOTA_BUTTON_TEMPLATE = "opencv/play_dota.jpg"
RETURN_TO_GAME_TEMPLATE = "opencv/return_to_game.jpg"

SECONDARY_WINDOWS = [my.SecondaryWindow("opencv_hero_pick_scanner", 400, 100)]
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


async def send_streamerbot_ws_request(ws, game_phase):
    if game_phase.in_game:
        await send_json_requests(
            ws, "streamerbot_ws_requests/switch_to_meta_scene.json")
    elif game_phase.versus_screen:
        await send_json_requests(
            ws, "streamerbot_ws_requests/dslr_hide_for_VS_screen.json")
    elif game_phase.starting_buy:
        await send_json_requests(
            ws, "streamerbot_ws_requests/dslr_move_for_starting_buy.json")
    elif game_phase.hero_pick:
        await send_json_requests(
            ws,
            "streamerbot_ws_requests/scene_change_and_dslr_move_for_pick.json")
    elif game_phase.finding_game:
        await send_json_requests(
            ws, "streamerbot_ws_requests/switch_to_meta_scene.json")


async def capture_and_process_image(capture_area, template):
    frame = await capture_window(capture_area)
    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    match_value = await compare_images(gray_frame, template)
    cv.imshow(SECONDARY_WINDOWS[0].name, gray_frame)
    secondary_windows_have_spawned.set()
    return match_value


async def capture_new_area(capture_area, filename):
    frame = await capture_window(capture_area)
    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    cv.imshow(SECONDARY_WINDOWS[0].name, gray_frame)
    secondary_windows_have_spawned.set()
    cv.imwrite(filename, gray_frame)


async def define_relevant_match(game_phase: PreGamePhases):
    capture_area = None
    template = None
    if game_phase.in_game:
        pass
    elif game_phase.versus_screen:
        capture_area = IN_GAME_AREA
        template = cv.imread(IN_GAME_TEMPLATE, cv.IMREAD_GRAYSCALE)
    elif game_phase.starting_buy or game_phase.hero_pick:
        capture_area = STARTING_BUY_AREA
        template = cv.imread(STARTING_BUY_TEMPLATE, cv.IMREAD_GRAYSCALE)
    elif game_phase.finding_game:
        capture_area = PICK_PHASE_AREA
        template = cv.imread(ALL_PICK_TEMPLATE, cv.IMREAD_GRAYSCALE)
    return capture_area, template


async def analyze_dota_interrupt():

    # Check if "All pick" or "Strategy time" still show up
    if (await capture_and_process_image(
            PICK_PHASE_AREA, ALL_PICK_TEMPLATE) >= 0.8
            or await
            capture_and_process_image(
                PICK_PHASE_AREA, STRATEGY_TIME_TEMPLATE) >= 0.8):
        return Interruption.DRAFT_SCREEN_SWAP

    # Check if "Return to game" button shows up
    elif (await capture_and_process_image(
            SEARCH_GAME_BUTTON_AREA, RETURN_TO_GAME_TEMPLATE) >= 0.8):
        return Interruption.TAB_OUT

    # Check if "Play Dota" button shows up
    elif (await capture_and_process_image(
            SEARCH_GAME_BUTTON_AREA, PLAY_DOTA_BUTTON_TEMPLATE) >= 0.8):
        return Interruption.GAME_CANCELED

    else:
        return None


async def detect_pregame_phase(ws):
    game_phase = PreGamePhases()
    game_phase.finding_game = True
    capture_area, template = await define_relevant_match(game_phase)

    while not stop_loop.is_set():

        match_value = await capture_and_process_image(capture_area, template)
        # match_value = 0.7
        # await capture_new_area(PLAY_DOTA_AREA, "opencv/return_to_game.jpg")

        if cv.waitKey(1) == ord("q"):
            break
        if not mute_main_loop_print_feedback.is_set():
            print(f"SSIM: {match_value:.6f}", end="\r")

        if match_value >= 0.8 and not game_phase.hero_pick:
            print("On hero pick screen")
            game_phase.hero_pick = True
            capture_area, template = await define_relevant_match(game_phase)
            await send_streamerbot_ws_request(ws, game_phase)
            continue

        elif match_value <= 0.8 and game_phase.hero_pick:
            # So, we lost track of the all pick template
            print("Exited hero pick")
            pass

        elif match_value >= 0.8 and not game_phase.starting_buy:
            print("Now, this is the starting buy !")
            game_phase.starting_buy = True
            await send_streamerbot_ws_request(ws, game_phase)

        elif (match_value <= 0.8 and game_phase.starting_buy and
              not game_phase.versus_screen):
            # So, we lost track of the starting buy template
            print("You exited the starting buy screen...")
            if analyze_dota_interrupt() == Interruption.DRAFT_SCREEN_SWAP:
                print("You're back on the hero pick screen")
                game_phase.starting_buy = False
                await send_streamerbot_ws_request(ws, game_phase)
                capture_area, template = await define_relevant_match(
                    game_phase)
                continue

            elif analyze_dota_interrupt() == Interruption.TAB_OUT:
                print("Tabbed out of starting buy screen in Dota", end="\r")
                continue

            elif analyze_dota_interrupt() == Interruption.GAME_CANCELED:
                print("Your game got canceled ! Resetting the script.")
                game_phase.hero_pick = False
                game_phase.starting_buy = False
                await send_streamerbot_ws_request(ws, game_phase)
                capture_area, template = await define_relevant_match(
                    game_phase)

            # If none of the above, we are in VS screen or left the app. As
            # of now, I do not differentiate between the two (too much work)
            else:
                print("You're in VS screen, or left Dota")
                game_phase.versus_screen = True
                capture_area, template = await define_relevant_match(
                    game_phase)
                await send_streamerbot_ws_request(ws, game_phase)

        elif (match_value >= 0.8 and game_phase.versus_screen
              and not game_phase.in_game):
            game_phase.in_game = True
            print("Woah ! You're in game now !")
            await send_streamerbot_ws_request(ws, game_phase)
            print("script will exit in 5 seconds..")
            await asyncio.sleep(5)
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
