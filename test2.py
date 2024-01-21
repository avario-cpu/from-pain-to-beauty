with open("terminal_loc/amount_of_windows", 'r') as f:
    content = f.read()
    new_content = int(content)
    print(content)


with open("terminal_loc/amount_of_windows", 'w') as f:
    new_content = new_content + 1
    f.write(str(new_content))
    print(new_content)


input("any key")

with open("terminal_loc/amount_of_windows", 'r') as f:
    content = f.read()
    new_content = int(content)
    print(content)

with open("terminal_loc/amount_of_windows", 'w') as f:
    new_content = (new_content - 1)
    f.write(str(new_content))
    print(new_content)
