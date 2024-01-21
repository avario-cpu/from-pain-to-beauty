import cv2 as cv
import numpy as np
import time
import mss
import client
import os
import threading

dota_shop_template = cv.imread('dota_shop_top_right.jpg')  # image used for template matching the Dota2 shop UI
stop_event = threading.Event()


def stop_detect_shop():
    stop_event.set()
    print('stopped shop_scan thread')
    module_thread.join()


# def start_scan():
#     module_thread.start()


def wait():  # used to slow down the script.
    time.sleep(0.1)
    pass


def window_capture():
    x = 1883
    y = 50
    w = 37
    h = 35

    with mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": w, "height": h}  # screen part to capture
        img = sct.grab(monitor)
        img = np.array(img)
    return img


def detect_shop():
    shop_is_open = False

    while not stop_event.is_set():

        screenshot = window_capture()
        cv.imshow('Computer Vision', screenshot)
        cv.imwrite('snapshot.jpg', screenshot)

        snapshot = cv.imread('snapshot.jpg')  # last scanned frame of my screen
        result = cv.matchTemplate(snapshot, dota_shop_template, cv.TM_SQDIFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

        if cv.waitKey(1) == ord("q"):  # if Q is pressed while having openCV window on focus
            break

        print(max_val)

        if max_val <= 0.4:
            if shop_is_open:
                wait()
                continue
            else:  # if the shop just opened ...
                shop_is_open = True
                client.hide_dslr()  # ...send a request to the Websocket server to trigger a Streamer.bot Action
                wait()
        else:
            if shop_is_open:  # if the shop just closed
                shop_is_open = False
                client.show_dslr()  # ...send a request to the Websocket server to trigger a Streamer.bot Action
                wait()
            else:
                wait()
                continue

    cv.destroyAllWindows()


module_thread = threading.Thread(target=detect_shop)
