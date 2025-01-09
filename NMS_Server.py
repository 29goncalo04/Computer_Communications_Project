import socket
import sys
import threading
import json

from Parser import *
from Menu import *
from Message_Sending import *
from Output import *


def processamento_udp(message, agent_address, s : socket.socket, tarefas_sem_ack):
    message_bits = ''.join(format(byte, '08b') for byte in message)  # garante que cada byte seja representado como uma sequência de 8 caracteres
    id_router = int(message_bits[0:8], 2)  # converte os bits do id_router para um valor inteiro
    msg_type = int(message_bits[8:11], 2)  # converte os bits do msg_type para um valor inteiro
    if (msg_type == 0):  # está a receber um pedido de registo
        threading.Thread(target = send_ack_to_agent, args = (0, s, agent_address, tarefas_sem_ack)).start()
        tarefas_sem_ack.append(0)
    elif (msg_type == 1):  # está a receber um ack do agente
        n_seq = int(message_bits[11:27], 2)  # converte os bits do n_seq para um valor inteiro
        if n_seq == 1:  # o server pode começar a enviar as tarefas
            if 0 in tarefas_sem_ack:
                tarefas_sem_ack.remove(0)
            tasks = ler_ficheiro_json(f"{id_router}.json")
            nr_tasks = len(tasks)
            current_task = 0
            while current_task < nr_tasks:
                task_for_client = json.dumps(tasks[current_task])
                nr_sequencia = int(json.loads(task_for_client)["task_id"])+1  # o número de sequência corresponde ao task_id + 1
                threading.Thread(target=send_task,args=(task_for_client, nr_sequencia, s, agent_address, tarefas_sem_ack)).start()
                current_task += 1
        else:
            tarefas_sem_ack.remove(n_seq)
    elif(msg_type == 3):  # é um output das métricas
        n_seq = int(message_bits[11:35], 2)  # converte os bits do n_seq para um valor inteiro
        metrica = int(message_bits[35:43], 2)  # converte os bits da metrica para um valor inteiro
        task_id = n_seq // 100000
        line_id = n_seq % 100000
        threading.Thread(target=send_ack_to_agent_for_output, args=(s, agent_address, task_id, line_id)).start()
        if n_seq not in tarefas_sem_ack:
            tarefas_sem_ack.append(n_seq)
            if metrica == 4:
                ultima_metrica = int(message_bits[43:75],2)
            else:
                bits_binarios = ''.join(message_bits[43:75])
                numero_em_int = int(bits_binarios, 2)
                ultima_metrica = struct.unpack('!f', numero_em_int.to_bytes(4, byteorder='big'))[0]
            ultima_metrica = round(ultima_metrica, 4)
            if metrica not in [2, 4]:  # se não for nem ping nem interface_stats
                bits_binarios = ''.join(message_bits[75:107])
                numero_em_int = int(bits_binarios, 2)
                media_metricas = struct.unpack('!f', numero_em_int.to_bytes(4, byteorder='big'))[0]
                media_metricas = round(media_metricas, 4)
            else:  # só está a receber a última métrica
                media_metricas = 0
            criar_ficheiro_output(id_router, metrica, ultima_metrica, media_metricas, line_id)


def udp_server(address:str, port:str):
    limpar_ficheiro_output()
    s : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # criar um socket
    try:
        s.bind((address,int(port)))
        threading.Thread(target=menu).start()
        tarefas_sem_ack = []
        while True:
            message, agent_address = s.recvfrom(1024)  # server adormece à espera de mensagem do agente
            threading.Thread(target=processamento_udp,args=(message,agent_address, s, tarefas_sem_ack)).start()
    finally:
        s.close()



######################################################################################

#####################################    TCP    ######################################

######################################################################################



def processamento_tcp(agent_socket, agent_address):
    while True:
        message = agent_socket.recv(6)
        if len(message) == 0:
            return
        message_bits = ''.join(format(byte, '08b') for byte in message)  # garante que cada byte seja representado como uma sequência de 8 caracteres
        id_tarefa = int(message_bits[0:8], 2)
        metrica = int(message_bits[8:16], 2)
        if metrica != 4:
            bits_binarios = ''.join(message_bits[16:])
            numero_em_int = int(bits_binarios, 2)
            ultima_metrica = struct.unpack('!f', numero_em_int.to_bytes(4, byteorder='big'))[0]
            ultima_metrica = round(ultima_metrica, 4)
        else:
            ultima_metrica = int(message_bits[16:], 2)
        criar_ficheiro_alertas(id_tarefa, metrica, ultima_metrica)


def tcp_server(address : str, port : str):
    s : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((address, int(port) +1)) 
        s.listen(5)
        while True:
            agent_socket,agent_address = s.accept()  # aceita a conexão e retorna um novo socket específico para a comunicação com o cliente conectado
            threading.Thread(target=processamento_tcp, args=(agent_socket,agent_address)).start()
    finally:
        s.close()


def main():

    address, port = sys.argv[1], sys.argv[2]
    threads = [threading.Thread(target=udp_server, args=(address,port)),
              threading.Thread(target=tcp_server, args=(address,port))]
    threads[0].start()
    threads[1].start()
    threads[0].join()
    threads[1].join()

if __name__ == "__main__":
        main()