from Output import*

def menu():
    print("\n")
    print("---------Deseja ver o output de qual agente?---------")
    print("-----------(Escolha um número entre 2 e 5)-----------")
    opcao_agent = input()
    if opcao_agent not in ["2", "3", "4", "5"]:
        menu()
    print("\n")
    print("Selecione a métrica que deseja consultar:")
    print("--------------Cpu_usage(1)--------------")
    print("--------------Ram_usage(2)--------------")
    print("---------------Latency(3)---------------")
    print("--------------Bandwidth(4)--------------")
    print("-----------Interface_stats(5)-----------")
    print("----------------Jitter(6)---------------")
    print("-------------Packet_loss(7)-------------")
    print("----------------Alerts(8)---------------")
    opcao_metric = input()
    if opcao_metric not in ["1", "2", "3", "4", "5", "6", "7", "8"]:
        menu()
    print()
    if opcao_metric!="8": exibe_output(int(opcao_agent), int(opcao_metric))
    else: exibe_alerts()
    menu()