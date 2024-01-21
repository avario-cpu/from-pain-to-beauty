import pygetwindow as gw
import time


def move_window(window_title, new_position):
    # Get the window by title
    window = gw.getWindowsWithTitle(window_title)

    if window:
        window = window[0]

        # Move the window to the new position
        window.moveTo(new_position[0], new_position[1])
        print(f"Moved {window_title} to ({new_position[0]}, {new_position[1]})")
    else:
        print(f"Window with title '{window_title}' not found.")


if __name__ == "__main__":
    # Replace 'Command Prompt' with the title of your terminal window
    terminal_title = 'Command Prompt'

    # Set the new position (x, y)
    new_position = (100, 100)

    # Move the terminal window to the new position
    move_window(terminal_title, new_position)

    # Add a delay to see the change
    time.sleep(2)
