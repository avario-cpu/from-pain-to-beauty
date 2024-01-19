import client
import shop_scan


def main():
    client.establish_connection()
    client.get_actions()
    shop_scan.detect_shop()
    print("closing client.")
    client.ws.close()


main()
