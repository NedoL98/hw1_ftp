import os
from server import run_server
from tests import run_tests

def main():
    mode = os.environ["HW1_MODE"]
    if mode == "server":
        run_server()
    elif mode == "tests":
        run_tests()

if __name__ == "__main__":
    main()