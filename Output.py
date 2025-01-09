import json
import glob


def criar_ficheiro_output(id_router, metrica, ultima_metrica, media_metricas, line_id):
    # estrutura inicial para o ficheiro JSON
    estrutura_inicial = {
        "cpu_usage": [],
        "ram_usage": [],
        "latency": [],
        "bandwidth": [],
        "interface_stats": [],
        "jitter": [],
        "packet_loss": []
    }
    try:
        with open(f'outputs{id_router}.json', 'r') as file:
            dados = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError): # se o ficheiro não existir ou estiver vazio, usa a estrutura inicial
        dados = estrutura_inicial
    if metrica == 0:
        mensagem = f"{ultima_metrica} {media_metricas}"
        dados["cpu_usage"].insert(line_id-1, mensagem)
    elif metrica == 1:
        mensagem = f"{ultima_metrica} {media_metricas}"
        dados["ram_usage"].insert(line_id-1, mensagem)
    elif metrica == 2:
        mensagem = f"{ultima_metrica}"
        dados["latency"].insert(line_id-1, mensagem)
    elif metrica == 3:
        mensagem = f"{ultima_metrica} {media_metricas}"
        dados["bandwidth"].insert(line_id-1, mensagem)
    elif metrica == 4:
        if ultima_metrica == 0: mensagem = "DOWN"
        elif ultima_metrica == 1: mensagem = "UP"
        dados["interface_stats"].insert(line_id-1, mensagem)
    elif metrica == 5:
        mensagem = f"{ultima_metrica} {media_metricas}"
        dados["jitter"].insert(line_id-1, mensagem)
    elif metrica == 6:
        mensagem = f"{ultima_metrica} {media_metricas}"
        dados["packet_loss"].insert(line_id-1, mensagem)
    with open(f'outputs{id_router}.json', 'w') as file:  # escreve os dados atualizados no ficheiro
        json.dump(dados, file, indent = 4)  # indent=4 é para uma formatação legível

def criar_ficheiro_alertas(id_task, metrica, ultima_metrica):
    # estrutura inicial para o ficheiro JSON
    estrutura_inicial = {
        "alerts": []
    }
    try:
        with open(f'outputs_alerts.json', 'r') as file:
            # tenta carregar os dados existentes se o ficheiro já existir
            dados = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):  # se o ficheiro não existir ou estiver vazio, usa a estrutura inicial
        dados = estrutura_inicial
    if metrica == 0:          #cpu
        mensagem = f"A tarefa {id_task} retornou {ultima_metrica}% de uso de CPU"
    elif metrica == 1:       #ram
        mensagem = f"A tarefa {id_task} retornou {ultima_metrica}% de uso de RAM"
    elif metrica == 2:       #latency
        mensagem = f"A tarefa {id_task} retornou uma variacao de latencia superior a 25%"
    elif metrica == 4:       #interface_stats
        mensagem = f"A tarefa {id_task} retornou que a interface que esta a ser monitorizada encontra-se inativa"
    elif metrica == 5:       #jitter
        mensagem = f"A tarefa {id_task} retornou {ultima_metrica} como valor de jitter"
    elif metrica == 6:       #packet_loss
        mensagem = f"A tarefa {id_task} retornou {ultima_metrica}% de perda de pacotes"
    dados["alerts"].append(mensagem)
    with open(f'outputs_alerts.json', 'w') as file:  # escreve os dados atualizados de volta no ficheiro
        json.dump(dados, file, indent = 4)  # indent=4 é para uma formatação legível


def limpar_ficheiro_output():
    for ficheiro in glob.glob("outputs*"):  # procura por todos os ficheiros na diretoria atual que começam com "output"
        with open(ficheiro, 'w') as file:  # limpa o conteúdo do ficheiro (se existir) no início do servidor
            pass


def exibe_output(id_agent, metrica):
    try:
        with open(f'outputs{id_agent}.json', 'r') as file:
            dados = json.load(file)
            if not dados:  # caso o ficheiro esteja vazio
                print(f"O agente {id_agent} não retornou outputs")
                return
            metricas_map = {
                "cpu_usage": 1,
                "ram_usage": 2,
                "latency": 3,
                "bandwidth": 4,
                "interface_stats": 5,
                "jitter": 6,
                "packet_loss": 7
            }
            for metrica_map, valor in metricas_map.items():
                if  valor == metrica:
                    if not dados[metrica_map]:
                        print ("Não existe resultado para exibir referente a essa métrica")
                    else:
                        ultima_linha = dados[metrica_map][-1]
                        valores = ultima_linha.split()
                        if len(valores) == 2:
                            print(f"O último resultado dessa métrica foi: {valores[0]}")
                            print(f"A média dos resultados até agora é: {valores[1]}")
                        elif len(valores) == 1:
                            print(f"O último resultado dessa métrica foi: {valores[0]}")
                    break
    except (FileNotFoundError, json.JSONDecodeError):  # se o ficheiro não existir
        print(f"O agente {id_agent} não retornou outputs")


def exibe_alerts():
    try:
        with open(f'outputs_alerts.json', 'r') as file:
            dados = json.load(file)
            if not dados:  # caso o ficheiro esteja vazio
                print(f"Não existem alertas")
                return
            i = 1
            while i<=min(10, len(dados["alerts"])):
                print(dados["alerts"][-i])
                i+=1
    except (FileNotFoundError, json.JSONDecodeError):  # se o ficheiro não existir
        print(f"Não existem alertas")