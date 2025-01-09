import json
import ipaddress
import struct

from bitarray import bitarray


def ler_ficheiro_json(caminho_ficheiro):
    try:
        with open(caminho_ficheiro, 'r', encoding='utf-8') as f:
            dados = json.load(f)  # lê e interpreta o JSON
        return dados
    except FileNotFoundError:
        print(f"Erro: O ficheiro '{caminho_ficheiro}' não foi encontrado.")


def parser_task(task_from_server, agent_addresses):
    message_bits = ''.join(format(byte, '08b') for byte in task_from_server)
    metrica = int(message_bits[27:30], 2)
    frequencia = int(message_bits[30:40], 2)
    command = []
    if metrica == 0:   #cpu_usage
        command = [
            "mpstat",
            "-P", "0",  # monitorizar a cpu principal
            str(frequencia)
        ]
        alert_flow = int(message_bits[40:48], 2)
        return metrica, command, alert_flow
    elif metrica == 1:   #ram_usage
        command = [
            "free",
            "-h",  # exibe a memória em formato legível (GB, MB)
            "-s", str(frequencia) # atualiza a cada x segundos.
        ]
        alert_flow = int(message_bits[40:48], 2)
        return metrica, command, alert_flow
    elif metrica == 2:   #latency
        packets = int(message_bits[40:48],2)
        frequency_packets = int(message_bits[48:56],2)
        dados = int(message_bits[56:], 2)
        ip = str(ipaddress.IPv4Address(dados >> 32))
        command = [
            "bash", "-c", f"while true; do ping -c {packets} -i {frequency_packets} {ip}; done"
        ]
        return metrica, command, None
    elif metrica == 3 or metrica == 5 or metrica == 6:   # bandwidth ou jitter ou packet_loss
        dados = int(message_bits[40:104], 2)
        ip_server = str(ipaddress.IPv4Address(dados >> 32))
        ip_client = str(ipaddress.IPv4Address(dados & 0xFFFFFFFF))
        for ip in agent_addresses:           
            if(ip_server == ip):
                command = [
                    "iperf3",
                    "-s",
                    "-i", str(frequencia)
                ]
                command = ["stdbuf", "-oL"] + command  # adiciona stdbuf para saída sem buffer
                break
        for ip in agent_addresses:           
            if(ip_client == ip):
                command = [
                    "iperf3",
                    "-c", str(ip_server),  # define o modo cliente e IP do servidor
                    "-u",  # define o protocolo UDP
                    "-i", str(frequencia),
                    "-t 0"  # faz com que corra infinitamente
                ]
                command = ["stdbuf", "-oL"] + command  # adiciona stdbuf para saída sem buffer
                break
        if metrica == 3:
            return metrica, command, None
        if metrica == 5:
            alert_flow = int(message_bits[104:112], 2)
            return metrica, command, alert_flow
        if metrica == 6:
            alert_flow = int(message_bits[104:112], 2)
            return metrica, command, alert_flow
    elif metrica == 4:   #interface_stats
        dados = int(message_bits[40:48], 2)
        command = [
            "bash", "-c", f"while true; do ip link show eth{dados}; sleep {frequencia}; done"
        ]
        return metrica, command, None


def parse_output(metrica, output, metricas_totais, frequency_packets):
    if metrica == 0:  #cpu_usage
        # ignora linhas irrelevantes
        if not any(skip_word in output for skip_word in ["Linux", "CPU", "Average"]):
            fields = output.split()
            idle_cpu = float(fields[-1].replace(",", "."))  # converte %idle para float
            cpu_usage = 100.0 - idle_cpu  # calcula o uso da CPU
            resultado = round(cpu_usage, 2)  #  para 2 casas decimais
            metricas_totais.append(resultado)
            soma_resultados = 0
            for valor in metricas_totais:
                soma_resultados += valor
            resultado_medio = round((soma_resultados / len(metricas_totais)),2)
            return resultado, resultado_medio
    if metrica == 1:   # ram_usage
        if output.startswith("Mem:"):
            fields = output.split()
            total = float(fields[1].replace("Gi", "").replace(",", "."))  # Total de RAM
            used = float(fields[2].replace("Gi", "").replace(",", "."))   # RAM usada
            ram_usage = round((used / total) * 100, 2)  # percentagem de ram utilizada no último output recebido
            metricas_totais.append(ram_usage)
            soma_resultados = 0
            for valor in metricas_totais:
                soma_resultados += valor
            resultado_medio = round((soma_resultados / len(metricas_totais)),2)
            return ram_usage, resultado_medio
    if metrica == 2:   # latency
        if "rtt min" in output:
            fields = output.split(" = ")[1].split("/")
            avg = fields[1]
            desvio = fields[3].split(" ")[0]
            return float(avg), float(desvio)
    if metrica == 3:   # bandwidth
        if "Mbits/sec" in output:
            fields = output.split()
            bitrate_index = fields.index("Mbits/sec") - 1  # valor que está antes de "Mbits/sec"
            bitrate = float(fields[bitrate_index])  # pega no valor do Bitrate
            metricas_totais.append(bitrate)
            soma_resultados = 0
            for valor in metricas_totais:
                soma_resultados += valor
            resultado_medio = round((soma_resultados / len(metricas_totais)),2)
            return bitrate, resultado_medio
    if metrica == 4:    # interface_status
        if "state" in output:
            fields = output.split()
            state_index = fields.index("state") + 1
            status = fields[state_index]  # obtém o valor que está a seguir ao campo 'state'
            return status
    if metrica == 5:    # jitter
        if "Mbits/sec" in output and "ms" in output:
            fields = output.split()
            jitter_index = fields.index("ms") - 1  # valor que está antes de "ms"
            jitter = float(fields[jitter_index])  # pega no valor do jitter
            metricas_totais.append(jitter)
            soma_resultados = 0
            for valor in metricas_totais:
                soma_resultados += valor
            resultado_medio = round((soma_resultados / len(metricas_totais)),3)
            return jitter, resultado_medio
    if metrica == 6:    # packet_loss
        if "%" in output:  # Garante que há uma percentagem na linha
            fields = output.split("(")  # divide onde começa o parêntese
            percent_part = fields[1]  # pega na parte após o '('
            packet_loss = float(percent_part.split("%")[0])  # pega no valor antes do '%' e converte para float
            metricas_totais.append(packet_loss)
            soma_resultados = 0
            for valor in metricas_totais:
                soma_resultados += valor
            resultado_medio = round((soma_resultados / len(metricas_totais)),1)
            return packet_loss, resultado_medio
        

# id_tarefa(8 bits) | metrica (8 bits) | ultima_metrica (32 bits)     -> 48 bits
def parse_alert(metrica, ultima_metrica, id_tarefa):
    message = bitarray()
    message.extend(format(int(id_tarefa), '08b'))
    message.extend(format(int(metrica), '08b'))
    if (ultima_metrica == "DOWN"): message.extend(format(0, '032b'))
    elif (ultima_metrica == "UP"): return None
    else:
        ultima_metrica_bin = ''.join(format(byte, '08b') for byte in struct.pack('!f', ultima_metrica))
        message.extend(ultima_metrica_bin)
    return message