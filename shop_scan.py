import cv2 as cv
import time
import mss
import numpy as np

import client

dota_shop_template = cv.imread('dota_pinned_items.png')  # image to match with for open/closed Dota2 shop detection


def wait():  # to slow down the script so that it doesn't scan too many frames
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
    shop_is_open = False  # will become True when openCV matches templates
    print("scanning for shop...")

    while "Screen capturing":

        screenshot = window_capture()
        cv.imshow('Computer Vision', screenshot)
        cv.imwrite('snapshot.jpg', screenshot)

        snapshot = cv.imread('snapshot.jpg')  # last scanned frame of my screen
        result = cv.matchTemplate(snapshot, dota_shop_template, cv.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

        if cv.waitKey(1) == ord("q"):
            cv.destroyAllWindows()
            break

        if max_val >= 0.3:
            if shop_is_open:  # if shop was already open last check, don't change scene
                print('shop was already open, continue.')
                wait()
                continue
            else:  # if shop wasn't open last check ...
                shop_is_open = True
                print('\nshop just opened, change scene!\n')
                client.go_to_shop_shown()  # ... change OBS scene via Websocket
                wait()
        else:  # if there is no successful match detected with openCV...
            if shop_is_open:  # ...but the shop was open during the last check...
                shop_is_open = False
                print('\nshop just closed, change scene!\n')
                client.go_to_shop_hidden()  # ...change OBS scene via Websocket
                wait()
            else:  # if shop was already closed, don't change scene
                print('Shop was already closed, continue.')
                wait()
                continue


