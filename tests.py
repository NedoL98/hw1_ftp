import os
import socket
import time
from ftplib import FTP

BUF_SIZE = 1024

def check_cmd(cmd_ret, code):
    if os.environ["HW1_QUIET"] == "0":
        print(cmd_ret, code)
    if not cmd_ret.startswith(code):
        raise Exception("fail")
    return "ok"

def exception_handler(*args):
    try:
        check_cmd(*args)
    except:
        raise

def minimal_tests():
    ftp = FTP()
    # exception_handler(ftp.connect(os.environ["HW1_HOST"], int(os.environ["HW1_PORT"])), "220")
    # exception_handler(ftp.connect("localhost", 21), "220")
    # exception_handler(ftp.connect("209.250.251.55", 8011), "220")
    exception_handler(ftp.connect("209.250.251.55", 8003), "220")
    ftp.putcmd("user ftp_test")
    ftp.getline()
    ftp.putcmd("pass p")
    ftp.getline()
    ftp.putcmd("noop")
    exception_handler(ftp.getline(), "200")
    ftp.putcmd("type kek")
    exception_handler(ftp.getline(), "50")
    ftp.putcmd("type a")
    exception_handler(ftp.getline(), "")

    test_string = "testingtesting\ntestingaaaa\n"
    with open("test_file.txt", "w") as f:
        f.write(test_string)

    # ftp.putcmd("stor test_file.txt")
    # exception_handler(ftp.getline(), "425")

    data_socket = socket.socket()
    data_socket.bind((os.environ["HW1_HOST"], 0))
    data_socket.listen()
    data_host, data_port = data_socket.getsockname()

    port_cmd = "port " + str(data_host).replace(".", ",") + "," + str(int(data_port / 256)) + "," + str(data_port % 256)
    ftp.putcmd(port_cmd)
    print(port_cmd)
    exception_handler(ftp.getline(), "200")
    ftp.putcmd("stor test_file.txt")
    exception_handler(ftp.getline(), "150")

    f_obj = open("test_file.txt", "r")
    conn, addr = data_socket.accept()
    while True:
        data = f_obj.read(BUF_SIZE)
        if len(data) == 0:
            break
        conn.send(bytes(data, "ASCII"))
    conn.close()
    data_socket.close()

    exception_handler(ftp.getline(), "226")
    ftp.putcmd("retr new_test_file.txt")
    exception_handler(ftp.getline(), "425")

    data_socket = socket.socket()
    data_socket.bind((os.environ["HW1_HOST"], 0))
    data_socket.listen()
    data_host, data_port = data_socket.getsockname()
    port_cmd = "port " + str(data_host).replace(".", ",") + "," + str(int(data_port / 256)) + "," + str(data_port % 256)
    ftp.putcmd(port_cmd)
    exception_handler(ftp.getline(), "200")

    ftp.putcmd("retr test_file.txt")
    exception_handler(ftp.getline(), "150")

    recv_data = ""
    conn, addr = data_socket.accept()
    while True:
        data = conn.recv(BUF_SIZE)
        if len(data) == 0:
            break
        recv_data += data.decode()

    if recv_data != test_string:
        raise Exception("fail")

    ftp.quit()
    return "ok"


def run_tests():
    test_type = os.environ["HW1_TEST"]
    quiet = os.environ["HW1_QUIET"]
    ret = None
    if test_type == "minimal":
        ret = minimal_tests()
    if quiet == "1":
        if ret == "ok":
            print("ok")
        else:
            print("fail")