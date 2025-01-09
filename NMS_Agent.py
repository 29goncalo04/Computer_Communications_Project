import socket
import sys
import threading
import subprocess
import netifaces

from Parser import *
from Message_Sending import *
from Parser import parse_output


def run_command(command, metrica, alert_flow, s, address, port, id, task_id, mensagens_sem_ack, tcp_errors):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    line_id = 0
    metricas_totais = []
    frequency_packets = 0
    while True:
        output = process.stdout.readline().strip()  # lê a saída linha por linha
        if output:
            #print(output)
            valor_print = parse_output(metrica, output, metricas_totais, frequency_packets)
            if valor_print:
                line_id += 1
                if isinstance(valor_print, tuple):  # se existir ultima métrica e média das métricas
                    ultima_metrica, media_metricas = valor_print
                else:  # se só existir última métrica
                    ultima_metrica = valor_print
                    media_metricas = 0
                if(alert_flow):
                    if float(ultima_metrica) > alert_flow : 
                        mensagem = parse_alert(metrica, float(ultima_metrica), task_id)
                        tcp_errors.append(mensagem)
                else:
                    if metrica == 2:
                        variacao = media_metricas
                        if variacao >= 0.25*ultima_metrica : 
                            mensagem = parse_alert(metrica, float(ultima_metrica), task_id)
                            tcp_errors.append(mensagem)
                    if metrica == 4:
                        mensagem = parse_alert(metrica, ultima_metrica, task_id)
                        if mensagem : tcp_errors.append(mensagem)
                n_sequencia = (int(task_id) * 100000) + int(line_id)
                threading.Thread(target = send_output, args = (id, ultima_metrica, media_metricas, metrica, n_sequencia, s, address, port, mensagens_sem_ack)).start()



def udp_agent(address:str, port:str, id:str, tcp_errors):
    # obtém todos os endereços IP de todas as interfaces
    agent_addresses = []
    mensagens_sem_ack = []
    for interface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs:  # verifica se a interface tem um endereço IPv4
            agent_addresses.extend([addr['addr'] for addr in addrs[netifaces.AF_INET]]) # Armazena apenas os IPs numa lista
    s : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    try:
        while True:   
            try:
                send_regist(id, 0, s, address, port)  # envia pedido de registo ao servidor
                s.settimeout(5)  # configura o timeout para 5 segundos
                message = s.recv(1024)  # recebe suposto ack do server
                message_bits = ''.join(format(byte, '08b') for byte in message) # garante que cada byte seja representado como uma sequência de 8 caracteres
                msg_type = int(message_bits[8:11], 2)
                n_seq = int(message_bits[11:27], 2)
                if msg_type == 1 and n_seq == 0:
                    threading.Thread(target=send_ack_to_server, args=(id, 1, s, address, port, mensagens_sem_ack)).start()
                    mensagens_sem_ack.append(1)
                    break
            except socket.timeout:
                continue
        while True:
            try:
                task_from_server = s.recv(1024)  # recebe suposta tarefa do servidor
                message_bits = ''.join(format(byte, '08b') for byte in task_from_server)
                msg_type = int(message_bits[8:11], 2)
                if msg_type == 2:
                    if 1 in mensagens_sem_ack:
                        mensagens_sem_ack.remove(1)
                    n_seq = int(message_bits[11:27], 2)
                    threading.Thread(target=send_ack_to_server, args=(id, n_seq, s, address, port,mensagens_sem_ack)).start()  #confirma receção da tarefa
                    if n_seq not in mensagens_sem_ack:
                        mensagens_sem_ack.append(n_seq)
                        metrica, command, alert_flow = parser_task(task_from_server, agent_addresses)
                        threading.Thread(target=run_command, args=(command, metrica, alert_flow, s, address, port, id, n_seq-1, mensagens_sem_ack, tcp_errors)).start()
                elif msg_type == 4:
                    n_seq = int(message_bits[:8], 2)*100000 + int(message_bits[11:], 2)
                    mensagens_sem_ack.remove(n_seq)
            except socket.timeout:
                continue
    finally:
        s.close()



######################################################################################

#####################################    TCP    ######################################

######################################################################################



def tcp_agent(address : str, port : str, tcp_errors):
    s : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.connect((address, int(port) +1))
        last_index = 0
        while True:
            if len(tcp_errors) > last_index:
                for alert in tcp_errors[last_index:]:
                    s.send(alert)
                last_index = len(tcp_errors)
    finally:
        s.close()


def main():
    address, port, id = sys.argv[1], sys.argv[2], sys.argv[3]
    tcp_errors = []

    threads = [threading.Thread(target=udp_agent, args=(address,port,id, tcp_errors)),
               threading.Thread(target=tcp_agent, args=(address,port, tcp_errors))]

    threads[0].start()
    threads[1].start()
    threads[0].join()
    threads[1].join()
   

if __name__ == "__main__":
        main()