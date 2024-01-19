from websockets.sync.client import connect
import re

get_actions_json = """
{
  "request": "GetActions",
  "id": "<id>"
}
"""
# Only needs either ID or name to be provided. ID will stay the same after renames.
shop_hidden_json = """
{
  "request": "DoAction",
  "action": {
    "id": "6cba2fc5-205f-4e51-9b35-7b0d5331cc7b",
    "name": "Shop Hidden"
  },
  "args": {
    "key": "value",
  },
  "id": "<id>"
}
"""

shop_shown_json = """
{
  "request": "DoAction",
  "action": {
    "id": "e314b940-fe9f-4f30-8108-891826a98a06",
    "name": "Shop Shown"
  },
  "args": {
    "key": "value",
  },
  "id": "<id>"
}
"""

ws = connect("ws://127.0.0.1:8080/")
print("connected to websocket:", ws, "\n")


def get_actions():  # gets a list of all my Streamer.bot actions
    print("getting actions list...")
    ws.send(get_actions_json)
    message = ws.recv()
    action_list = pretty_action_list(message)
    print(action_list, "\n")


def go_to_shop_hidden():
    ws.send(shop_hidden_json)
    message = ws.recv()
    print(f"Received: {message}\n")


def go_to_shop_shown():
    ws.send(shop_shown_json)
    message = ws.recv()
    print(f"Received: {message}\n")


def pretty_action_list(msg):  # make the list more readable by adding new lines
    pattern = "{"
    msg = re.sub(pattern, "\n{", msg)
    pattern = "}],"
    msg = re.sub(pattern, "}],\n", msg)
    return msg


