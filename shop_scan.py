import cv2 as cv
import time
import mss
import numpy as np

import test

dota_shop = cv.imread('dota_shop.png')


def window_capture():
    # Define your Monitor
    x = 1520
    y = 50
    w = 400
    h = 730

    with mss.mss() as sct:
        # Part of the screen to capture
        monitor = {"left": x, "top": y, "width": w, "height": h}
        img = sct.grab(monitor)
        img = np.array(img)
        cv.rectangle(img, (1300, 880), (1920, 30), (0, 255, 0), cv.LINE_4)
    return img


def detect_shop() -> object:
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
            print('match found')
            f = open("watched_folders/shop_on/watched_txt.txt", 'w')
            f.write("this txt being modified triggers a Streamer.bot action !")
            f.close()
        else:
            print('match not found')
            f = open("watched_folders/shop_off/watched_txt.txt", 'w')
            f.write("this txt being modified triggers a Streamer.bot action !")
            f.close()


detect_shop()
