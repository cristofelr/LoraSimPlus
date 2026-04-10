# Tutorial: Simulação com Clusterização no LoRaSimPlus

## Pré-requisitos

```bash
pip3 install simpy numpy matplotlib
```

---

## Passo 1 — Configurar os parâmetros em `ParameterConfig.py`

```python
# --- Rede ---
nrNodes      = 100       # número de nós
nrBS         = 1         # número de gateways
radius       = 2000      # raio da topologia em metros
avgSendTime  = 300000    # intervalo médio de envio (ms)
simtime      = 3600000   # duração da simulação (ms) — 1 hora
PayloadSize  = 20        # tamanho do payload (bytes)

# --- LoRa ---
allocation_type   = "Local"   # "Local" ou "Global"
allocation_method = "random"  # "random", "closest" ou "polling"

# --- Clusterização ---
clustering_enabled   = True      # True = ativa clustering
nrClusters           = 5         # número de clusters (K-means)
clustering_algorithm = "kmeans"  # "kmeans" ou "leach"
leach_ch_prob        = 0.05      # prob. de ser CH (LEACH)
leach_rounds         = 20        # número de rounds (LEACH)
node_initial_energy  = 1.0       # energia inicial por nó (Joules)
```

---

## Passo 2 — Executar a simulação

### Usando o arquivo de configuração (recomendado):

```bash
python3 main.py
```

### Via linha de comando:

```bash
# K-means — 100 nós, 5 clusters, 1 gateway, 1 hora
python3 main.py 100 300000 Local random 3600000 1 1 1 1 2000 20 1 5 kmeans

# LEACH — 10% prob. de CH, 30 rounds, energia inicial 2.0 J
python3 main.py 100 300000 Local random 3600000 1 1 1 1 2000 20 1 0 leach 0.10 30 2.0

# Sem clustering (comportamento original)
python3 main.py 100 300000 Local random 3600000 1 1 1 1 2000 20 0
```

**Formato completo:**
```
python3 main.py <Nós> <Intervalo_ms> <TipoAlocação> <MétodoAlocação>
                <Duração_ms> <Gateways> <Colisão> <Antena> <Redes>
                <Raio_m> <Payload> <Clustering> <nClusters>
                <Algoritmo> <LeachProb> [<LeachRounds> <EnergiaInicial_J>]
```

---

## Passo 3 — Saída do terminal

```
=======================================================
  Clustering Summary — Algorithm: LEACH
=======================================================
  Total rounds simulated : 20
  Final clusters         : 5
  Final CHs              : 5
  First node death       : round 8
  Network lifetime       : 17 rounds  (last node died)
  Alive nodes (final)    : 0
  Avg residual energy    : 0.0000e+00 J
=======================================================
  Cluster  0: CH=node12  Members=[3, 7] Alive=3
  ...
```

O fluxo de comunicação na rede é:

```
Nó (CM) ──► Cluster Head (CH) ──► Gateway (GW)
```

- **CMs** usam distância ao CH para cálculo de SF/BW
- **CHs** usam distância ao Gateway para cálculo de SF/BW
- No gráfico dos clusters, os **CHs aparecem como ★ amarelas**

---

## Passo 4 — Gráfico de clusters

Ao final da clusterização, o gráfico é exibido e salvo em:

```
results/<timestamp>/<timestamp>-clusters.png
```

O gráfico mostra:
- Nós coloridos por cluster
- Linhas ligando CMs ao seu CH (mesma cor)
- CHs marcados com **★** amarelo
- Gateways marcados com **▲** ciano

---

## Passo 5 — Verificar os arquivos de resultados

Os arquivos são salvos em `results/<timestamp>/`:

| Arquivo | Conteúdo |
|---|---|
| `*-clusters.png` | Gráfico visual dos clusters |
| `*-cluster-rounds.csv` | Métricas por round: nós vivos, energia residual, nº CHs |
| `*-cluster-nodes.csv` | Estado final de cada nó: energia, cluster, role, alive |
| `link_metrics.txt` | Log de cada transmissão com coluna `ROLE` (CH/CM/NODE) |
| `*-result.txt` | Resumo: parâmetros + DER + energia + lifetime da rede |

### Ver métricas por round:
```bash
column -t -s ',' results/*/\*-cluster-rounds.csv
```

### Ver estado final dos nós:
```bash
column -t -s ',' results/*/\*-cluster-nodes.csv | head -20
```

---

## Modelo de Energia (First-Order Radio)

O consumo de energia é calculado com o **modelo de rádio de primeira ordem** de Heinzelman (2000):

| Quem | Operação | Fórmula |
|---|---|---|
| CM | Transmite ao CH | `E_elec * bits + E_amp * bits * d²` |
| CM | Recebe broadcast do CH | `E_elec * bits` |
| CH | Recebe de cada CM | `E_elec * bits * n_membros` |
| CH | Agrega dados | `E_DA * bits * n_membros` |
| CH | Transmite ao Gateway | `E_elec * bits + E_amp * bits * d²` |

Um nó morre quando sua `energia ≤ 0`.

---

## Métricas de Lifetime

| Métrica | Descrição |
|---|---|
| **First node death** | Round em que o **primeiro** nó morreu |
| **Network lifetime** | Round em que o **último** nó morreu |
| **Alive nodes** | Número de nós vivos ao final da simulação |
| **Avg residual energy** | Energia média dos nós vivos (em Joules) |

---

## Diferença entre K-means e LEACH

| | **K-means** | **LEACH** |
|---|---|---|
| Controle | Você define `nrClusters` | Probabilístico (`leach_ch_prob`) |
| Rounds | 1 (fixo) | Múltiplos (`leach_rounds`) |
| CH | Mais central do cluster | Eleito por prob. + energia |
| Lifetime | Não rastreia mortes | Rastreia por round |
| Uso ideal | Controle preciso | Simular protocolos IoT reais |

---

## Arquivos do módulo de clustering

| Arquivo | Função |
|---|---|
| `Clustering.py` | K-means, LEACH, modelo de energia, gráfico, CSV |
| `ParameterConfig.py` | Parâmetros configuráveis |
| `Node.py` | `cluster_id`, `is_ch`, `parent_ch`, `energy`, `is_alive` |
| `simulation.py` | Integração e geração dos arquivos de resultado |
| `main.py` | Interface CLI |
