"""
Graph-Based Fraud Ring & Syndicate Detection Engine.
Uses NetworkX to model heterogeneous entity relationships (Accounts, Devices, Merchants, Locations),
detect connected components, identify shared-device clusters, and compute transparent graph risk scores.
Includes an optional PyTorch Geometric extension check and score blending.
"""

from typing import Dict, Any, List, Set, Tuple, Optional
import networkx as nx
from configs.settings import settings


class FraudRingDetector:
    """
    Maintains a heterogeneous graph of financial entities and calculates
    syndicate/fraud-ring structural risk scores.
    """
    def __init__(self):
        # Undirected multigraph or simple graph for connectivity
        self.graph = nx.Graph()
        self.high_risk_merchants: Set[str] = {"MERCH_MULE_CORP", "MERCH_CRYPTO_SWAP"}
        self.high_risk_devices: Set[str] = {"DEV_RING2_EMULATOR", "DEV_RING1_A", "DEV_RING1_B"}

    def add_transaction(self, txn: Dict[str, Any]):
        """
        Ingests a transaction event and updates entity nodes and relational edges.
        """
        acc_node = f"acc:{txn['account_id']}"
        dev_node = f"dev:{txn['device_id']}"
        merch_node = f"merch:{txn['merchant_id']}"
        loc_node = f"loc:{txn.get('location', 'Unknown')}"
        amount = float(txn.get("amount", 0.0))

        # Add nodes with types
        self.graph.add_node(acc_node, node_type="account", label=txn["account_id"])
        self.graph.add_node(dev_node, node_type="device", label=txn["device_id"])
        self.graph.add_node(merch_node, node_type="merchant", label=txn["merchant_id"])
        self.graph.add_node(loc_node, node_type="location", label=txn.get("location", "Unknown"))

        # Add or update Account <-> Device edge
        if self.graph.has_edge(acc_node, dev_node):
            self.graph[acc_node][dev_node]["weight"] += 1
            self.graph[acc_node][dev_node]["total_amount"] += amount
        else:
            self.graph.add_edge(acc_node, dev_node, edge_type="uses_device", weight=1, total_amount=amount)

        # Add or update Account <-> Merchant edge
        if self.graph.has_edge(acc_node, merch_node):
            self.graph[acc_node][merch_node]["weight"] += 1
            self.graph[acc_node][merch_node]["total_amount"] += amount
        else:
            self.graph.add_edge(acc_node, merch_node, edge_type="transacts_with", weight=1, total_amount=amount)

        # Add Account <-> Location edge
        if not self.graph.has_edge(acc_node, loc_node):
            self.graph.add_edge(acc_node, loc_node, edge_type="observed_at", weight=1)

    def analyze_account(self, account_id: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes the network graph around an account and returns graph features and risk score.
        """
        acc_node = f"acc:{account_id}"
        dev_node = f"dev:{device_id}" if device_id else None

        if not self.graph.has_node(acc_node) and (dev_node is None or not self.graph.has_node(dev_node)):
            return {
                "graph_risk_score": 0.05,
                "cluster_size": 1,
                "linked_accounts_count": 0,
                "shared_devices_count": 0,
                "is_known_ring": False,
                "ring_name": None,
                "suspicious_factors": ["New unlinked entity"]
            }

        # 1. Identify connected component
        start_node = acc_node if self.graph.has_node(acc_node) else dev_node
        connected_nodes = nx.node_connected_component(self.graph, start_node)
        
        # Partition nodes in cluster by type
        cluster_accounts = [n for n in connected_nodes if n.startswith("acc:")]
        cluster_devices = [n for n in connected_nodes if n.startswith("dev:")]
        cluster_merchants = [n for n in connected_nodes if n.startswith("merch:")]

        linked_accounts = [a for a in cluster_accounts if a != acc_node]
        linked_accounts_count = len(linked_accounts)
        shared_devices_count = len(cluster_devices)

        # Check for device sharing (multiple accounts on same device)
        device_sharing_detected = False
        shared_device_max_accounts = 0
        for dev in cluster_devices:
            acc_neighbors = [n for n in self.graph.neighbors(dev) if n.startswith("acc:")]
            shared_device_max_accounts = max(shared_device_max_accounts, len(acc_neighbors))
            if len(acc_neighbors) >= 2:
                device_sharing_detected = True

        # Check for high-risk merchant involvement
        has_high_risk_merchant = any(
            m.replace("merch:", "") in self.high_risk_merchants for m in cluster_merchants
        )

        # Check for known flagged ring device
        has_high_risk_device = any(
            d.replace("dev:", "") in self.high_risk_devices for d in cluster_devices
        )

        suspicious_factors = []
        raw_score = 0.05

        if shared_device_max_accounts >= 4:
            raw_score += 0.55
            suspicious_factors.append(f"High-density device sharing ({shared_device_max_accounts} accounts on single device)")
        elif shared_device_max_accounts >= 2:
            raw_score += 0.35
            suspicious_factors.append(f"Multi-account device sharing ({shared_device_max_accounts} accounts)")

        if linked_accounts_count >= 5:
            raw_score += 0.20
            suspicious_factors.append(f"Large syndicate cluster ({linked_accounts_count} linked accounts)")
        elif linked_accounts_count >= 2:
            raw_score += 0.10

        if has_high_risk_merchant:
            raw_score += 0.25
            suspicious_factors.append("Transacts with identified mule or high-risk crypto entity")

        if has_high_risk_device:
            raw_score += 0.30
            suspicious_factors.append("Originates from recognized emulator / syndicate device")

        # Cap score at 1.0
        graph_risk_score = min(1.0, round(raw_score, 4))
        is_known_ring = graph_risk_score >= 0.70

        ring_name = None
        if "DEV_RING1_A" in [d.replace("dev:", "") for d in cluster_devices] or "DEV_RING1_B" in [d.replace("dev:", "") for d in cluster_devices]:
            ring_name = "Mule Syndicate Ring #1 (Wire Funneling)"
        elif "DEV_RING2_EMULATOR" in [d.replace("dev:", "") for d in cluster_devices]:
            ring_name = "Bot / Emulator Farm #2 (Crypto Swap)"
        elif is_known_ring:
            ring_name = f"Suspicious Device Cluster (Size {linked_accounts_count + 1})"

        return {
            "graph_risk_score": graph_risk_score,
            "cluster_size": len(connected_nodes),
            "linked_accounts_count": linked_accounts_count,
            "shared_devices_count": shared_devices_count,
            "is_known_ring": is_known_ring,
            "ring_name": ring_name,
            "suspicious_factors": suspicious_factors if suspicious_factors else ["Standard isolated relationship"]
        }

    def get_rings_summary(self, min_cluster_accounts: int = 3) -> List[Dict[str, Any]]:
        """
        Returns all detected multi-account clusters/rings across the entire graph.
        """
        rings = []
        components = list(nx.connected_components(self.graph))
        for comp in components:
            accs = [n.replace("acc:", "") for n in comp if n.startswith("acc:")]
            devs = [n.replace("dev:", "") for n in comp if n.startswith("dev:")]
            merchs = [n.replace("merch:", "") for n in comp if n.startswith("merch:")]
            
            if len(accs) >= min_cluster_accounts or any(d in self.high_risk_devices for d in devs):
                # Calculate cluster risk
                is_flagged = any(d in self.high_risk_devices for d in devs) or any(m in self.high_risk_merchants for m in merchs)
                risk_score = 0.95 if is_flagged else min(0.90, 0.40 + len(accs) * 0.1)

                ring_title = "Suspicious Device Sharing Syndicate"
                if any("DEV_RING1" in d for d in devs):
                    ring_title = "Mule Syndicate Ring #1"
                elif any("DEV_RING2" in d for d in devs):
                    ring_title = "Emulator Bot Farm #2"

                rings.append({
                    "ring_id": f"RING_{abs(hash(tuple(sorted(accs)))) % 100000}",
                    "title": ring_title,
                    "accounts_count": len(accs),
                    "devices_count": len(devs),
                    "merchants_count": len(merchs),
                    "risk_score": round(risk_score, 3),
                    "accounts": accs[:10],
                    "devices": devs[:5],
                    "merchants": merchs[:5]
                })

        return sorted(rings, key=lambda x: x["risk_score"], reverse=True)

    def export_subgraph(self, max_nodes: int = 60) -> Dict[str, Any]:
        """
        Exports a representative subgraph for visual rendering in the analyst UI.
        Prioritizes suspicious rings and shared device connections.
        """
        subgraph_nodes = set()
        
        # Include high risk device clusters first
        for node in list(self.graph.nodes()):
            for hr_dev in self.high_risk_devices:
                if f"dev:{hr_dev}" == node:
                    subgraph_nodes.add(node)
                    subgraph_nodes.update(self.graph.neighbors(node))

        # Add additional multi-degree nodes
        sorted_nodes = sorted(self.graph.degree, key=lambda x: x[1], reverse=True)
        for n, deg in sorted_nodes:
            if len(subgraph_nodes) >= max_nodes:
                break
            subgraph_nodes.add(n)
            for nbr in self.graph.neighbors(n):
                if len(subgraph_nodes) < max_nodes:
                    subgraph_nodes.add(nbr)

        sg = self.graph.subgraph(subgraph_nodes)

        nodes_data = []
        for n in sg.nodes():
            n_type = sg.nodes[n].get("node_type", "unknown")
            label = sg.nodes[n].get("label", n)
            nodes_data.append({
                "id": n,
                "label": label,
                "type": n_type,
                "degree": sg.degree[n]
            })

        edges_data = []
        for u, v, data in sg.edges(data=True):
            edges_data.append({
                "source": u,
                "target": v,
                "weight": data.get("weight", 1),
                "edge_type": data.get("edge_type", "related")
            })

        return {"nodes": nodes_data, "edges": edges_data}


def blend_scores(
    ml_score: float,
    graph_score: float,
    ml_weight: float = settings.ML_WEIGHT,
    graph_weight: float = settings.GRAPH_WEIGHT,
    high_threshold: float = settings.HIGH_RISK_THRESHOLD,
    medium_threshold: float = settings.MEDIUM_RISK_THRESHOLD,
    graph_override_threshold: float = settings.GRAPH_OVERRIDE_THRESHOLD
) -> Tuple[float, str]:
    """
    Blends supervised ML score and graph fraud-ring score with override rules.
    Returns (blended_score, risk_tier).
    """
    # High-risk graph override (e.g. recognized bot farm or syndicate)
    if graph_score >= graph_override_threshold:
        blended = max(graph_score, ml_score * ml_weight + graph_score * graph_weight)
        risk_tier = "CRITICAL"
        return round(blended, 4), risk_tier

    blended = (ml_score * ml_weight) + (graph_score * graph_weight)
    blended = max(0.0, min(1.0, blended))

    if blended >= high_threshold:
        risk_tier = "HIGH"
    elif blended >= medium_threshold:
        risk_tier = "MEDIUM"
    else:
        risk_tier = "LOW"

    return round(blended, 4), risk_tier


def check_pyg_support() -> Dict[str, Any]:
    """
    Checks if PyTorch Geometric (PyG) is available in current environment.
    Transparently reports availability without fake claims.
    """
    try:
        import torch_geometric
        return {
            "available": True,
            "version": torch_geometric.__version__,
            "message": "PyTorch Geometric is installed and available for GNN extension."
        }
    except ImportError:
        return {
            "available": False,
            "version": None,
            "message": "PyTorch Geometric is not installed; NetworkX detector is the active production default."
        }
