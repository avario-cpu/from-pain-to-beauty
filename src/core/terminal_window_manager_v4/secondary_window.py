import sys
import tkinter as tk

# Get the title from the command-line arguments
title = sys.argv[1] if len(sys.argv) > 1 else "Default Title"

# Get the size from the command-line arguments and convert it back to a tuple
width = sys.argv[2] if len(sys.argv) > 2 else "200"
height = sys.argv[3] if len(sys.argv) > 3 else "200"

root = tk.Tk()
root.title(title)
root.geometry(f"{width}x{height}")  # Set the window size
root.mainloop()
