import keyboard
import time
import test2

exit_bool = False


def start_function():
    print("Function started!")
    # Add your function logic here


def exit_script():
    print("exit called!")
    global exit_bool
    exit_bool = True


# Set the hotkey (e.g., Ctrl+Alt+F)
keyboard.add_hotkey('Ctrl+Alt+F', start_function)
keyboard.add_hotkey('Ctrl+Alt+;', exit_script)
keyboard.add_hotkey('Ctrl+Alt+/', test2.test_call)


def main():
    while True:
        # Your main program logic goes here
        if exit_bool:
            break
        else:
            time.sleep(1)  # Add a short delay to reduce CPU usage
            print('running')


# if __name__ == '__main__':
main()
