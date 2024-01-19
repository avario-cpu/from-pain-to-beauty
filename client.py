from websockets.sync.client import connect
import re

get_actions_json = """
{
  "request": "GetActions",
  "id": "<id>"
}
"""
# Both using either the action name or id works, one can be left empty if the other is provided
do_action_json = """
{
  "request": "DoAction",
  "action": {
    "id": "74041930-bd70-41e7-a9c8-e80c74384731",
    "name": ""
  },
  "args": {
    "key": "value",
  },
  "id": "<id>"
}
"""


def streamer_bot_connect():
    websocket = connect("ws://127.0.0.1:8080/")


def get_action():
    with connect("ws://127.0.0.1:8080/") as websocket:
        websocket.send(get_actions_json)
        message = websocket.recv()
        pattern = "},{"
        message = re.sub(pattern, "},\n{", message)  # make it go at newline for readability
        print(f"received:{message}\n")


def do_action():
    with connect("ws://127.0.0.1:8080/") as websocket:
        websocket.send(do_action_json)
        message = websocket.recv()
        print(f"Received: {message}\n")


get_action()
do_action()
