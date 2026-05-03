"""
Reinforcement Learning: Q-learning agent for route optimization.

We treat route optimization as a Traveling-Salesman-style problem and let a
Q-learning agent discover good orderings by trial and error.

State  = (current_stop, frozenset(visited_stops))
Action = next stop to visit
Reward = -distance to next stop  (so maximizing reward = minimizing distance)

For small problems (<= ~12 stops) this converges to a near-optimal route.
For larger problems we fall back to nearest-neighbor with a 2-opt polish in
route_optimizer.py — that's what production traffic should hit.
"""
import math
import random
from typing import List, Tuple, Dict


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two (lat, lon) points."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class QLearningRouteAgent:
    """Q-learning agent that learns a good visit order over many episodes."""

    def __init__(self, alpha: float = 0.1, gamma: float = 0.9,
                 epsilon: float = 0.2, episodes: int = 500):
        self.alpha = alpha       # learning rate
        self.gamma = gamma       # discount factor
        self.epsilon = epsilon   # exploration rate
        self.episodes = episodes
        self.Q: Dict[Tuple, Dict[int, float]] = {}

    def _q(self, state, action) -> float:
        return self.Q.get(state, {}).get(action, 0.0)

    def _set_q(self, state, action, value):
        self.Q.setdefault(state, {})[action] = value

    def _best_action(self, state, valid_actions: List[int]) -> int:
        if not valid_actions:
            return -1
        if random.random() < self.epsilon:
            return random.choice(valid_actions)
        # Greedy w.r.t. current Q-values
        return max(valid_actions, key=lambda a: self._q(state, a))

    def train(self, start: Tuple[float, float], stops: List[Tuple[float, float]]) -> List[int]:
        """Train on the given problem and return the best learned order (indices into stops)."""
        n = len(stops)
        if n == 0:
            return []
        if n == 1:
            return [0]

        # Build a distance matrix once — much cheaper than recomputing each step.
        # Index 0 = start; indices 1..n = stops
        all_points = [start] + stops
        dist = [[haversine_km(*all_points[i], *all_points[j]) for j in range(n + 1)]
                for i in range(n + 1)]

        best_order, best_total = None, float("inf")

        for _ in range(self.episodes):
            visited = set()
            current = 0  # start
            order, total = [], 0.0

            while len(visited) < n:
                state = (current, frozenset(visited))
                valid = [a for a in range(1, n + 1) if a not in visited]
                action = self._best_action(state, valid)

                reward = -dist[current][action]
                visited.add(action)
                next_state = (action, frozenset(visited))

                next_valid = [a for a in range(1, n + 1) if a not in visited]
                future = max((self._q(next_state, a) for a in next_valid), default=0.0)

                old_q = self._q(state, action)
                new_q = old_q + self.alpha * (reward + self.gamma * future - old_q)
                self._set_q(state, action, new_q)

                order.append(action - 1)  # back to stops-index space
                total += dist[current][action]
                current = action

            if total < best_total:
                best_total, best_order = total, order

        return best_order or list(range(n))


def rl_optimize_route(start: Tuple[float, float],
                      stops: List[Tuple[float, float]]) -> Tuple[List[int], float]:
    """
    Public entry point. Returns (ordered_indices, total_distance_km).

    For >12 stops, training Q-learning is slow and unstable, so we fall back to
    nearest-neighbor — which is what `route_optimizer.optimize_route()` already does.
    """
    if len(stops) > 12:
        from ml.route_optimizer import nearest_neighbor_route
        return nearest_neighbor_route(start, stops)

    agent = QLearningRouteAgent(episodes=400)
    order = agent.train(start, stops)

    # Recompute total distance for the chosen order
    total = haversine_km(*start, *stops[order[0]])
    for i in range(len(order) - 1):
        total += haversine_km(*stops[order[i]], *stops[order[i + 1]])
    return order, total
