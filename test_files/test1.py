import json
import re


def create_dict():
    # here make the dictionary, with (slot{i} : "Title") pairs
    slots = {"slot" + str(i): "FREE" for i in range(1, 10)}
    return slots


def take_slots_in_dict(slots_to_take: list):
    # assign, if free a slot from the dict to a title.
    for slot in slots_to_take:
        if my_dict["slot" + str(slot)] == "FREE":
            my_dict["slot" + str(slot)] = "TAKEN"


def take_first_free_slot_in_dict():
    for slot, status in my_dict.items():
        if status == "FREE":
            my_dict[slot] = "TAKEN"
            print(slot, "was the first open slot available")
            return slot


def free_slots_in_dict(slots_to_free: list):
    # take a slot from the dictionary and free it up.
    for slot in slots_to_free:
        if my_dict["slot" + str(slot)] == "TAKEN":
            my_dict["slot" + str(slot)] = "FREE"


def simulate_cmd_disappear(slot_to_free):
    my_dict[slot_to_free] = "FREE"
    print(my_dict)


def simulate_cmd_reposition():
    slot_taken = take_first_free_slot_in_dict()
    slot_taken_number = re.sub(r'\D', "", slot_taken)  # remove non digit characters from the slot key
    print(slot_taken_number)
    slot_taken_number = int(slot_taken_number)

    if slot_taken_number in [1, 2, 3]:
        print("slot occupied will be in 1st column")
    elif slot_taken_number in [4, 5, 6]:
        print("slot occupied will be in 2nd column")
    elif slot_taken_number in [7, 8, 9]:
        print("slot occupied will be in 3rd column")

    print(my_dict)

    input("press Enter to free slot")

    simulate_cmd_disappear(slot_taken)


def write_dict():
    with open("test_dict.json", "w") as file:
        json.dump(my_dict, file)


my_dict = create_dict()
# take_slots_in_dict([1, 2, 3, ])
# free_slots_in_dict([])
# simulate_cmd_reposition()
# write_dict()
