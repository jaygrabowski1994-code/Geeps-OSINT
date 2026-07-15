#!/usr/bin/env python3

import os
from modules.menu import main_menu

def clear():
    os.system("clear")

while True:
    clear()

    choice = main_menu()

    if choice == "0":
        print("\nThanks for using Geeps OSINT Hub.")
        break

    elif choice == "1":
        print("\nUsername Investigation selected.")
        input("\nPress Enter to continue...")

    elif choice == "2":
        print("\nEmail Investigation selected.")
        input("\nPress Enter to continue...")

    elif choice == "3":
        print("\nPhone Investigation selected.")
        input("\nPress Enter to continue...")

    elif choice == "4":
        print("\nDomain Investigation selected.")
        input("\nPress Enter to continue...")

    elif choice == "5":
        print("\nUpdater coming soon.")
        input("\nPress Enter to continue...")

    else:
        print("\nInvalid option.")
        input("\nPress Enter to continue...")

