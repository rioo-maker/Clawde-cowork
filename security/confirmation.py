def confirm_actions(actions):

    print("⚠️ Actions to execute:")

    for a in actions:
        print(a)

    confirm = input("Confirm ? (y/n): ")

    return confirm.lower() == "y"