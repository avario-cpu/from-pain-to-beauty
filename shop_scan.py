import cv2 as cv
import time
import mss
import numpy as np

import client

dota_shop_template = cv.imread('dota_pinned_items.png')


def wait():
    # print(f' FPS {(1 / (time.time() - last_time))}')  # commented out, maybe useful maybe not
    time.sleep(0.5)


def window_capture():
    x = 1520
    y = 707
    w = 400
    h = 70

    with mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": w, "height": h}  # screen part to capture
        img = sct.grab(monitor)
        img = np.array(img)
    return img


def detect_shop():
    shop_is_open = False  # True if openCV matches templates

    while "Screen capturing":
        screenshot = window_capture()
        cv.imshow('Computer Vision', screenshot)
        cv.imwrite('snapshot.jpg', screenshot)

        snapshot = cv.imread('snapshot.jpg')
        result = cv.matchTemplate(snapshot, dota_shop_template, cv.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

        if cv.waitKey(1) == ord("q"):
            cv.destroyAllWindows()
            break

        if max_val >= 0.3:
            if shop_is_open:
                print('shop was already open, continue.')
                wait()  # slow down the script, no need to check 40 times per seconds.
                continue
            else:  # if shop wasn't open last check
                shop_is_open = True
                print('\n\nshop just opened, change scene!\n\n')
                client.go_to_shop_shown()
                wait()
        else:  # if there is no successful match detected with openCV...
            if shop_is_open:  # ...but the shop was open during the last check
                shop_is_open = False
                print('\n\nshop just closed, change scene!\n\n')
                client.go_to_shop_hidden()
                wait()
            else:  # if shop was already closed
                print('Shop was already closed, continue.')
                wait()
                continue


detect_shop()
client.client.close()
