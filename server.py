#!/usr/bin/env python3
import socket
import os
import selectors
import sys
from types import SimpleNamespace as sn
import logging
import struct
import signal

if len(sys.argv) < 5:
    print('Usage: ./server.py Listening_addr Listening_port Redir_addr Redir_port')
    os._exit(1)

HOST = sys.argv[1]
PORT = int(sys.argv[2])
DB = sys.argv[3]
DB_PORT = int(sys.argv[4])
uds_addr = '/uds_socket'

proxy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy_server.bind((HOST, PORT))
proxy_server.listen()

logging.basicConfig(filename='./connection.log', level=logging.INFO)
wait_response = False
prep_stmt = None


def parse_input(input):
    data = bytes(input)
    data_len = data[0] + (data[1] << 8) + (data[2] << 16)
    if data[4] == 3:  # Query
        try:
            query = input[5:].decode('ascii')
        except:
            return 0
        else:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(uds_addr)
                sock.sendall(query.encode('ascii'))
                recv_data = sock.recv(1024)
                a = struct.unpack('!H', recv_data)[0]
                ans = 1 if a != 0 else 0
            except Exception as msg:
                return 0
            else:
                return ans
            finally:
                sock.close()
    else:
        return 0


def handle_conn(conn, addr):
    sel = selectors.DefaultSelector()
    try:
        db = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        db.connect((DB, DB_PORT))
        db_addr = (DB, DB_PORT)
        if db:
            logging.info("Connected to %s:%s" % (DB, DB_PORT))
            data_W = sn(addr=addr, outb=b'', tag="W")
            data_D = sn(addr=db_addr, outb=b'', tag="D")
            rw = selectors.EVENT_READ | selectors.EVENT_WRITE
            sel.register(conn, rw, data=data_W)
            sel.register(db, rw, data=data_D)
            data_Wout = b''
            data_Dout = b''
            while True:
                events = sel.select(timeout=10)
                for key, mask in events:
                    (data, tag) = serve(key, mask, sel)
                    if data is not None and tag == "W":
                        data_Dout += data
                        data_D = sn(addr=db_addr, outb=data_Dout, tag="D")
                        sel.modify(db, rw, data=data_D)
                    elif data is not None and tag == "D":
                        data_Wout += data
                        data_W = sn(addr=addr, outb=data_Wout, tag="W")
                        sel.modify(conn, rw, data=data_W)
                    elif data is not None and tag == "WS":
                        data_Wout = data
                    elif data is not None and tag == "DS":
                        data_Dout = data
                    elif tag == "C":
                        db.close()
                        sel.unregister(db)
                        logging.info('Closed connection with %s:%s' %
                                     (DB, DB_PORT))
                        os._exit(0)
        else:
            logging.error("Can\'t build connection with db")
            conn.close()
            os._exit(0)

    except Exception as e:
        print(e)


def serve(key, mask, sel):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)
        if recv_data:
            if data.tag == "W":
                prediction = parse_input(recv_data)
                if prediction > 0:
                    test_data = b'\x1f\x00\x00\x01\xff\x28\x04#42000SQL Injection Detected'
                    sock.send(test_data)
                    return (None, data.tag)
            if data.tag == "D" and wait_response:
                parse_input(recv_data)
            return (recv_data, data.tag)
        else:
            sel.unregister(sock)
            sock.close()
            logging.info('Closed connection with %s:%s' %
                         (data.addr[0], data.addr[1]))
            return (None, "C")

    if mask & selectors.EVENT_WRITE:
        if data.outb:
            sent = sock.send(data.outb)
            data.outb = data.outb[sent:]
        return (data.outb, data.tag + "S")


while True:
    conn, addr = proxy_server.accept()
    logging.info("Received connection from %s:%s" % (addr[0], addr[1]))
    child_pid = os.fork()
    if child_pid == 0:  # child process
        handle_conn(conn, addr)
        break
    elif child_pid > 0:   # parent process
        conn.close()
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
