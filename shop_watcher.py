import asyncio
import logging

import cv2 as cv
import mss
import numpy as np
import websockets
from skimage.metrics import structural_similarity as ssim

# Configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
SCREEN_CAPTURE_AREA = {"left": 1883, "top": 50, "width": 37, "height": 35}
TEMPLATE_IMAGE_PATH = 'opencv/dota_shop_top_right_icon.jpg'
WEBSOCKET_URL = "ws://127.0.0.1:8080/"
SECONDARY_WINDOW_NAMES = ['opencv_shop_watcher']

secondary_window_spawned = asyncio.Event()
mute_print = asyncio.Event()
stop_event_loop = asyncio.Event()


async def capture_window(area):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


async def compare_images(image_a, image_b):
    return ssim(image_a, image_b)


async def send_websocket_json_message(ws, json_file_path):
    with open(json_file_path, 'r') as file:
        await ws.send(file.read())
    response = await ws.recv()
    logging.info(f"WebSocket response: {response}")


async def scan_for_shop_and_notify():
    shop_is_currently_open = False
    template = cv.imread(TEMPLATE_IMAGE_PATH, cv.IMREAD_GRAYSCALE)
    async with websockets.connect(WEBSOCKET_URL) as ws:
        while not stop_event_loop:
            frame = await capture_window(SCREEN_CAPTURE_AREA)
            gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            match_value = await compare_images(gray_frame, template)

            cv.imshow(SECONDARY_WINDOW_NAMES[0], gray_frame)
            secondary_window_spawned.set()
            if cv.waitKey(1) == ord("q"):
                break

            if not mute_print:
                print(f"SSIM: {match_value}", end="\r")

            if match_value >= 0.8 and not shop_is_currently_open:
                logging.info("Shop just opened")
                await send_websocket_json_message(
                    ws, "streamerbot_ws_requests/hide_dslr.json")
                shop_is_currently_open = True

            elif match_value < 0.8 and shop_is_currently_open:
                logging.info("Shop just closed")
                await send_websocket_json_message(
                    ws, "streamerbot_ws_requests/show_dslr.json")
                shop_is_currently_open = False
            await asyncio.sleep(0)


async def main():
    await scan_for_shop_and_notify()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        cv.destroyAllWindows()
