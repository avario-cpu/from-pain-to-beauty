import client
import shop_scan


def main():
    client.get_actions()
    shop_scan.detect_shop()
    print("closing client")
    client.ws.close()
    pass


# if __name__ == '__main__':
    # main()
