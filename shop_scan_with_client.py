import cv2 as cv
import time
import mss
import numpy as np

import os

dota_shop_template = cv.imread('dota_pinned_items.png')


def wait():
    # print(f'FPS {(1 / (time.time() - last_time))}')  # commented out, maybe useful maybe not
    time.sleep(1)


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
    shop_is_open = False  # True if openCV matches templates

    if os.listdir('watched_folder_shop_hidden')[0] == 'renamed.txt':
        hidden_shop_txt_is_renamed = True  # weird variable, ik but necessary
    else:
        hidden_shop_txt_is_renamed = False

    if os.listdir('watched_folder_shop_shown')[0] == 'renamed.txt':
        shown_shop_txt_is_renamed = True
    else:
        shown_shop_txt_is_renamed = False

    while "Screen capturing":
        screenshot = window_capture()

        # Display the picture
        cv.imshow('Computer Vision', screenshot)

        # See if the template matches
        cv.imwrite('snapshot.jpg', screenshot)
        snapshot = cv.imread('snapshot.jpg')
        result = cv.matchTemplate(snapshot, dota_shop_template, cv.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

        # Press "q" to quit
        if cv.waitKey(1) == ord("q"):
            cv.destroyAllWindows()
            break

        if max_val >= 0.3:
            if shop_is_open:
                print('shop was already open, continue.')
                wait()
                continue
            else:
                shop_is_open = True  # if shop wasn't open last check
                print('\n\nshop just opened, renaming file\n\n')
                if shown_shop_txt_is_renamed:
                    os.rename('watched_folder_shop_shown/renamed.txt', 'watched_folder_shop_shown/rename.txt')
                    shown_shop_txt_is_renamed = False
                    wait()
                else:
                    os.rename('watched_folder_shop_shown/rename.txt', 'watched_folder_shop_shown/renamed.txt')
                    shown_shop_txt_is_renamed = True
                    wait()

        else:  # if no successful match with openCV = shop is closed
            if shop_is_open:  # if shop was open last check
                shop_is_open = False  # change the state
                print('\n\nshop just closed, renaming file\n\n')
                if hidden_shop_txt_is_renamed:
                    os.rename('watched_folder_shop_hidden/renamed.txt', 'watched_folder_shop_hidden/rename.txt')
                    hidden_shop_txt_is_renamed = False
                    wait()
                else:
                    os.rename('watched_folder_shop_hidden/rename.txt', 'watched_folder_shop_hidden/renamed.txt')
                    hidden_shop_txt_is_renamed = True
                    wait()
            else:  # if shop was already closed
                print('Shop was already closed, continue')
                wait()
                continue


detect_shop()
