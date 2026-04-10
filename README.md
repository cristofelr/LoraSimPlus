# LoRaSim para Alocação de Parâmetros
[LoRaSim](https://www.lancaster.ac.uk/scc/sites/lora/lorasim.html) é um simulador LoRa desenvolvido com base no simpy, uma biblioteca Python para simulação de eventos discretos. O LoRaSim fornece um processo completo de transmissão de pacotes de rede e propõe um mecanismo de detecção de colisão. No entanto, o LoRaSim não fornece métodos de alocação de parâmetros LoRa durante a transmissão de pacotes, que é atualmente o foco de pesquisa de muitos pesquisadores de LoRa. O LoRaSimPlus fornece aos pesquisadores serviços programáveis mais ricos baseados no LoRaSim, o que pode ajudar os pesquisadores a realizar pesquisas mais profundas sobre consumo de energia e transmissão de pacotes da rede LoRaWAN.

Esta versão estendida, **LoRaSimPlus**, inclui suporte avançado para clusterização (K-means e LEACH) e modelagem de energia, desenvolvida para simular cenários de IoT com maior fidelidade.

## Requisitos
* Python == 3.x
* simpy
* matplotlib
* numpy
  
## Como Usar
O arquivo `ParameterConfig.py` inclui todas as configurações de parâmetros padrão suportadas pelo simulador. Você pode modificar as configurações padrão no `ParameterConfig.py` e usar a seguinte linha de comando para executar o simulador:

```bash
python3 main.py
```

Você também pode deixar as configurações padrão inalteradas e definir os parâmetros através da linha de comando:

```bash
python3 main.py <Nodes> <Interval> <AllocType> <AllocMode> <SimTime> <Gateways> <CollisionMode> <Antenna> <Networks> <Radius> <Payload> <Clustering(0/1)> <Algorithm> <CH_Prob> <Rounds> <InitialEnergy> <Graphics(0/1)> <CH_Selection>
```

### Parâmetros de Clusterização:
- **Clustering**: 0 (desativado) ou 1 (ativado).
- **Algorithm**: `kmeans` ou `leach`.
- **CH_Prob**: Probabilidade de se tornar Cluster Head (ex: 0.1).
- **Rounds**: Número de rodadas (LEACH).
- **InitialEnergy**: Energia inicial em Joules (ex: 1.0).
- **Graphics**: 0 (ocultar visualização) ou 1 (exibir).
- **CH_Selection**: `default` (padrão do algoritmo) ou `centroid` (força seleção pelo centroide).

Para mais detalhes sobre os parâmetros de clusterização, consulte o [TUTORIAL.md](TUTORIAL.md).

## Clusterização (Clustering)
O LoRaSimPlus suporta dois algoritmos principais de clusterização:

1.  **K-means**: Agrupa os nós geograficamente em *K* clusters fixos. O nó mais central de cada grupo é eleito como Cluster Head (CH).
2.  **LEACH (Low-Energy Adaptive Clustering Hierarchy)**: Protocolo probabilístico e adaptativo que rotaciona o papel de CH entre os nós para balancear o consumo de energia. Suporta múltiplos rounds de simulação e rastreamento de morte de nós.

O fluxo de comunicação na rede clusterizada segue o padrão:
`Nó (Membro) ──► Cluster Head (CH) ──► Gateway (GW)`

## Estrutura do Software
O simulador é composto pelos seguintes arquivos principais:

### [ParameterConfig.py](ParameterConfig.py)
Inclui todas as variáveis globais, parâmetros LoRaWAN e de clusterização.

### [main.py](main.py)
Programa principal que inicia a simulação e fornece a interface CLI.

### [Clustering.py](Clustering.py)
Implementa os algoritmos K-means e LEACH, o modelo de energia de primeira ordem e as ferramentas de visualização de clusters.

### [simulation.py](simulation.py)
Gerencia o ambiente SimPy e integra a lógica de rede com a clusterização.

### [Node.py](Node.py), [Gateway.py](Gateway.py), [Packet.py](Packet.py), [Propagation.py](Propagation.py)
Definem os objetos fundamentais da rede LoRaWAN, modelos de propagação e detecção de colisão.

### Arquivos de Saída:
- `*-result.txt`: Resultados gerais da simulação LoRa.
- `*-cluster-nodes.csv`: Lista de nós, suas posições, clusters e energia residual.
- `*-cluster-rounds.csv`: Métricas de energia por rodada (idealizado).
- `*-cluster-performance.csv`: **(Novo)** Métricas reais da simulação (PDR, pacotes enviados/perdidos, Bits/Joule por cluster).
- `*-clusters.png`: Visualização do layout de clusters (fundo branco).

## Créditos
As melhorias e extensões aplicadas nesta versão do simulador (LoRaSimPlus), incluindo a implementação dos módulos de clusterização, métricas de energia e otimizações de CLI, foram realizadas por:

**Cristofe Rocha**
*Aluno de Doutorado da Universidade Federal de Pernambuco (UFPE)*
