from websockets.sync.client import connect
import re


def init():
    print("establishing connection...")
    ws = connect("ws://127.0.0.1:8080/")
    return ws


def disconnect(ws):
    ws.close()
    print(f"disconnected from websocket: {ws}")


def get_actions(ws):
    """gets a list of all my Streamerbot actions"""
    print("getting actions list...")
    with open("ws_requests/get_actions.json", 'r') as file:
        file_contents = file.read()
    ws.send(file_contents)
    message = ws.recv()
    pretty_message = make_pretty(message)
    print(f"action list: {pretty_message}\n")


def make_pretty(msg):
    """makes the list of actions more readable by adding new lines"""
    pattern = "{"
    msg = re.sub(pattern, "\n{", msg)
    pattern = "}],"
    msg = re.sub(pattern, "}],\n", msg)
    return msg


def request_show_dslr(ws):
    with open("ws_requests/show_dslr.json", 'r') as file:
        file_contents = file.read()
    ws.send(file_contents)
    message = ws.recv()
    print(f"Received: {message}")


def request_hide_dslr(ws):
    with open("ws_requests/hide_dslr.json", 'r') as file:
        file_contents = file.read()
    ws.send(file_contents)
    message = ws.recv()
    print(f"Received: {message}")


def main():
    ws = init()
    get_actions(ws)


if __name__ == "__main__":
    main()
