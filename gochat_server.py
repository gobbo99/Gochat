import os
import time
import json
import sys
import socket
from threading import Thread
import logging
import configparser

env_port = os.environ.get('CHATROOM_PORT', 12345)
host = os.environ.get('CHATROOM_HOST', '0.0.0.0')
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.FileHandler('/var/log/gochat/server.log'))
ips = []


ENCODER = 'utf-8'

try:
    port = int(env_port)
except ValueError as e:
    print(f'Env variable CHATROOM_PORT is invalid! {str(e)}')

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client_nick_map = {}   # socket.socket: 'nick'
banned_ip = []
threads_list = []


"""
Stream oriented connection socket.SOCK_STREAM
Using global server(socket object, representing host server)
Loading host ip addr and port number from config file.
Setting server for listen after we bind host address with listening port

Binding port with ip address so there is a connection link, so we can call listen() 
listen(n) - makes it listening socket, n - maximum number of queued connections
accept() - returns representatoin of client socket and client address info -> socket, ipaddr
close()
port - Just a number representing virtual port for different network services / application process on TCP/IP
socket - uniquely identifies endpoint, it's endpoint between /two/way/ communication between two applications on the net 
"""


def start_tcp_server():
    global host
    global port
    global server
    server.bind((host, port))
    server.listen()


def handle_client_conn(client: socket):
    global client_nick_map
    nick = client_nick_map.get(client, '')
    broadcast_system_msgs(f'{nick} has joined the chat!')
    while True:
        try:
            msg = client.recv(1024).decode(ENCODER)
            broadcast(msg, nick)
        except BrokenPipeError as e:
            broadcast_msg = f'{nick} has been terminated!'
            client_nick_map.pop(client)
            print(f"Connection closed by client: {nick}\n{client}")
            logging.info(f'Connection terminated for {nick}\n Error: {str(e)}')
            broadcast_system_msgs(broadcast_msg)
            break
        except Exception as e:
            broadcast_msg = f'{nick} has been terminated!'
            client_nick_map.pop(client)
            print(f"Connection closed for client: {nick}\n{client}")
            logging.info(f'Connection terminated for {nick}\n Error: {str(e)}')
            broadcast_system_msgs(broadcast_msg)
            break


def broadcast(msg, nick):
    data = {'nick': nick, 'msg': msg}
    serialized_data = json.dumps(data).encode(ENCODER)
    for client in client_nick_map:
        client.send(serialized_data)


def broadcast_system_msgs(msg):
    for client in client_nick_map:
        client.send(msg.encode(ENCODER))


"""
Blocking function that waits incoming tcp connection, waiting for connection, returns socket object, ip addr info
"""


def receive_connection():
    global client_nick_map
    global ips
    while True:
        client, address = server.accept()
        try:
            if address[0] == '0.0.0.0':
                logging.debug(f'New connection from {address[0]} discounted!')
                continue
            if ips.count(address[0]) > 3:
                logging.debug(f'New connection from {address[0]} discounted!')
                continue
            client.send('NICK'.encode(ENCODER))
            nick = client.recv(1024).decode(ENCODER)
            client_nick_map[client] = nick
            print(f'New connection: {address}\n########################\nNickname: {nick}\n')
            logging.info(f'New connection: {address} | Nickname: {nick}\n')
            ips.append(address[0])
        except Exception as e:
            ips.pop(address[0])
            logging.error('err:' + str(e))
            continue

        t = Thread(target=handle_client_conn, args=(client,))
        t.start()
        threads_list.append(t)


if __name__ == '__main__':
    start_tcp_server()
    try:
        print('Server is listening...')
        receive_connection()
    except Exception as e:
        print(e)
        threads_list.clear()
        sys.exit(1)
