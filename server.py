import socket
import sys
import threading

def udp_server(address : str, port : str):
    #address, port = sys.argv[1], sys.argv[2]       -> acho que aqui não é preciso

    try:
        s : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)        #criar um socket
        s.bind((address,int(port)))

        print(f"Inicializei o servidor de UDP em {address}:{port}") # este f serve para o "address" e o "port" serem tratados como variaveis e nao como texto

        while True:

            message, agent_address = s.recvfrom(1024) #server adormece

            print(f"Recebi uma mensagem do {agent_address}: {message.decode('utf-8')}")
    finally:
        s.close()



def processamento_tcp(connection, agent_address):
    while True:
        message : bytes = connection.recv(1024) #aqui não precisamos de colocar recvfrom porque já temos o ip do agente que aceitamos a ligação

        if message == b'':
            exit()
        print(f"No servidor TCP recebi uma mensagem do {agent_address} com: {message.decode('utf-8')}")


def tcp_server(address : str, port : str):
    s : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:

        s.bind((address, int(port) +1))     #mas podemos usar a mesma no trabalho

        print(f"Inicializei o servidor TCP em {address}:{int(port)+1}")

        s.listen(5)     #é quase sempre 5 man, mas acho que é kinda irrelevante

        while True:
            connection,agent_address = s.accept()

            threading.Thread(target=processamento_tcp, args=(connection,agent_address)).start()
                #não é preciso join porque não é preciso sincronizar o termino das threads todas, não interessa quando esta termina
            print(f"Recebi uma conexão do {agent_address}")

    finally:
        s.close()


def main():
    address, port = sys.argv[1], sys.argv[2]

    threads = [threading.Thread(target=udp_server, args=(address,port)),
               threading.Thread(target=tcp_server, args=(address,port))]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
        main()