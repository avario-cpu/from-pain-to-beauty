break_shop_scan_loop = False


def stop_the_shop_scan():
    print('stopping scan')
    global break_shop_scan_loop
    break_shop_scan_loop = True
