#!/bin/bash

echo "--- TESTE 1: K-means (100 nós, 5 clusters) ---"
python3 main.py 100 300000 Local random 3600000 1 1 1 1 2000 20 1 5 kmeans 0.05 1 1.0 0

echo -e "\n--- TESTE 2: LEACH (50 nós, 20 rounds, baixa energia para teste de morte) ---"
# Parâmetros: <Nós> <Intervalo> <AllocType> <AllocMethod> <SimTime> <GWs> <Colisão> <Antena> <Redes> <Raio> <Payload> <Clustering> <nClusters> <Algoritmo> <LeachProb> <Rounds> <EnergiaInicial> <Graphics>
python3 main.py 50 300000 Local random 3600000 1 0 0 1 2000 20 1 0 leach 0.1 20 0.00005 0

echo -e "\n--- Verificando arquivos gerados ---"
ls -R results/ | grep -E "clusters.png|cluster-rounds.csv|cluster-nodes.csv"
