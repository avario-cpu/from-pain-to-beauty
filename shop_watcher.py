import asyncio
import logging

import cv2 as cv
import mss
import numpy as np
import websockets
from skimage.metrics import structural_similarity as ssim
from websockets import WebSocketException

# Configuration
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S',
                    filename="temp/logs/shop_watcher.log")

SCREEN_CAPTURE_AREA = {"left": 1883, "top": 50, "width": 37, "height": 35}
TEMPLATE_IMAGE_PATH = 'opencv/dota_shop_top_right_icon.jpg'
WEBSOCKET_URL = "ws://127.0.0.1:8080/"
SECONDARY_WINDOW_NAMES = ['opencv_shop_watcher']

secondary_window_spawned = asyncio.Event()
mute_print_feedback = asyncio.Event()
stop_loop = asyncio.Event()


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
    addr = writer.get_extra_info('peername')
    print(f"Socket server connected by {addr}")
    while True:
        data = await reader.read(1024)
        if not data:
            print("Socket client disconnected")
            break
        message = data.decode()
        print(f"Received from subprocess: {message}")
        writer.write(b"ACK from WebSocket server")
        await writer.drain()
    writer.close()


async def run_socket_server():
    server = await asyncio.start_server(handle_socket_client, 'localhost',
                                        9999)
    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")

    async with server:
        await server.serve_forever()


async def scan_for_shop_and_notify(ws):
    shop_is_currently_open = False
    template = cv.imread(TEMPLATE_IMAGE_PATH, cv.IMREAD_GRAYSCALE)

    while not stop_loop.is_set():
        frame = await capture_window(SCREEN_CAPTURE_AREA)
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        match_value = await compare_images(gray_frame, template)
        cv.imshow(SECONDARY_WINDOW_NAMES[0], gray_frame)
        secondary_window_spawned.set()

        if cv.waitKey(1) == ord("q"):
            break
        if not mute_print_feedback.is_set():
            print(f"SSIM: {match_value}", end="\r")

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


async def main():
    socket_server = run_socket_server()
    ws = None
    try:
        await asyncio.gather(socket_server)
        ws = await establish_ws_connection()
        await scan_for_shop_and_notify(ws)
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
    finally:
        if ws:
            await ws.close()
        cv.destroyAllWindows()


if __name__ == "__main__":
    asyncio.run(main())
