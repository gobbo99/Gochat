import time
import json
import sys
import os
import curses
import datetime
import socket
import argparse
from threading import Thread, Lock
import logging

ENCODER = 'utf-8'
try:
    HOST, PORT = os.environ.get('GOCHAT_CLIENT').split(':')
    PORT = int(PORT)
except:
    parser = argparse.ArgumentParser("Define host ip and port.")
    parser.add_argument('-a', '--ip', type=str, help='Host IP address')
    parser.add_argument('-p', '--port', type=int, help='Port number')
    args = parser.parse_args()
    HOST = args.ip
    PORT = args.port


class ChatClient:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __init__(self, stdscr, nick):
        self.win = stdscr
        self.nickname = nick
        self.max_history = 100
        self.msgs = []
        self.lock = Lock()
        self.rows = None
        self.cols = None
        self.max_rows = 100
        self.max_cols = 100
        self.max_msgs = curses.LINES - 2

    def listen_service(self):
        self.client.connect((HOST, PORT))
        while True:
            try:
                rec_data = self.client.recv(1024).decode(ENCODER)
                if not rec_data:
                    break
                if is_json(rec_data):
                    data = json.loads(rec_data)
                    msg = data['msg']
                    sender_nick = data['nick']
                    time_sent = datetime.datetime.now().time()
                    formatted_msg = f"({time_sent.strftime('%H:%M')})[{sender_nick}]: {msg}"
                    with self.lock:
                        self.msgs.append(formatted_msg)
                elif rec_data == 'NICK':
                    while True:
                        retry = 10
                        try:
                            self.client.send(self.nickname.encode(ENCODER))
                            break
                        except BlockingIOError:
                            if retry == 0:
                                sys.exit(1)
                            retry -= 1
                            time.sleep(0.5)
                            continue
                else:
                    with self.lock:
                        self.msgs.append(rec_data)

                self.render_updates()

            except Exception as e:
                print(f'An error occurred: {e}')
                sys.exit(1)
                self.client.close()
                break
            time.sleep(0.03)

    def render_updates(self):
        curses.curs_set(0)
        new_rows, new_cols = self.win.getmaxyx()
        if new_cols != self.cols or new_rows != self.rows:
            self.cols = new_cols
            self.rows = new_rows
            self.max_msgs = self.rows - 2

        """
        Messages stord in formats:
        1. (time)[nick]: message
        2. (time)system_message
        + 1 for index value because string[x:y] y is exclusive and y is ')' or ']' that we want to format
        """
        for i, message in enumerate(self.msgs[-self.max_msgs:]):
            if message.find('[') != -1:
                time_sep = message.find(")") + 1
                index_sep = message.find("]:") + 1
                time_str = message[:time_sep]
                info_str = message[time_sep:index_sep]
                msg_str = message[index_sep:]
                if self.nickname in message:
                    self.win.addstr(i, 0, time_str.ljust(self.cols-1), curses.color_pair(3) | curses.A_NORMAL)
                    self.win.addstr(i, len(time_str), info_str.ljust(self.cols-1), curses.color_pair(1) | curses.A_BOLD)
                    self.win.addstr(i, len(info_str+time_str), msg_str.ljust(self.cols-1), curses.color_pair(2) | curses.A_NORMAL)
                else:
                    self.win.addstr(i, 0, time_str.ljust(self.cols-1), curses.color_pair(3) | curses.A_NORMAL)
                    self.win.addstr(i, len(time_str), info_str.ljust(self.cols-1), curses.color_pair(2) | curses.A_NORMAL)
                    self.win.addstr(i, len(info_str+time_str), msg_str.ljust(self.cols-1), curses.color_pair(2) | curses.A_NORMAL)
            else:
                self.win.addstr(i, 0, message.ljust(self.cols-1), curses.color_pair(3) | curses.A_NORMAL)

        # Move the cursor to the last row where the user prompt is
        curses.curs_set(1)
        self.win.move(self.rows - 1, len(f'[{self.nickname}]: '))
        self.win.refresh()

    def get_input(self):
        prompt = f'[{self.nickname}]: '
        while True:
            try:
                filler = ' ' * (self.cols - 1)
                self.win.addstr(curses.LINES - 1, 0, filler, curses.color_pair(5))
                self.win.addstr(curses.LINES - 1, 0, prompt, curses.color_pair(4) | curses.A_BOLD)
                user_input = ""
                curses.echo()
                key = self.win.getch()
                while key != 10:  # 10 is the ASCII code for Enter
                    if key == curses.KEY_BACKSPACE or key == 127:  # Handle backspace
                        user_input = user_input[:-1]
                        self.win.addch(curses.LINES - 1, len(prompt) + len(user_input), ' ', curses.color_pair(5))
                        self.win.move(curses.LINES - 1, len(prompt) + len(user_input))
                    elif 32 <= key <= 126:  # Accept printable ASCII characters
                        user_input += chr(key)
                        self.win.addch(curses.LINES - 1, len(prompt) + len(user_input) - 1, chr(key),
                                       curses.color_pair(5))
                    key = self.win.getch()
                if user_input.lower().strip() == '/exit':
                    self.win.addstr(curses.LINES - 1, 0, "Type 'yes' to confirm exit: ")
                    inp = self.win.getstr(curses.LINES - 1, len("Type 'yes' to confirm exit: "))
                    if inp.decode(ENCODER).lower().strip() == "yes":
                        break
                    else:
                        continue
                self.client.send(user_input.encode(ENCODER))
                # Clear the input line
                self.win.clrtoeol()
                curses.noecho()
            except Exception as e:
                break


def is_json(s):
    try:
        json.loads(s)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def start_client(stdscr, nick=None):
    chat_client = ChatClient(stdscr, nick)
    chat_client.rows, chat_client.cols = stdscr.getmaxyx()
    set_curses(stdscr)
    t1 = Thread(target=chat_client.listen_service)
    t2 = Thread(target=chat_client.get_input)
    t1.start()
    t2.start()
    t2.join()


def set_curses(curser_screen):
    curses.start_color()
    curses.init_pair(1, 184, 52)  # self nickname color
    curses.init_pair(2, 195, 52)  # txt color
    curses.init_pair(3, 81, 52)  # system msgs
    curses.init_pair(4, 184, 235)  # self nickname color
    curses.init_pair(5, 195, 235)  # txt color
    curser_screen.bkgd(' ', curses.color_pair(2))


if __name__ == '__main__':
    global nick
    nick = input("Enter your nickname: ")
    curses.wrapper(start_client, nick=nick)
