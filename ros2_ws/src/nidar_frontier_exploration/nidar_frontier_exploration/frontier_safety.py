"""Evaluate free-space connectivity and cell clearance."""

from collections import deque


def find_free_components(data, width, height):
    """Find 4-connected regions of known free space."""
    if width <= 0 or height <= 0:
        raise ValueError('Invalid map dimensions')

    if len(data) != width * height:
        raise ValueError('Map data size mismatch')

    free = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if data[y * width + x] == 0
    }

    components = []

    directions = (
        (-1, 0), (1, 0),
        (0, -1), (0, 1)
    )

    while free:
        start = min(free)
        free.remove(start)

        component = {start}
        queue = deque([start])

        while queue:
            x, y = queue.popleft()

            for dx, dy in directions:
                nx, ny = x + dx, y + dy

                neighbor = (nx, ny)

                if neighbor in free:
                    free.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)

        components.append(component)

    components.sort(key=len, reverse=True)

    return components


def clearance_filter(
    data,
    width,
    height,
    candidates,
    radius_cells
):
    """
    Retain free cells with a fully free square neighbourhood.

    Occupied, unknown and out-of-map cells are treated
    as unsafe.

    radius_cells is measured in grid cells.
    """
    if radius_cells < 0:
        raise ValueError('radius_cells must be >= 0')

    if width <= 0 or height <= 0:
        raise ValueError('Invalid map dimensions')

    if len(data) != width * height:
        raise ValueError('Map data size mismatch')

    safe = set()

    for x, y in candidates:
        if not (0 <= x < width and 0 <= y < height):
            continue

        valid = True

        for dy in range(-radius_cells, radius_cells + 1):
            for dx in range(-radius_cells, radius_cells + 1):
                nx = x + dx
                ny = y + dy

                if not (
                    0 <= nx < width
                    and 0 <= ny < height
                ):
                    valid = False
                    break

                if data[ny * width + nx] != 0:
                    valid = False
                    break

            if not valid:
                break

        if valid:
            safe.add((x, y))

    return safe
