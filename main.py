from database import create_tables, seed_initial_data
from gui import ParkingApp
import tkinter as tk


if __name__ == "__main__":
    create_tables()

    # Run only once for initial setup
    # seed_initial_data()

    root = tk.Tk()
    app = ParkingApp(root)
    root.mainloop()