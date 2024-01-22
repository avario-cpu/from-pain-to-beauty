from websockets.sync.client import connect
import re

print("establishing connection...")
ws = connect("ws://127.0.0.1:8080/")


def disconnect():
    ws.close()
    print(f"disconnected from websocket: {ws}")


def get_actions():  # gets a list of all my Streamer.bot actions
    print("getting actions list...")
    with open("ws_requests/get_actions.json", 'r') as file:
        file_contents = file.read()
    ws.send(file_contents)
    message = ws.recv()
    pretty_message = make_pretty(message)
    print(f"action list: {pretty_message}\n")


def make_pretty(msg):  # makes the list of actions more readable by adding new lines
    pattern = "{"
    msg = re.sub(pattern, "\n{", msg)
    pattern = "}],"
    msg = re.sub(pattern, "}],\n", msg)
    return msg


def request_show_dslr():
    with open("ws_requests/show_dslr.json", 'r') as file:
        file_contents = file.read()
    ws.send(file_contents)
    message = ws.recv()
    print(f"Received: {message}")


def request_hide_dslr():
    with open("ws_requests/hide_dslr.json", 'r') as file:
        file_contents = file.read()
    ws.send(file_contents)
    message = ws.recv()
    print(f"Received: {message}")


get_actions()
