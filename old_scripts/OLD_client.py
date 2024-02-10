from websockets.exceptions import WebSocketException
from websockets.sync.client import connect
import re


# Assuming the 'connect' function used is synchronous as per the import.
# Adjust if using an asynchronous approach with 'websockets.connect'.

def init():
    websocket_url = "ws://127.0.0.1:8080/"
    try:
        print("establishing connection...")
        ws = connect(websocket_url)
        print(f"connection {ws} established")
        return ws
    except WebSocketException as e:
        print(f"WebSocket error: {e}")
    except ConnectionError as e:
        print(f"Connection error: {e}")
    input('Press enter to quit')
    return None


def disconnect(ws):
    try:
        ws.close()
        print(f"disconnected from websocket: {ws}")
    except Exception as e:
        print(f"Error disconnecting: {e}")


def get_actions(ws):
    """Gets a list of all my Streamerbot actions."""
    actions_file_path = "../streamerbot_ws_requests/get_actions.json"
    try:
        print("getting actions list...")
        with open(actions_file_path, 'r') as file:
            ws.send(file.read())
        print(f"action list: {make_pretty(ws.recv())}\n")
    except Exception as e:
        print(f"Error getting actions: {e}")


def make_pretty(msg):
    """Makes the list of actions more readable by adding new lines."""
    msg = re.sub("{", "\n{", msg)
    msg = re.sub("}],", "}],\n", msg)
    return msg


def send_request(ws, json_file_path):
    """Generalizes request sending to avoid repetition."""
    try:
        with open(json_file_path, 'r') as file:
            ws.send(file.read())
        print(f"Received: {ws.recv()}")
    except Exception as e:
        print(f"Error sending request: {e}")


def request_show_dslr(ws):
    send_request(ws, "../streamerbot_ws_requests/dslr_show.json")


def request_hide_dslr(ws):
    send_request(ws, "../streamerbot_ws_requests/dslr_hide.json")


def main():
    ws = init()
    if ws:
        get_actions(ws)


if __name__ == "__main__":
    main()
