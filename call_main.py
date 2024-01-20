import main
import keyboard


def start_main():
    main.shop_scan()
    print("Function started!")


# Set the hotkey (e.g., Ctrl+Alt+S)
keyboard.add_hotkey('Ctrl+Alt+Shift+P', start_main)

try:
    while True:
        pass
except KeyboardInterrupt:
    # Handle KeyboardInterrupt (Ctrl+C)
    print("Program interrupted by user.")
finally:
    # Clean up or perform any necessary tasks before exiting
    keyboard.remove_all_hotkeys()
