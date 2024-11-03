import socket
import sys
import threading


def udp_agent(address : str, port : str):
    s : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        message : str = "adoro redes :):)"
        s.sendto(message.encode("utf-8"), (address, int(port)))
    finally:
         s.close()

def tcp_agent(address : str, port : str):
    s : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.connect((address, int(port) +1))
        message : str = "odeio redes"
        s.send(message.encode('utf-8')) #passar para bytes a string que vai ser enviada
        message = message+ ", mas tipo, muito"
        s.send(message.encode('utf-8'))
    finally:
        s.close()


def main():
    address, port = sys.argv[1], sys.argv[2]

    threads = [threading.Thread(target=udp_agent, args=(address,port)),
               threading.Thread(target=tcp_agent, args=(address,port))]

    for t in threads:
        t.start()

    for t in threads:
        t.join()
    

if __name__ == "__main__":
        main()