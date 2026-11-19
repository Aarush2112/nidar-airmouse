"""Detect and cluster occupancy-grid frontiers."""

from collections import deque


def detect_frontiers(data, width, height):
    """
    Detect free cells adjacent to unknown space.

    OccupancyGrid values:
      -1 = unknown
       0 = free
     100 = occupied
    """
    if width <= 0 or height <= 0:
        raise ValueError('Invalid map dimensions')

    if len(data) != width * height:
        raise ValueError('Map data size mismatch')

    frontiers = set()

    def index(x, y):
        return y * width + x

    for y in range(height):
        for x in range(width):

            if data[index(x, y)] != 0:
                continue

            neighbors = [
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1)
            ]

            for nx, ny in neighbors:
                if not (0 <= nx < width and 0 <= ny < height):
                    continue

                if data[index(nx, ny)] == -1:
                    frontiers.add((x, y))
                    break

    return frontiers


def cluster_frontiers(frontiers, min_size=1):
    """Group frontier cells using 8-connected adjacency."""
    if min_size < 1:
        raise ValueError('min_size must be >= 1')

    remaining = set(frontiers)
    clusters = []

    directions = [
        (-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
        (-1,  1), (0,  1), (1,  1)
    ]

    while remaining:
        start = min(remaining)
        remaining.remove(start)

        queue = deque([start])
        cluster = []

        while queue:
            x, y = queue.popleft()
            cluster.append((x, y))

            for dx, dy in directions:
                neighbor = (x + dx, y + dy)

                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)

        if len(cluster) >= min_size:
            clusters.append(cluster)

    clusters.sort(key=len, reverse=True)

    return clusters


def cluster_centroid(cluster):
    """
    Return the arithmetic centroid in grid coordinates.

    This is for visualization only and is not
    necessarily a safe or reachable navigation goal.
    """
    if not cluster:
        raise ValueError('Cannot calculate empty cluster centroid')

    x = sum(p[0] for p in cluster) / len(cluster)
    y = sum(p[1] for p in cluster) / len(cluster)

    return x, y
