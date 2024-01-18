import cv2 as cv
import time
import mss
import numpy as np

import os

dota_shop = cv.imread('dota_pinned_items.png')


def window_capture():
    # Define your Monitor
    x = 1520
    y = 707
    w = 400
    h = 70

    with mss.mss() as sct:
        # Part of the screen to capture
        monitor = {"left": x, "top": y, "width": w, "height": h}
        img = sct.grab(monitor)
        img = np.array(img)
    return img


def detect_shop():
    shop_on_is_renamed = False
    shop_off_is_renamed = False

    while "Screen capturing":
        # Define Time
        last_time = time.time()

        # Get the img
        screenshot = window_capture()

        # Display the picture
        cv.imshow('Computer Vision', screenshot)

        # See if the template matches
        cv.imwrite('snapshot.jpg', screenshot)
        snapshot = cv.imread('snapshot.jpg')
        result = cv.matchTemplate(snapshot, dota_shop, cv.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

        print(f'FPS {(1 / (time.time() - last_time))}')

        # Press "q" to quit
        if cv.waitKey(1) == ord("q"):
            cv.destroyAllWindows()
            break

        if max_val >= 0.25:
            if shop_on_is_renamed:
                os.rename('watched_folder_shop_on/rename.txt', 'watched_folder_shop_on/rename.txt')
                shop_on_is_renamed = False
            else:
                os.rename('watched_folder_shop_on/rename.txt', 'watched_folder_shop_on/rename.txt')
                shop_on_is_renamed = True
        else:
            if shop_off_is_renamed:
                os.rename('watched_folder_shop_off/rename.txt', 'watched_folder_shop_off/rename.txt')
                shop_off_is_renamed = False
            else:
                os.rename('watched_folder_shop_off/rename.txt', 'watched_folder_shop_off/rename.txt')
                shop_off_is_renamed = True


detect_shop()
