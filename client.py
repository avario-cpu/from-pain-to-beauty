from websockets.sync.client import connect
import re

print("establishing connection...")
ws = connect("ws://127.0.0.1:8080/")
print("connected to websocket:", ws)


def get_actions():  # gets a list of all my Streamer.bot actions
    print("getting actions list...")
    with open("ws_requests/get_actions.json", 'r') as file:
        file_contents = file.read()
    ws.send(file_contents)
    message = ws.recv()
    message = make_pretty(message)
    print(f"action list: {message}\n")


def make_pretty(msg):  # makes the list of actions more readable by adding new lines
    pattern = "{"
    msg = re.sub(pattern, "\n{", msg)
    pattern = "}],"
    msg = re.sub(pattern, "}],\n", msg)
    return msg


def toggle_dslr():
    with open("ws_requests/toggle_DSLR.json", 'r') as file:
        file_contents = file.read()
    ws.send(file_contents)
    message = ws.recv()
    print(f"Received: {message}")


get_actions()
