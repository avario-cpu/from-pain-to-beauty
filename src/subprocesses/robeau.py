import socket
import subprocess

from src.core import constants as const
from src.scripts import google_stt

HOST = 'localhost'  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)


def launch_stt():
    command = (f'start cmd /k "cd /d {const.PROJECT_DIR_PATH} '
               f'&& set PYTHONPATH={const.PYTHONPATH} '
               f'&& .\\venv\\Scripts\\activate '
               f'&& cd {const.SCRIPTS_DIR_PATH} '
               f'&& py {google_stt.SCRIPT_NAME}.py"')

    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    return process


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print("Server is listening...")
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                message = data.decode('utf-8').strip()
                print(f"Received: {message}")


if __name__ == "__main__":
    main()
