import socket
import os

BUF_SIZE = 1024
should_drop = False

def is_accessible(root_directory, path_to_file):
    return os.path.realpath(path_to_file).startswith(os.path.realpath(root_directory))

def get_abs_path(current_directory, relative_filepath):
    if relative_filepath.startswith("/"):
        return relative_filepath
    else:
        return os.path.join(current_directory, relative_filepath)

class ServerData(object):
    def __init__(self):
        self.cmd_socket = None
        self.cmd_conn = None
        self.cmd_addr = None

        self.init_directory = None
        self.current_directory = None

        self.data_sock_init = False
        self.data_addr = None
        self.data_port = None

        self.pasv = False
        self.pasv_data_socket = None
        self.pasv_host = None
        self.pasv_port = None

        self.logged_in = False
        self.username = None
        self.path_to_users = None

        self.represenation_type = "a"
        self.transfer_mode = "b"
        self.file_structure = "f"

        self.debug = False

    def init(self):
        try:
            if os.environ["HW1_DEBUG"] == "1":
                self.debug = True
        except:
            pass

        # explicitly "log in" if no authentication required
        if os.environ["HW1_AUTH_DISABLED"] == "1":
            self.logged_in = True

        self.path_to_users = os.environ["HW1_USERS"]
        self.cmd_socket = socket.socket()
        print(os.environ["HW1_HOST"], int(os.environ["HW1_PORT"]))
        self.cmd_socket.bind((os.environ["HW1_HOST"], int(os.environ["HW1_PORT"])))
        self.cmd_socket.listen()
        self.init_listen()

    def init_listen(self):
        self.cmd_conn, self.cmd_addr = self.cmd_socket.accept()
        self.send_command("220 FTP server ready.")

        self.init_directory = os.environ["HW1_DIRECTORY"]
        self.current_directory = self.init_directory

    def reset_data_conn(self):
        self.data_sock_init = False
        self.pasv = False
        self.pasv_data_socket = None
        self.pasv_host = None
        self.pasv_port = None

    def send_command(self, args):
        try:
            self.cmd_conn.send(str.encode(args.strip() + "\r\n"))
        except:
            should_drop = True

    def user_handler(self, args):
        self.username = args
        if self.username == "anonymous":
            self.send_command("230 Login successful.")
        else:
            self.send_command("331 Please specify the password.")

    def quit_handler(self, args):
        self.send_command("221 Goodbye.")

    def port_handler(self, args):
        tokens = args.split(',')
        if len(tokens) != 6:
            self.send_command("500 Illegal PORT command.")
            return
        for token in tokens:
            try:
                int(token)
            except:
                self.send_command("500 Illegal PORT command.")
                return
            if int(token) < 0 or int(token) > 255:
                self.send_command("500 Illegal PORT command.")
                return
        self.data_addr = ".".join(tokens[:4])
        self.data_port = int(tokens[4]) * 256 + int(tokens[5])
        self.data_sock_init = True
        self.send_command("200 PORT command successful. Consider using PASV.")

    def type_handler(self, args):
        tokens = args.split()
        if tokens[0] == "a":
            self.represenation_type = tokens[0]
            self.send_command("200 Switching to ASCII mode.")
        elif tokens[0] == "i":
            self.represenation_type = tokens[0]
            self.send_command("200 Switching to Binary mode.")
        else:
            self.send_command("500 Unrecognised TYPE command.")

    def mode_handler(self, args):
        if args == "s":
            self.transfer_mode = "s"
            self.send_command("200 Mode set to S.")
        elif args == "b":
            self.transfer_mode = "b"
        elif args == "c":
            self.transfer_mode = "c"
        else:
            self.send_command("504 Bad MODE command.")

    def stru_handler(self, args):
        if args == "f":
            self.file_structure = "f"
            self.send_command("200 Structure set to F.")
        elif args == "r":
            self.file_structure = "r"
        elif args == "p":
            self.file_structure = "p"
        else:
            self.send_command("504 Bad STRU command.")

    def check_sock_init(self):
        if not self.data_sock_init:
            self.send_command("425 Use PORT or PASV first.")
            return False
        return True

    def get_data_transfer_socket(self):
        data_socket = socket.socket()
        if self.pasv:
            data_conn, data_addr = self.pasv_data_socket.accept()
            return data_conn
        else:
            try:
                data_socket.connect((self.data_addr, self.data_port))
                return data_socket
            except:
                self.reset_data_conn()
                self.send_command("425 Failed to establish connection.")
                return None

    def get_file_obj(self, rel_filepath, file_open_args):
        filepath = get_abs_path(self.current_directory, rel_filepath)
        file_obj = None
        try:
            if self.debug:
                print("Trying to use " + filepath)
            if not is_accessible(self.init_directory, filepath):
                raise
            file_obj = open(filepath, file_open_args)
            return file_obj
        except:
            if "r" in file_open_args:
                self.send_command("550 Failed to open file.")
            elif "w" in file_open_args or "a" in file_open_args:
                self.send_command("553 Could not create file.")
            self.reset_data_conn()
            return None

    def write_to_file(self, filepath, file_open_args):
        if not self.check_sock_init():
            return

        file_obj = self.get_file_obj(filepath, file_open_args)
        if file_obj is None:
            return
        data_socket = self.get_data_transfer_socket()
        if data_socket is None:
            return
        self.send_command("150 Ok to send data.")
        while True:
            data = data_socket.recv(BUF_SIZE)
            if len(data) == 0:
                break
            file_obj.write(data.decode("ASCII"))
        file_obj.close()
        data_socket.close()
        self.send_command("226 Transfer complete.")
        self.reset_data_conn()

    def retrieve_handler(self, args):
        if not self.check_sock_init():
            return

        file_obj = self.get_file_obj(args, "r")
        if file_obj is None:
            return
        data_socket = self.get_data_transfer_socket()
        if data_socket is None:
            return
        self.send_command("150 Opening data cmd_connection for " + args.strip() + "\n")
        while True:
            data = file_obj.read(BUF_SIZE)
            if len(data) == 0:
                break
            data_socket.send(bytes(data, "ASCII"))
        file_obj.close()
        data_socket.close()
        self.send_command("226 Transfer complete.")
        self.reset_data_conn()

    def store_handler(self, args):
        self.write_to_file(args, "w")

    def noop_handler(self, args):
        self.send_command("200 NOOP ok.")

    def cdup_handler(self, args):
        if self.current_directory != self.init_directory:
            self.current_directory = os.path.dirname(self.current_directory)
        if self.debug:
            print("Current directory: " + self.current_directory)
        self.send_command("250 Directory successfully changed.")

    def cwd_handler(self, args):
        if " " in args:
            self.send_command("550 Failed to change directory.")
            return
        new_abs_path = get_abs_path(self.current_directory, args)
        if is_accessible(self.init_directory, new_abs_path):
            self.current_directory = new_abs_path
            self.send_command("250 Directory successfully changed.")
            if self.debug:
                print("Current directory: " + self.current_directory)
            return
        else:
            self.send_command("550 Failed to change directory.")
            return

    def appe_handler(self, args):
        self.write_to_file(args, "a")

    def dele_handler(self, args):
        filepath = get_abs_path(self.current_directory, args)
        if is_accessible(self.init_directory, filepath) and os.path.isfile(filepath):
            try:
                os.remove(filepath)
                self.send_command("250 Delete operation successful.")
            except:
                self.send_command("550 Delete operation failed.")
        else:
            self.send_command("550 Delete operation failed.")

    def rmdir_handler(self, args):
        dirpath = get_abs_path(self.current_directory, args)
        if is_accessible(self.init_directory, dirpath) and os.path.isdir(dirpath):
            try:
                os.remove(dirpath)
                self.send_command("250 Remove directory operation successful.")
            except:
                self.send_command("550 Remove directory operation failed.")
        else:
            self.send_command("550 Remove directory operation failed.")

    def mkdir_handler(self, args):
        dirpath = get_abs_path(self.current_directory, args)
        if is_accessible(self.init_directory, dirpath):
            try:
                os.mkdir(dirpath)
                self.send_command("257 " + dirpath + " created")
            except:
                self.send_command("550 Create directory operation failed.")
        else:
            self.send_command("550 Create directory operation failed.")

    def nlst_handler(self, args):
        if not self.check_sock_init():
            return
        data_socket = self.get_data_transfer_socket()
        if data_socket is None:
            return

        self.send_command("150 Here comes the directory listing.")
        for file in os.listdir(self.current_directory):
            data_socket.send(bytes(file + "\n", "ASCII"))
        data_socket.close()
        self.send_command("226 Directory send OK.")
        self.reset_data_conn()

    def pasv_handler(self, args):
        self.pasv_data_socket = socket.socket()
        self.pasv_data_socket.bind((os.environ["HW1_HOST"], 0))
        self.pasv_data_socket.listen()
        self.pasv_host, self.pasv_port = self.pasv_data_socket.getsockname()

        pasv_host_str = str(self.pasv_host).replace(".", ",")
        pasv_port_str = str(int(self.pasv_port / 256)) + "," + str(self.pasv_port % 256)
        address_str = pasv_host_str + "," + pasv_port_str

        self.send_command("227 Entering Passive Mode (" + address_str + ").")
        self.pasv = True
        self.data_sock_init = True

    def pass_handler(self, args):
        if self.username is None:
            self.send_command("503 Login with USER first.")
        elif self.logged_in:
            self.send_command("230 Already logged in.")
        else:
            found = False
            with open(self.path_to_users, "r") as users:
                for line in users.readlines():
                    tokens = line.strip().split("\t")
                    assert(len(tokens) == 2)
                    if tokens[0] == self.username and tokens[1] == args:
                        found = True
                        break
            if not found:
                self.username = None
                self.send_command("530 Login incorrect.")
            else:
                self.logged_in = True
                self.send_command("230 Login successful.")

    def unknown_handler(self, args):
        self.send_command("500 Unknown command.")

    def serve(self):
        global should_drop
        while True:
            data = self.cmd_conn.recv(BUF_SIZE)
            args = data.decode("ASCII").lower().strip().split(" ", 1)
            if len(args) < 1:
                continue
            if args == [""]:
                break
            command = args[0]
            if len(args) == 1:
                args = ""
            else:
                args = args[1]

            if not self.logged_in and command != "user" and command != "pass":
               self.send_command("530 Please login with USER and PASS.")
               continue

            if command == "user":
                self.user_handler(args)
            elif command == "quit":
                self.quit_handler(args)
                break
            elif command == "port":
                self.port_handler(args)
            elif command == "type":
                self.type_handler(args)
            elif command == "mode":
                self.mode_handler(args)
            elif command == "stru":
                self.stru_handler(args)
            elif command == "retr":
                self.retrieve_handler(args)
            elif command == "stor":
                self.store_handler(args)
            elif command == "noop":
                self.noop_handler(args)
            elif command == "cdup":
                self.cdup_handler(args)
            elif command == "cwd":
                self.cwd_handler(args)
            elif command == "appe":
                self.appe_handler(args)
            elif command == "dele":
                self.dele_handler(args)
            elif command == "rmd":
                self.rmdir_handler(args)
            elif command == "mkd":
                self.mkdir_handler(args)
            elif command == "nlst":
                self.nlst_handler(args)
            elif command == "pasv":
                self.pasv_handler(args)
            elif command == "pass":
                self.pass_handler(args)
            else:
                self.unknown_handler(args)
            if should_drop:
                break

        self.cmd_conn.close()

def run_server():
    server = ServerData()
    server.init()
    while True:
        server.serve()
        server.init_listen()
