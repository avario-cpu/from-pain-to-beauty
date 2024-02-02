import websockets
from websockets.sync.client import connect
import re


def init():
    try:
        print("establishing connection...")
        ws = connect("ws://127.0.0.1:8080/")
        print(f"connection {ws} established")
        return ws
    except websockets.WebSocketException as e:
        print(e)
        input('enter to quit')
    except ConnectionError as e:
        print(e)
        return None


def disconnect(ws):
    ws.close()
    print(f"disconnected from websocket: {ws}")


def get_actions(ws):
    """gets a list of all my Streamerbot actions"""
    print("getting actions list...")
    with open("../streamerbot_ws_requests/get_actions.json", 'r') as file:
        ws.send(file.read())
    print(f"action list: {make_pretty(ws.recv())}\n")


def make_pretty(msg):
    """makes the list of actions more readable by adding new lines"""
    pattern = "{"
    msg = re.sub(pattern, "\n{", msg)
    pattern = "}],"
    msg = re.sub(pattern, "}],\n", msg)
    return msg


def request_show_dslr(ws):
    with open("../streamerbot_ws_requests/show_dslr.json", 'r') as file:
        ws.send(file.read())
    print(f"Received: {ws.recv()}")


def request_hide_dslr(ws):
    with open("../streamerbot_ws_requests/hide_dslr.json", 'r') as file:
        ws.send(file.read())
    print(f"Received: {ws.recv()}")


def main():
    ws = init()
    get_actions(ws)


if __name__ == "__main__":
    main()
