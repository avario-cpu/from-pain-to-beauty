import atexit

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

import constants

HERO_PICK_CAPTURE_AREA = {"left": 790, "top": 140, "width": 340, "height": 40}
HERO_PICK_TEMPLATE_PATH = "opencv/dota_select_your_hero_message.jpg"
SECONDARY_WINDOWS = [my.SecondaryWindow("opencv_hero_pick_scanner", 340,
                                        40), ]
SCRIPT_NAME = "dota2_pregame_detector"
STREAMERBOT_WS_URL = "ws://127.0.0.1:50001/"
stop_hero_pick_loop = asyncio.Event()
secondary_windows_have_spawned = asyncio.Event()
mute_main_loop_print_feedback = asyncio.Event()
stop_subprocess = asyncio.Event()


class PregameSate:

    def __init__(self):
        self.hero_pick = False
        self.starting_buy = False
        self.versus_screen = False


async def handle_socket_client(reader, writer):
    while True:
        data = await reader.read(1024)
        if not data:
            print("Socket client disconnected")
            break
        message = data.decode()
        if message == constants.STOP_SUBPROCESS_MESSAGE:
            stop_subprocess.set()
        print(f"Received: {message}")
        writer.write(b"ACK from WebSocket server")
        await writer.drain()
    writer.close()


async def run_socket_server():
    server = await asyncio.start_server(handle_socket_client, 'localhost',
                                        59000)
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


async def capture_window(area):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


async def compare_images(image_a, image_b):
    return ssim(image_a, image_b)


async def detect_hero_pick_phase():
    game_sate = PregameSate()
    template = cv.imread(HERO_PICK_TEMPLATE_PATH, cv.IMREAD_GRAYSCALE)

    while not stop_hero_pick_loop.is_set():
        frame = await capture_window(HERO_PICK_CAPTURE_AREA)
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        match_value = await compare_images(gray_frame, template)
        cv.imshow(SECONDARY_WINDOWS[0].name, gray_frame)
        secondary_windows_have_spawned.set()

        if cv.waitKey(1) == ord("q"):
            break
        if not mute_main_loop_print_feedback.is_set():
            print(f"SSIM: {match_value:.6f}", end="\r")
        if match_value >= 0.8:
            game_sate.hero_pick = True
            print("Hey! You're picking :)")
            await asyncio.sleep(1)
        await asyncio.sleep(0.01)


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


if __name__ == "__main__":
    try:
        asyncio.run(detect_hero_pick_phase())
    finally:
        cv.destroyAllWindows()
