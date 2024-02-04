import asyncio
import atexit
import time

import denied_slots_db_handler as denied_sdh
import shop_watcher
import single_instance
import slots_db_handler as sdh
import terminal_window_manager_v3 as twm_v3


def exit_countdown():
    """Give a bit of time to read terminal exit statements"""
    for seconds in reversed(range(1, 6)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    exit()


async def main():
    """If there are no single instance lock file, start the Dota2 shop_watcher
     module. At launch, reposition immediately the terminal providing feedback
    regarding its execution. Shortly after, reposition the secondary window
    which the module spawns. This is all done in an asynchronous way thanks
    to a database providing information used for the window positions"""
    script_name = "dota2_shop_watcher"

    if single_instance.lock_exists():
        slot = twm_v3.handle_window(twm_v3.WindowType.DENIED_SCRIPT,
                                    script_name)
        atexit.register(denied_sdh.free_slot, slot)
        print("\n>>> Lock file is present: exiting... <<<")
    else:
        slot = twm_v3.handle_window(twm_v3.WindowType.ACCEPTED_SCRIPT,
                                    script_name,
                                    shop_watcher.SECONDARY_WINDOW_NAMES)

        single_instance.create_lock_file()
        atexit.register(single_instance.remove_lock)
        atexit.register(sdh.free_slot_named, script_name)

        shop_watcher.mute_main_loop_print_feedback.set()
        task = asyncio.create_task(shop_watcher.main())
        await shop_watcher.secondary_windows_have_spawned.wait()
        twm_v3.adjust_secondary_windows(slot,
                                        shop_watcher.SECONDARY_WINDOW_NAMES)

        shop_watcher.mute_main_loop_print_feedback.clear()
        await task


if __name__ == "__main__":
    asyncio.run(main())
    input('enter to q')
