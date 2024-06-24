import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim
import asyncio
import my_classes as my

HERO_PICK_CAPTURE_AREA = {"left": 790, "top": 140, "width": 340, "height": 40}
HERO_PICK_TEMPLATE_PATH = "opencv/dota_select_your_hero_message.jpg"
SECONDARY_WINDOWS = [my.SecondaryWindow("opencv_hero_pick_scanner", 340,
                                        40), ]
stop_hero_pick_loop = asyncio.Event()
secondary_windows_have_spawned = asyncio.Event()
mute_main_loop_print_feedback = asyncio.Event()


class PregameSate:

    def __init__(self):
        self.hero_pick = False
        self.starting_buy = False
        self.versus_screen = False


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


if __name__ == "__main__":
    try:
        asyncio.run(detect_hero_pick_phase())
    finally:
        cv.destroyAllWindows()
