import socket
import json
import ipaddress
import time
import struct

from bitarray import bitarray


# id(8 bits) | msg_type(3 bits) | n_seq(16 bits) | padding(5 bits)
def send_regist(id:str, n_sequencia:int, s:socket.socket, address:str, port:str):
    message = bitarray()
    id_agent = int(id)
    msg_type = 0 # indica que é um pedido de registo
    padding = 0
    message.extend(format(id_agent, '08b'))
    message.extend(format(msg_type, '03b'))
    message.extend(format(n_sequencia, '016b'))
    message.extend(format(padding, '05b'))
    s.sendto(message, (address, int(port)))


# id(8 bits) | msg_type(3 bits) | n_seq(16 bits) | padding(5 bits)
def send_ack_to_agent(n_sequencia:int, s:socket.socket, agent_address, tarefas_sem_ack):
    message = bitarray()
    id = 1
    msg_type = 1 # indica que é um ack
    padding = 0
    message.extend(format(id, '08b'))
    message.extend(format(msg_type, '03b'))
    message.extend(format(n_sequencia, '016b'))
    message.extend(format(padding, '05b'))
    while True:
        s.sendto(message, agent_address)
        time.sleep(5)
        if n_sequencia in tarefas_sem_ack:
            continue
        else:
            break


# task_id(8 bits) | msg_type(3 bits) | n_seq(21 bits)
def send_ack_to_agent_for_output(s:socket.socket, agent_address, task_id, line_id):
    message = bitarray()
    msg_type = 4 # indica que é um ack para os outputs das tarefas
    message.extend(format(int(task_id), '08b'))
    message.extend(format(msg_type, '03b'))
    message.extend(format(int(line_id), '021b'))
    s.sendto(message, agent_address)


# id(8 bits) | msg_type(3 bits) | n_seq(16 bits) | padding(5 bits)
def send_ack_to_server(id_agent, n_sequencia:int, s:socket.socket, address, port, outputs_sem_ack):
    message = bitarray()
    msg_type = 1 # indica que é um ack
    message.extend(format(int(id_agent), '08b'))
    message.extend(format(msg_type, '03b'))
    message.extend(format(n_sequencia, '016b'))
    message.extend(format(0, '05b'))
    while True:
        s.sendto(message, (address, int(port)))
        time.sleep(5)
        if n_sequencia in outputs_sem_ack and n_sequencia == 1:
            continue
        else:
            break


# id(8bits) | msg_type(3 bits) | n_seq(16 bits) | metrica(3 bits) | frequencia(10 bits) | dados(x bits)
def send_task(tarefa, n_sequencia:int, s:socket.socket, agent_address, tarefas_sem_ack):              
    message = bitarray()
    task = json.loads(tarefa)
    id = 0
    msg_type = 2
    metricas_map = {
        "cpu_usage": 0,
        "ram_usage": 1,
        "latency": 2,
        "bandwidth": 3,
        "interface_stats": 4,
        "jitter": 5,
        "packet_loss": 6
    }
    metrica_final = 7
    for metrica, valor in metricas_map.items():
        if task["link_metrics"].get(metrica):
            metrica_final = valor
            break
    frequencia = int(task["frequency"])
    if metrica_final == 2: # apenas tem endereço de destino para fazer o ping
        dados = int(ipaddress.IPv4Address(task["link_metrics"]["latency"]["destination"]))
        packets = int(task["link_metrics"]["latency"]["packets"])
        frequency_packets = int(task["link_metrics"]["latency"]["frequency_packets"])
    if metrica_final == 3: # precisa de endereço para server iperf e para o respetivo cliente
        ip_server = int(ipaddress.IPv4Address(task["link_metrics"]["bandwidth"]["server_address"]))
        ip_client = int(ipaddress.IPv4Address(task["link_metrics"]["bandwidth"]["client_address"]))
        dados = (ip_server << 32) | ip_client  # concatena os dois IPs (32 bits cada)
    if metrica_final == 5: # precisa de endereço para server iperf e para o respetivo cliente
        ip_server = int(ipaddress.IPv4Address(task["link_metrics"]["jitter"]["server_address"]))
        ip_client = int(ipaddress.IPv4Address(task["link_metrics"]["jitter"]["client_address"]))
        dados = (ip_server << 32) | ip_client  # concatena os dois IPs (32 bits cada)
    if metrica_final == 6: # precisa de endereço para server iperf e para o respetivo cliente
        ip_server = int(ipaddress.IPv4Address(task["link_metrics"]["packet_loss"]["server_address"]))
        ip_client = int(ipaddress.IPv4Address(task["link_metrics"]["packet_loss"]["client_address"]))
        dados = (ip_server << 32) | ip_client # concatena os dois IPs (32 bits cada)
    if metrica_final == 4:
        interface_map = {
            "eth0": 0,
            "eth1": 1,
            "eth2": 2,
            "eth3": 3,
            "eth4": 4
        }
        dados = interface_map.get(task["link_metrics"]["interface_stats"])
    message.extend(format(id, '08b'))
    message.extend(format(msg_type, '03b'))
    message.extend(format(n_sequencia, '016b'))
    message.extend(format(metrica_final, '03b'))
    message.extend(format(frequencia, '010b'))
    if metrica_final not in [0, 1]:
        if metrica_final == 2:
            message.extend(format(packets, '08b'))
            message.extend(format(frequency_packets, '08b'))
            message.extend(format(dados, '032b'))
        if metrica_final == 3 or metrica_final == 5 or metrica_final == 6:
            message.extend(format(dados, '064b'))
        if metrica_final == 4:
            message.extend(format(dados, '08b'))
    if metrica_final not in [2, 3, 4]:
        alert_flow = int(task["alertflow_conditions"])
        message.extend(format(alert_flow, '08b'))
    while True:
        s.sendto(message, agent_address)
        if n_sequencia not in tarefas_sem_ack:
            tarefas_sem_ack.append(n_sequencia)
        time.sleep(5)
        if n_sequencia in tarefas_sem_ack:
            continue
        else:
            break


# id(8 bits) | msg_type(3 bits) | n_seq(24 bits) | metrica(8bits) | ultima_metrica(32 bits) | media_metricas (32 bits)
def send_output(id, ultima_metrica, media_metricas, metrica, n_sequencia, s, address, port, outputs_sem_ack):
    outputs_sem_ack.append(n_sequencia)
    message = bitarray()
    msg_type = 3
    message.extend(format(int(id), '08b'))
    message.extend(format(msg_type, '03b'))
    message.extend(format(n_sequencia, '024b'))
    message.extend(format(metrica, '08b'))
    if metrica == 4:  # em interface_stats 0 significa que está DOWN e 1 significa que está UP
        if ultima_metrica == "DOWN": message.extend(format(0, '032b'))
        elif ultima_metrica == "UP": message.extend(format(1, '032b'))
    else:
        ultima_metrica_bin = ''.join(format(byte, '08b') for byte in struct.pack('!f', ultima_metrica))
        message.extend(ultima_metrica_bin)
    if metrica not in [2, 4]:
        media_metricas_bin = ''.join(format(byte, '08b') for byte in struct.pack('!f', media_metricas))
        message.extend(media_metricas_bin)
    while True:
        s.sendto(message, (address, int(port)))
        time.sleep(5)
        if n_sequencia in outputs_sem_ack:
            continue
        else:
            break