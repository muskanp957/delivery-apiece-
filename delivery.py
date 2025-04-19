from fastapi import FastAPI, HTTPException
from typing import Dict, List, Tuple
from itertools import permutations
from fastapi.responses import RedirectResponse

app = FastAPI()

# ✅ Root route ("/") - returns a helpful message
@app.get("/")
def root():
    return {"message": "Welcome! Use POST /calculate with your product order."}

# ✅ Favicon route - returns 204 (no content)
@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="https://fastapi.tiangolo.com/img/favicon.png")
    # or alternatively just:
    # from fastapi.responses import Response
    # return Response(status_code=204)

# Warehouse stock: product -> (center, weight in kg)
product_data = {
    "A": ("C1", 3), "B": ("C1", 2), "C": ("C1", 8),
    "D": ("C2", 12), "E": ("C2", 25), "F": ("C2", 15),
    "G": ("C3", 0.5), "H": ("C3", 1), "I": ("C3", 2)
}

# Distances between locations
distances = {
    ("C1", "L1"): 3, ("C2", "L1"): 2.5, ("C3", "L1"): 2,
    ("C1", "C2"): 4, ("C2", "C3"): 3, ("C1", "C3"): 7
}
# Make bidirectional
for (a, b), d in list(distances.items()):
    distances[(b, a)] = d

# Cost calculation based on weight
def cost_per_distance(weight: float) -> float:
    if weight <= 5:
        return 10
    extra = weight - 5
    blocks = int((extra + 4.9999) // 5)
    return 10 + blocks * 8

# Group ordered products by warehouse
def group_products_by_center(order: Dict[str, int]) -> Dict[str, List[Tuple[str, int, float]]]:
    grouped = {"C1": [], "C2": [], "C3": []}
    for prod, qty in order.items():
        if prod not in product_data:
            raise ValueError(f"Product {prod} not found.")
        center, weight = product_data[prod]
        grouped[center].append((prod, qty, weight))
    return grouped

# Generate delivery/pickup route sequences
def generate_sequences(start: str, centers: List[str]) -> List[List[str]]:
    centers = list(set(centers))
    centers.remove(start)
    all_routes = []
    for perm in permutations(centers):
        route = [start]
        for c in perm:
            route += ["L1", c]
        route.append("L1")
        all_routes.append(route)
    return all_routes

# Calculate cost for one specific route
def calculate_route_cost(route: List[str], grouped: Dict[str, List[Tuple[str, int, float]]]) -> float:
    total_cost = 0.0
    carried_items = []

    for i in range(1, len(route)):
        from_loc, to_loc = route[i - 1], route[i]
        if from_loc in grouped:
            for _, qty, wt in grouped[from_loc]:
                carried_items += [(wt, from_loc)] * qty

        weight = sum(w for w, _ in carried_items)
        per_unit = cost_per_distance(weight)
        total_cost += distances[(from_loc, to_loc)] * per_unit

        if to_loc == "L1":
            carried_items = []

    return total_cost

# Find minimum delivery cost across all routes
def compute_min_cost(order: Dict[str, int]) -> float:
    grouped = group_products_by_center(order)
    centers = [c for c, items in grouped.items() if items]
    min_cost = float("inf")

    for start in centers:
        routes = generate_sequences(start, centers)
        for route in routes:
            cost = calculate_route_cost(route, grouped)
            if cost < min_cost:
                min_cost = cost

    return min_cost

# POST endpoint to calculate cost
@app.post("/calculate")
async def calculate_cost(order: Dict[str, int]):
    try:
        cost = compute_min_cost(order)
        return {"minimum_cost": cost}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
