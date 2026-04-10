import subprocess
import sys
import os

def run_cmd(cmd):
    print(f"\n> Executando: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERRO: {result.stderr}")
    else:
        print(result.stdout)
    return result.returncode

def test_all():
    # TESTE 1: K-means via CLI
    # python3 main.py <Nós> <Intervalo> <AllocType> <AllocMethod> <SimTime> <GWs> <Colisão> <Antena> <Redes> <Raio> <Payload> <Clustering> <nClusters> <Algoritmo>
    cmd_kmeans = [
        sys.executable, "main.py", 
        "100", "300000", "Local", "random", "3600000", 
        "1", "1", "1", "1", "2000", "20", "1", "5", "kmeans"
    ]
    
    # TESTE 2: LEACH via CLI (Energia baixa para ver mortes)
    # <Clustering> <nClusters> <Algoritmo> <LeachProb> <LeachRounds> <EnergiaInicial>
    cmd_leach = [
        sys.executable, "main.py", 
        "50", "300000", "Local", "random", "3600000", 
        "1", "0", "0", "1", "2000", "20", "1", "0", "leach", "0.1", "20", "0.00005"
    ]

    print("=== INICIANDO TESTES DE CLUSTERIZAÇÃO ===")
    
    # Set graphics to 0 in ParameterConfig.py temporarily for the test
    # Actually, main.py doesn't have a flag for graphics, it reads from config.
    # Let's patch ParameterConfig.py for the duration of the test.
    with open("ParameterConfig.py", "r") as f:
        original_config = f.read()
    
    try:
        # Force graphics=0
        new_config = original_config.replace("graphics = 1", "graphics = 0")
        with open("ParameterConfig.py", "w") as f:
            f.write(new_config)
            
        ret1 = run_cmd(cmd_kmeans)
        ret2 = run_cmd(cmd_leach)
        
        if ret1 == 0 and ret2 == 0:
            print("\n✅ TODOS OS TESTES PASSARAM!")
        else:
            print("\n❌ ALGUNS TESTES FALHARAM.")
            
    finally:
        # Restore config
        with open("ParameterConfig.py", "w") as f:
            f.write(original_config)

if __name__ == "__main__":
    test_all()
