# LoRaSimPlus

O **LoRaSimPlus** é uma extensão avançada do simulador LoRaSim, focada em redes LoRaWAN clusterizadas. Esta versão inclui suporte a algoritmos de agrupamento (K-means, LEACH), métricas detalhadas de energia, eficiência por bit e conformidade com protocolos de tempo (Duty Cycle e janelas de confirmação).

## 🚀 Como Executar

O simulador é controlado via linha de comando com 19 argumentos posicionais:

```bash
python3 main.py <Nodes> <Interval> <AllocType> <AllocMode> <SimTime> <nrBS> <Collision> <Antenna> <Networks> <Radius> <Payload> <Clustering> <nClusters> <Algo> <CH_Prob> <Rounds> <InitEnergy> <Graphics> <CH_Selection>
```

### Exemplo de Comando (Recomendado):
```bash
python3 main.py 100 300000 Local closest 3600000 1 1 1 1 2000 20 1 5 kmeans 0.1 1 1.0 0 centroid
```

### Tabela de Argumentos:
| Pos | Argumento | Descrição | Valores Sugeridos |
|-----|-----------|-----------|-------------------|
| 1 | `Nodes` | Número total de sensores | 10 a 2000 |
| 2 | `Interval` | Intervalo médio entre mensagens (ms) | 300000 (5 min) |
| 3 | `AllocType` | Escopo da alocação de rádio | `Local` ou `Global` |
| 4 | `AllocMode` | Método de escolha de SF | `closest`, `random`, `polling` |
| 5 | `SimTime` | Tempo total da simulação (ms) | 3600000 (1 hora) |
| 10 | `Radius` | Raio da rede em metros | 2000 |
| 12 | `Clustering`| Habilitar módulos de cluster (1=Sim, 0=Não) | 1 |
| 13 | `nClusters` | Quantidade de grupos de sensores | 5 |
| 14 | `Algorithm` | Algoritmo de formação | `kmeans` ou `leach` |
| 19 | `CH_Selection`| Método de escolha do cabeçalho | `centroid` ou `default` |

---

## 📊 Arquivos de Saída (Resultados)

Os resultados são salvos em `results/<timestamp>/`:

1.  **`links.csv`**: Log detalhado de **cada pacote enviado**. Contém Sensor ID, RSSI, SNR, Spreading Factor (SF), ToA e status final (RECEIVED, COLLISION, LOST).
2.  **`*-cluster-performance.csv`**: Métricas agregadas por cluster:
    -   **PDR**: Taxa de entrega de pacotes.
    -   **acks**: Mensagens que receberam confirmação da rede.
    -   **Bits/Joule**: Eficiência energética (Bits recebidos por Joule gasto).
    -   **Tempo de Estados**: Tempo médio em Transmissão (TX), Escuta (RX) e Sleep.
    -   **Duty Cycle**: Porcentagem de ocupação real do canal por nó.
3.  **`*-clusters.png`**: Mapa visual da rede com nós coloridos por cluster e Cluster Heads destacados.

---

## 🛠️ Novas Funcionalidades Implementadas

-   **Refatoração de Estado Global**: Otimização da sincronização de parâmetros via `ParameterConfig`.
-   **Duty Cycle Enforcement**: O simulador agora obriga os nós a respeitarem o tempo de silêncio legal após cada transmissão.
-   **Modelo LoRaWAN Class A**: Implementação das janelas de recepção RX1 e RX2 para simulação de confirmações (ACKs).
-   **Seleção por Centroide**: Capacidade de escolher como Cluster Head o nó mais próximo do centro geométrico do cluster.

## Créditos
Extensões e melhorias desenvolvidas por:
**Cristofe Rocha**
*Doutorando na Universidade Federal de Pernambuco (UFPE)*
