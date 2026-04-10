"""
Clustering.py
-------------
Distance-based clustering module for LoRaSimPlus.

Features
--------
- K-means clustering (deterministic number of clusters)
- LEACH clustering (probabilistic, energy-aware, multi-round)
- Energy model per node  (Tx + Rx contributions)
- Network lifetime tracking (first-node-death and last-node-death)
- Per-cluster metrics log (CSV)
- Matplotlib visualisation of clusters and CHs

ParameterConfig globals used
------------------------------
  clustering_enabled    (bool)   - enable/disable clustering
  nrClusters            (int)    - target number of clusters (K-means)
  clustering_algorithm  (str)    - "kmeans" | "leach"
  leach_ch_prob         (float)  - desired CH fraction for LEACH (0 < p < 1)
  leach_rounds          (int)    - number of LEACH rounds to simulate
  node_initial_energy   (float)  - initial energy per node in Joules
"""

import random
import math
import os
import csv
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
# (scipy imports removed due to numpy binary incompatibility)

import ParameterConfig

# ---------------------------------------------------------------------------
# Energy model constants  (First-Order Radio model — Heinzelman 2000)
# ---------------------------------------------------------------------------
E_ELEC  = 50e-9      # J/bit — electronics energy (Tx and Rx)
E_AMP   = 100e-12    # J/bit/m² — amplifier energy (free-space)
E_DA    = 5e-9       # J/bit — data aggregation energy at CH
PACKET_BITS = 200    # default assumed packet size in bits for energy model


def _tx_energy(bits, distance):
    """Energy to transmit *bits* over *distance* metres."""
    return bits * E_ELEC + bits * E_AMP * distance ** 2


def _rx_energy(bits):
    """Energy to receive *bits*."""
    return bits * E_ELEC


def _aggregate_energy(bits):
    """Energy to aggregate one packet at the CH."""
    return bits * E_DA


# ---------------------------------------------------------------------------
# Internal geometry helpers
# ---------------------------------------------------------------------------

def _euclidean(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def _centroid(node_list):
    if not node_list:
        return 0.0, 0.0
    cx = sum(n.x for n in node_list) / len(node_list)
    cy = sum(n.y for n in node_list) / len(node_list)
    return cx, cy


# ---------------------------------------------------------------------------
# K-means clustering
# ---------------------------------------------------------------------------

def _kmeans(nodes, k, max_iter=100):
    """
    Simple K-means with random seeding.
    Returns a list of k clusters (lists of nodes).
    """
    alive = [n for n in nodes if n.is_alive]
    if k >= len(alive):
        return [[n] for n in alive]

    centroids = random.sample([(n.x, n.y) for n in alive], k)
    clusters = [[] for _ in range(k)]

    for _ in range(max_iter):
        new_clusters = [[] for _ in range(k)]
        for node in alive:
            dists = [_euclidean(node.x, node.y, cx, cy) for cx, cy in centroids]
            best = int(np.argmin(dists))
            new_clusters[best].append(node)

        for i, cluster in enumerate(new_clusters):
            if not cluster:
                new_clusters[i] = [random.choice(alive)]

        new_centroids = [_centroid(c) for c in new_clusters]
        if new_centroids == centroids:
            clusters = new_clusters
            break
        centroids = new_centroids
        clusters = new_clusters

    return clusters


# ---------------------------------------------------------------------------
# LEACH-style clustering (single round, energy-weighted election)
# ---------------------------------------------------------------------------

def _leach_elect(nodes, p, round_num):
    """
    LEACH CH election for one round.
    A node can be CH only if it has not been CH in the last 1/p rounds.
    Probability of election = p / (1 - p*(round_num mod 1/p)).
    """
    alive = [n for n in nodes if n.is_alive]
    if not alive:
        return []

    threshold_period = max(1, int(round(1.0 / p)))
    ch_nodes = []
    for n in alive:
        rounds_since_ch = round_num - n.last_ch_round
        if rounds_since_ch < threshold_period:
            continue                              # must wait
        threshold = p / (1.0 - p * (round_num % threshold_period + 1e-9))
        if random.random() < threshold:
            ch_nodes.append(n)
            n.last_ch_round = round_num

    if not ch_nodes:
        # Guarantee at least one CH
        best = max(alive, key=lambda n: n.energy)
        ch_nodes = [best]
        best.last_ch_round = round_num

    return ch_nodes


def _leach(nodes, p, round_num):
    """
    Build clusters for one LEACH round.
    Returns list of clusters (each cluster is a list of nodes).
    """
    alive = [n for n in nodes if n.is_alive]
    ch_nodes = _leach_elect(alive, p, round_num)

    ch_index = {id(n): [n] for n in ch_nodes}
    for node in alive:
        if node in ch_nodes:
            continue
        nearest = min(ch_nodes, key=lambda ch: _euclidean(node.x, node.y, ch.x, ch.y))
        ch_index[id(nearest)].append(node)

    return list(ch_index.values())


# ---------------------------------------------------------------------------
# CH selection helpers
# ---------------------------------------------------------------------------

def _select_ch_kmeans(cluster):
    """For K-means: node closest to centroid becomes CH."""
    cx, cy = _centroid(cluster)
    return min(cluster, key=lambda n: _euclidean(n.x, n.y, cx, cy))


def _select_ch_leach(cluster):
    """For LEACH: CH is the node that was elected (highest energy)."""
    # The first node in each LEACH cluster group is the elected CH
    return cluster[0]


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

CLUSTER_COLORS = [
    '#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4',
    '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990',
    '#dcbeff', '#9A6324', '#fffac8', '#800000', '#aaffc3',
]


def plot_clusters(clusters, cluster_heads, folder_path, file_name, gateways=None, show=True):
    """
    Draw a scatter plot of the cluster layout and save to PNG.
    """
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')

    legend_patches = []

    for cid, cluster in enumerate(clusters):
        color = CLUSTER_COLORS[cid % len(CLUSTER_COLORS)]
        ch = cluster_heads[cid]

        # Draw cluster members
        for node in cluster:
            if node is ch:
                continue
            ax.scatter(node.x, node.y, c=color, s=35, zorder=3,
                       edgecolors='black', linewidths=0.3, alpha=0.85)
            # Line from CM to CH
            ax.plot([node.x, ch.x], [node.y, ch.y],
                    color=color, linewidth=0.5, alpha=0.35, zorder=2)

        # Draw CH
        ax.scatter(ch.x, ch.y, c='yellow', s=160, marker='*', zorder=5,
                   edgecolors='black', linewidths=0.6)
        ax.annotate(f'CH{cid}', (ch.x, ch.y),
                    textcoords='offset points', xytext=(6, 4),
                    fontsize=7, color='black', fontweight='bold')

        legend_patches.append(mpatches.Patch(color=color, label=f'Cluster {cid}'))

    # Draw gateways
    if gateways:
        for gw in gateways:
            ax.scatter(gw.x, gw.y, c='black', s=250, marker='^', zorder=6,
                       edgecolors='red', linewidths=1.5)
            ax.annotate(f'GW{gw.id}', (gw.x, gw.y),
                        textcoords='offset points', xytext=(6, 4),
                        fontsize=8, color='red', fontweight='bold')

    # CH legend entry
    legend_patches.append(mpatches.Patch(color='yellow', label='Cluster Head ★'))

    ax.legend(handles=legend_patches, loc='upper right',
              fontsize=8, framealpha=0.6, facecolor='white', labelcolor='black')
    ax.set_title('LoRaSimPlus — Cluster Layout', color='black', fontsize=13, pad=12)
    ax.set_xlabel('X (m)', color='black')
    ax.set_ylabel('Y (m)', color='black')
    ax.tick_params(colors='black')
    for spine in ax.spines.values():
        spine.set_edgecolor('black')

    plt.tight_layout()
    plot_path = os.path.join(folder_path, file_name + '-clusters.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    print(f'[Clustering] Cluster plot saved to {plot_path}')
    return plot_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class Clustering:
    """
    Main clustering facade used by simulation.py.

    Energy model
    ~~~~~~~~~~~~
    Each node carries `node.energy` (Joules).  On each round:
      - Every CM pays  Tx(CM→CH) + Rx overhead
      - Each CH pays   Rx * n_members  +  Aggregate * n_members + Tx(CH→GW)

    Network Lifetime
    ~~~~~~~~~~~~~~~~
    - first_death_round  : round when the first node dies
    - last_death_round   : round when the last node dies (network lifetime)
    """

    def __init__(self, algorithm="kmeans", nr_clusters=5,
                 leach_ch_prob=0.05, leach_rounds=20,
                 node_initial_energy=1.0, ch_selection_method="default"):
        self.algorithm = algorithm
        self.nr_clusters = nr_clusters
        self.leach_ch_prob = leach_ch_prob
        self.leach_rounds = leach_rounds
        self.node_initial_energy = node_initial_energy
        self.ch_selection_method = ch_selection_method

        # Results
        self.clusters = []
        self.cluster_heads = []
        self.round_metrics = []       # list of dicts, one per round
        self.first_death_round = None
        self.last_death_round = None
        self.total_rounds = 0

    # ------------------------------------------------------------------
    def _init_energy(self, nodes):
        """Initialise energy fields on each node."""
        for node in nodes:
            node.energy = self.node_initial_energy
            node.initial_energy = self.node_initial_energy
            node.is_alive = True
            node.last_ch_round = -9999   # LEACH: rounds since last CH role

    # ------------------------------------------------------------------
    def _consume_round_energy(self, clusters, cluster_heads, gateways):
        """
        Deduct energy for one round from all alive nodes.
        Uses the First-Order Radio model.
        """
        for cid, cluster in enumerate(clusters):
            ch = cluster_heads[cid]
            gw = gateways[0] if gateways else None

            # Distance CH → Gateway
            d_ch_gw = (_euclidean(ch.x, ch.y, gw.x, gw.y)
                       if gw else 1000.0)  # fallback if no GW provided

            # CH consumes: receive from members + aggregation + transmit to GW
            n_members = len(cluster)
            ch_rx_cost  = _rx_energy(PACKET_BITS) * n_members
            ch_agg_cost = _aggregate_energy(PACKET_BITS) * n_members
            ch_tx_cost  = _tx_energy(PACKET_BITS, d_ch_gw)
            ch.energy = max(0.0, ch.energy - (ch_rx_cost + ch_agg_cost + ch_tx_cost))

            for node in cluster:
                if node is ch:
                    continue
                d_cm_ch = _euclidean(node.x, node.y, ch.x, ch.y)
                cm_tx_cost = _tx_energy(PACKET_BITS, d_cm_ch)
                cm_rx_cost = _rx_energy(PACKET_BITS)   # receive CH broadcast
                node.energy = max(0.0, node.energy - (cm_tx_cost + cm_rx_cost))

        # Mark dead nodes
        for node in (n for c in clusters for n in c):
            if node.energy <= 0 and node.is_alive:
                node.is_alive = False

    # ------------------------------------------------------------------
    def _assign_roles(self, clusters):
        """Set cluster_id, is_ch, parent_ch fields on every node."""
        heads = []
        for cid, cluster in enumerate(clusters):
            if self.ch_selection_method == "centroid":
                ch = _select_ch_kmeans(cluster) # already does centroid
            elif self.ch_selection_method == "energy_proximity":
                # We reuse the specific logic here or call our new method
                # (simplified: we'll call a per-cluster version)
                ch = self._select_ch_weighted_centroid(cluster)
            elif self.algorithm == "leach" and self.ch_selection_method == "default":
                ch = _select_ch_leach(cluster)
            else:
                # Default to centroid for kmeans or if explicitly requested
                ch = _select_ch_kmeans(cluster)
                
            heads.append(ch)
            for node in cluster:
                node.cluster_id = cid
                if node is ch:
                    node.is_ch = True
                    node.parent_ch = None
                else:
                    node.is_ch = False
                    node.parent_ch = ch
        return heads

    # ------------------------------------------------------------------
    def _run_kde_kmeans(self, nodes, gateways):
        """KDE-KMeans: Dynamic K estimation + RAMO CH selection."""
        # 1. Estimate K using KDE (manual implementation)
        suggested_k = self._estimate_k_kde(nodes)
        print(f"[KDE] Estimated optimal K: {suggested_k}")
        
        # 2. Run Clustering with suggested K
        self.clusters = _kmeans(nodes, suggested_k)
        
        # 3. Assign roles using RAMO (Relief-Aware Multi-Objective)
        # Calculate manual density for all nodes
        bandwidth = ParameterConfig.radius / 5.0 # heuristic bandwidth
        coords = np.array([[n.x, n.y] for n in nodes])
        for node in nodes:
            dists_sq = (coords[:,0] - node.x)**2 + (coords[:,1] - node.y)**2
            node.density = np.sum(np.exp(-0.5 * dists_sq / (bandwidth**2)))
            
        self.cluster_heads = self._assign_roles_ramo(self.clusters)
        
        # 4. Energy and metrics
        self._consume_round_energy(self.clusters, self.cluster_heads, gateways)
        self.total_rounds = 1
        self._record_final_metrics(nodes)

    def _estimate_k_kde(self, nodes):
        """Suggest K based on number of manual density peaks."""
        if len(nodes) < 10: return self.nr_clusters
        
        # Use a grid-based approach to find peaks
        bandwidth = ParameterConfig.radius / 5.0
        grid_size = 40
        x = np.linspace(-ParameterConfig.radius, ParameterConfig.radius, grid_size)
        y = np.linspace(-ParameterConfig.radius, ParameterConfig.radius, grid_size)
        X, Y = np.meshgrid(x, y)
        grid_coords = np.vstack([X.ravel(), Y.ravel()]).T
        node_coords = np.array([[n.x, n.y] for n in nodes])
        
        Z = np.zeros(grid_coords.shape[0])
        for i, g_coord in enumerate(grid_coords):
            dists_sq = (node_coords[:,0] - g_coord[0])**2 + (node_coords[:,1] - g_coord[1])**2
            Z[i] = np.sum(np.exp(-0.5 * dists_sq / (bandwidth**2)))
        
        Z = Z.reshape(X.shape)
        
        # Simple peak detection: count local maxima on the grid
        k = 0
        for i in range(1, grid_size-1):
            for j in range(1, grid_size-1):
                val = Z[i,j]
                if (val > Z[i-1,j] and val > Z[i+1,j] and 
                    val > Z[i,j-1] and val > Z[i,j+1] and
                    val > np.mean(Z)):
                    k += 1
        
        return max(2, min(k, 15)) # Constraint K between 2 and 15

    def _assign_roles_ramo(self, clusters):
        """RAMO CH Selection: Energy + Density + Weighted Centroid."""
        heads = []
        for cid, cluster in enumerate(clusters):
            if not cluster: continue
            
            # 1. Weighted Centroid (Weak-Node Attraction)
            total_w = 0.0
            sum_x = 0.0
            sum_y = 0.0
            for n in cluster:
                # weight increases as energy decreases
                w = 1.1 - (n.energy / n.initial_energy)
                sum_x += n.x * w
                sum_y += n.y * w
                total_w += w
            w_centroid_x = sum_x / total_w
            w_centroid_y = sum_y / total_w
            
            # 2. Score candidates
            best_node = None
            max_score = -float('inf')
            
            cluster_alive = [n for n in cluster if n.is_alive]
            if not cluster_alive:
                best_node = cluster[0]
            else:
                max_e = max(n.energy for n in cluster_alive) if cluster_alive else 1
                max_d = max(n.density for n in cluster_alive) if cluster_alive else 1
                
                for node in cluster_alive:
                    dist = np.sqrt((node.x - w_centroid_x)**2 + (node.y - w_centroid_y)**2)
                    norm_dist = dist / (2 * ParameterConfig.radius) 
                    
                    score = (0.4 * (node.energy/max_e) + 
                             0.3 * (node.density/max_d) - 
                             0.3 * norm_dist)
                    
                    if score > max_score:
                        max_score = score
                        best_node = node
            
            if not best_node: best_node = cluster[0]
            
            heads.append(best_node)
            for node in cluster:
                node.cluster_id = cid
                if node is best_node:
                    node.is_ch = True
                    node.parent_ch = None
                else:
                    node.is_ch = False
                    node.parent_ch = best_node
                    
        return heads

    def _record_final_metrics(self, nodes):
        """Helper to avoid code duplication in run methods."""
        alive_count = sum(1 for n in nodes if n.is_alive)
        avg_energy  = (sum(n.energy for n in nodes if n.is_alive) / alive_count
                       if alive_count else 0.0)

        self.round_metrics.append({
            'round': 1,
            'n_clusters': len(self.clusters),
            'n_ch': len(self.cluster_heads),
            'alive_nodes': alive_count,
            'dead_nodes': len(nodes) - alive_count,
            'avg_residual_energy_J': round(avg_energy, 6),
            'total_residual_energy_J': round(sum(n.energy for n in nodes), 6),
        })

        if alive_count < len(nodes) and self.first_death_round is None:
            self.first_death_round = 1

    # ------------------------------------------------------------------
    def _select_chs_by_energy_proximity(self):
        """
        Multi-objective: Move CH closer to nodes with LOW energy (inverse weight).
        Pick CH from nodes with energy ABOVE cluster average.
        """
        heads = []
        for cluster in self.clusters:
            if not cluster: continue
            
            # 1. Calculate weighted centroid (higher weight for low energy nodes)
            # weight_i = 1.05 - (current_energy / initial_energy)
            total_w = 0.0
            sum_x = 0.0
            sum_y = 0.0
            cluster_energies = []
            
            for node in cluster:
                # Use a small epsilon to avoid weight 0
                w = 1.1 - (node.energy / node.initial_energy)
                sum_x += node.x * w
                sum_y += node.y * w
                total_w += w
                cluster_energies.append(node.energy)
            
            w_centroid_x = sum_x / total_w
            w_centroid_y = sum_y / total_w
            avg_energy = sum(cluster_energies) / len(cluster_energies)
            
            # 2. Candidate pool: Nodes with energy >= cluster average
            # (or at least 30% left to be a reliable CH)
            candidates = [n for n in cluster if n.is_alive and n.energy >= avg_energy]
            if not candidates:
                candidates = [n for n in cluster if n.is_alive] # Fallback
                
            # 3. Pick candidate closest to the weighted centroid
            best_node = candidates[0]
            min_dist = float('inf')
            for node in candidates:
                d = np.sqrt((node.x - w_centroid_x)**2 + (node.y - w_centroid_y)**2)
                if d < min_dist:
                    min_dist = d
                    best_node = node
            
            heads.append(best_node)
            best_node.is_ch = True
        return heads

    # ------------------------------------------------------------------
    def run(self, nodes, gateways=None):
        """
        Partition nodes into clusters, run energy simulation for
        `leach_rounds` rounds (LEACH) or a single pass (K-means).

        Parameters
        ----------
        nodes    : list of myNode
        gateways : list of myBS (used for CH→GW energy calculation)
        """
        self._init_energy(nodes)

        if self.algorithm == "kmeans":
            self._run_kmeans(nodes, gateways)
        elif self.algorithm == "kde_kmeans":
            self._run_kde_kmeans(nodes, gateways)
        elif self.algorithm == "leach":
            self._run_leach(nodes, gateways)
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm!r}")

        self._print_summary()

    # ------------------------------------------------------------------
    def _run_kmeans(self, nodes, gateways):
        """K-means: single clustering pass + one round of energy."""
        self.clusters = _kmeans(nodes, self.nr_clusters)
        self.cluster_heads = self._assign_roles(self.clusters)
        self._consume_round_energy(self.clusters, self.cluster_heads, gateways)
        self.total_rounds = 1

        alive_count = sum(1 for n in nodes if n.is_alive)
        avg_energy  = (sum(n.energy for n in nodes if n.is_alive) / alive_count
                       if alive_count else 0.0)

        self.round_metrics.append({
            'round': 1,
            'n_clusters': len(self.clusters),
            'n_ch': len(self.cluster_heads),
            'alive_nodes': alive_count,
            'dead_nodes': len(nodes) - alive_count,
            'avg_residual_energy_J': round(avg_energy, 6),
            'total_residual_energy_J': round(sum(n.energy for n in nodes), 6),
        })

        if alive_count < len(nodes) and self.first_death_round is None:
            self.first_death_round = 1
        if alive_count == 0:
            self.last_death_round = 1

    # ------------------------------------------------------------------
    def _run_leach(self, nodes, gateways):
        """LEACH: multi-round simulation with energy decay."""
        all_nodes = list(nodes)

        for r in range(1, self.leach_rounds + 1):
            alive = [n for n in all_nodes if n.is_alive]
            if not alive:
                break

            clusters = _leach(alive, self.leach_ch_prob, r)
            heads = self._assign_roles(clusters)
            self._consume_round_energy(clusters, heads, gateways)

            # Track first / last death
            prev_alive = sum(1 for n in all_nodes if n.is_alive)
            alive_now  = sum(1 for n in all_nodes if n.is_alive)
            if alive_now < len(all_nodes) and self.first_death_round is None:
                self.first_death_round = r
            if alive_now == 0:
                self.last_death_round = r

            avg_energy = (sum(n.energy for n in all_nodes if n.is_alive) / alive_now
                          if alive_now else 0.0)

            self.round_metrics.append({
                'round': r,
                'n_clusters': len(clusters),
                'n_ch': len(heads),
                'alive_nodes': alive_now,
                'dead_nodes': len(all_nodes) - alive_now,
                'avg_residual_energy_J': round(avg_energy, 6),
                'total_residual_energy_J': round(
                    sum(n.energy for n in all_nodes), 6),
            })

            # Keep last round's clustering as the final state
            self.clusters = clusters
            self.cluster_heads = heads
            self.total_rounds = r

            if alive_now == 0:
                self.last_death_round = r
                break

        # If all nodes still alive after all rounds
        if self.last_death_round is None and self.first_death_round is None:
            self.first_death_round = self.total_rounds
            
    # ------------------------------------------------------------------
    def cross_validate(self, nodes, n_folds=5):
        """
        Perform K-Fold Cross-Validation for clustering stability.
        Returns a dictionary with average performance metrics.
        """
        if len(nodes) < n_folds * 2:
            return {"error": "Not enough nodes for K-fold"}
            
        random.shuffle(nodes)
        self._init_energy(nodes) # Ensure is_alive and energy fields exist
        folds = np.array_split(nodes, n_folds)
        results = []
        
        print(f"\n[Validation] Starting {n_folds}-Fold Cross-Validation...")
        for i in range(n_folds):
            # Split into training and test sets
            test_set = folds[i]
            train_set = [n for j, f in enumerate(folds) if j != i for n in f]
            
            # 1. 'Train' on train_set (find K and Cluster Centers)
            # Use original algorithm settings
            temp_nodes = [n for n in train_set] # clones not needed as we only read
            suggested_k = self._estimate_k_kde(temp_nodes)
            
            # Use internal _kmeans instead of sklearn for environment compatibility
            clusters_train = _kmeans(train_set, suggested_k)
            centers = []
            for c in clusters_train:
                if c:
                    centers.append([np.mean([n.x for n in c]), np.mean([n.y for n in c])])
            centers = np.array(centers)
            
            # 2. 'Evaluate' on test_set
            # Metrics: WCSS (Inertia) on test set
            coords_test = np.array([[n.x, n.y] for n in test_set])
            test_inertia = 0.0
            for pt in coords_test:
                dists_sq = np.sum((centers - pt)**2, axis=1)
                test_inertia += np.min(dists_sq)
            
            avg_inertia = test_inertia / len(test_set)
            results.append({
                'fold': i+1,
                'k': suggested_k,
                'avg_inertia': avg_inertia
            })
            print(f"  Fold {i+1}: K={suggested_k}, Avg Inertia={avg_inertia:.2f}")

        # Final average
        avg_k = sum(r['k'] for r in results) / n_folds
        final_inertia = sum(r['avg_inertia'] for r in results) / n_folds
        print(f"[Validation] CV Result: Avg K={avg_k:.1f}, Avg Test Inertia={final_inertia:.2f}\n")
        
        return {
            'n_folds': n_folds,
            'avg_k': avg_k,
            'avg_test_inertia': final_inertia,
            'fold_details': results
        }

    # ------------------------------------------------------------------
    def save_metrics(self, folder_path, file_name):
        """
        Write two CSV files:
          1. <file>-cluster-rounds.csv  — per-round summary
          2. <file>-cluster-nodes.csv   — per-node final state
        """
        # Per-round metrics
        rounds_path = os.path.join(folder_path, file_name + '-cluster-rounds.csv')
        if self.round_metrics:
            with open(rounds_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.round_metrics[0].keys())
                writer.writeheader()
                writer.writerows(self.round_metrics)
            print(f'[Clustering] Round metrics → {rounds_path}')

        # Per-node final state
        nodes_path = os.path.join(folder_path, file_name + '-cluster-nodes.csv')
        all_nodes = list({id(n): n
                          for cluster in self.clusters
                          for n in cluster}.values())
        with open(nodes_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['node_id', 'x', 'y', 'cluster_id',
                             'role', 'residual_energy_J', 'alive'])
            for node in all_nodes:
                role  = 'CH' if node.is_ch else 'CM'
                alive = 'YES' if node.is_alive else 'NO'
                writer.writerow([node.id, node.x, node.y,
                                 node.cluster_id, role,
                                 round(node.energy, 6), alive])
        print(f'[Clustering] Node metrics   → {nodes_path}')

        return rounds_path, nodes_path

    # ------------------------------------------------------------------
    def save_performance_metrics(self, folder_path, file_name, payload_size):
        """
        Save per-cluster performance metrics (PDR, Bits/Joule).
        """
        perf_path = os.path.join(folder_path, file_name + '-cluster-performance.csv')
        
        # Group nodes by cluster
        cluster_data = {}
        for cid in range(len(self.clusters)):
            cluster_data[cid] = {
                'sent': 0,
                'received': 0,
                'lost': 0,
                'collided': 0,
                'energy_J': 0.0,
                'time_tx_ms': 0.0,
                'time_rx_ms': 0.0,
                'time_sleep_ms': 0.0,
                'acks': 0,
                'nodes': []
            }

        # Collect all nodes
        all_nodes = [n for cluster in self.clusters for n in cluster]
        for node in all_nodes:
            cid = node.cluster_id
            if cid in cluster_data:
                cluster_data[cid]['sent'] += node.sent
                cluster_data[cid]['received'] += node.node_received
                cluster_data[cid]['lost'] += node.node_lost
                cluster_data[cid]['collided'] += node.node_collided
                cluster_data[cid]['energy_J'] += node.node_total_energy
                cluster_data[cid]['time_tx_ms'] += node.time_tx
                cluster_data[cid]['time_rx_ms'] += node.time_rx
                cluster_data[cid]['time_sleep_ms'] += node.time_sleep
                cluster_data[cid]['acks'] += node.node_acks_received
                cluster_data[cid]['nodes'].append(node)

        with open(perf_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['cluster_id', 'sent', 'received', 'lost', 'collided', 'acks',
                             'PDR', 'energy_J', 'bits_per_joule', 
                             'avg_tx_ms', 'avg_rx_ms', 'avg_sleep_ms', 'duty_cycle_avg'])
            for cid, data in cluster_data.items():
                node_count = len(data['nodes'])
                pdr = (data['received'] / data['sent']) if data['sent'] > 0 else 0.0
                bits = data['received'] * payload_size * 8
                bpj = (bits / data['energy_J']) if data['energy_J'] > 0 else 0.0
                
                avg_tx = data['time_tx_ms'] / node_count if node_count > 0 else 0.0
                avg_rx = data['time_rx_ms'] / node_count if node_count > 0 else 0.0
                avg_sleep = data['time_sleep_ms'] / node_count if node_count > 0 else 0.0
                # Duty Cycle = TX / (TX + RX + Sleep)
                total_time = data['time_tx_ms'] + data['time_rx_ms'] + data['time_sleep_ms']
                dc = (data['time_tx_ms'] / total_time) if total_time > 0 else 0.0

                writer.writerow([cid, data['sent'], data['received'], data['lost'], data['collided'], data['acks'],
                                 round(pdr, 4), round(data['energy_J'], 6), round(bpj, 4),
                                 round(avg_tx, 2), round(avg_rx, 2), round(avg_sleep, 2), round(dc, 6)])
        
        print(f'[Clustering] Performance metrics → {perf_path}')
        return perf_path

    # ------------------------------------------------------------------
    def plot(self, folder_path, file_name, gateways=None, show=True):
        """Render and save the cluster layout plot."""
        return plot_clusters(self.clusters, self.cluster_heads,
                             folder_path, file_name, gateways, show=show)

    # ------------------------------------------------------------------
    def distance_cm_to_ch(self, node):
        """Return Euclidean distance from a CM to its CH (0 for CHs)."""
        if node.is_ch or node.parent_ch is None:
            return 0.0
        return _euclidean(node.x, node.y, node.parent_ch.x, node.parent_ch.y)

    # ------------------------------------------------------------------
    def _print_summary(self):
        print(f'\n{"="*55}')
        print(f'  Clustering Summary — Algorithm: {self.algorithm.upper()}')
        print(f'{"="*55}')
        print(f'  Total rounds simulated : {self.total_rounds}')
        print(f'  Final clusters         : {len(self.clusters)}')
        print(f'  Final CHs              : {len(self.cluster_heads)}')
        if self.first_death_round is not None:
            print(f'  First node death       : round {self.first_death_round}')
        else:
            print(f'  First node death       : none (all alive)')
        if self.last_death_round is not None:
            print(f'  Network lifetime       : {self.last_death_round} rounds'
                  f'  (last node died)')
        else:
            print(f'  Network lifetime       : > {self.total_rounds} rounds'
                  f'  (network alive)')
        if self.round_metrics:
            last = self.round_metrics[-1]
            print(f'  Alive nodes (final)    : {last["alive_nodes"]}')
            print(f'  Avg residual energy    : {last["avg_residual_energy_J"]:.4e} J')
        print(f'{"="*55}')
        for i, ch in enumerate(self.cluster_heads):
            members = [n.id for n in self.clusters[i] if not n.is_ch]
            alive_m = sum(1 for n in self.clusters[i] if n.is_alive)
            print(f'  Cluster {i:2d}: CH=node{ch.id:<4d}'
                  f'  Members={members}  Alive={alive_m}')
        print()
