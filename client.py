from websockets.sync.client import connect
import re


get_actions_json = """
{
  "request": "GetActions",
  "id": "<id>"
}
"""
# Both using either the action name or id works, one can be left empty if the other is provided
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


def get_actions():
    ws.send(get_actions_json)
    message = ws.recv()
    pattern = "},{"
    message = re.sub(pattern, "},\n{", message)  # make it go at newline for readability
    print(f"received:{message}\n")


def go_to_shop_hidden():
    ws.send(shop_hidden_json)
    message = ws.recv()
    print(f"Received: {message}\n")


def go_to_shop_shown():
    ws.send(shop_shown_json)
    message = ws.recv()
    print(f"Received: {message}\n")


get_actions()
