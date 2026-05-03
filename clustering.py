"""
Unsupervised ML: K-Means clustering of delivery locations.

Groups deliveries into geographic clusters so each driver gets a coherent zone
instead of crisscrossing the whole city.
"""
from typing import List, Tuple, Dict
import numpy as np
from sklearn.cluster import KMeans


def cluster_deliveries(coords: List[Tuple[float, float]], n_clusters: int = 3,
                       seed: int = 42) -> Tuple[List[int], List[Tuple[float, float]]]:
    """
    Args:
        coords: list of (lat, lng) tuples
        n_clusters: number of clusters (= number of drivers, typically)

    Returns:
        labels: cluster id for each input coord (same order)
        centroids: (lat, lng) of each cluster's center
    """
    if len(coords) == 0:
        return [], []
    n_clusters = max(1, min(n_clusters, len(coords)))  # can't have more clusters than points
    X = np.array(coords)
    kmeans = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
    labels = kmeans.fit_predict(X)
    centroids = [tuple(c) for c in kmeans.cluster_centers_]
    return labels.tolist(), centroids


def assign_clusters_to_drivers(delivery_ids: List[int], coords: List[Tuple[float, float]],
                               n_drivers: int = 3) -> Dict[int, int]:
    """Map each delivery_id to a cluster_id (proxy for driver assignment)."""
    labels, _ = cluster_deliveries(coords, n_clusters=n_drivers)
    return {did: int(lbl) for did, lbl in zip(delivery_ids, labels)}
