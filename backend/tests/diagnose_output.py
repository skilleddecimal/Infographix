"""
Diagnose the layout output to find issues.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir.parent))
sys.path.insert(0, str(backend_dir))

from backend.archetypes import create_simple_marketecture
from backend.engine import create_layout


def diagnose_test1():
    """Diagnose Test 1 - Simple Marketecture."""
    print("=" * 70)
    print("TEST 1 DIAGNOSIS: Simple Marketecture")
    print("=" * 70)

    layout = create_simple_marketecture(
        title="Web Application Architecture",
        layers={
            "Frontend": ["React App", "Admin Portal", "Mobile Web"],
            "API Layer": ["REST API", "GraphQL Gateway"],
            "Services": ["Auth Service", "User Service", "Order Service", "Payment Service"],
            "Data": ["PostgreSQL", "Redis Cache", "S3 Storage"],
        },
        subtitle="3-Tier Architecture with Microservices",
    )

    print(f"\nSlide: {layout.slide_width_inches}\" x {layout.slide_height_inches}\"")
    print(f"Title: {layout.title.text.content if layout.title else 'None'}")
    print(f"Elements: {len(layout.elements)}")

    # Group elements by type
    labels = []
    blocks = []
    bands = []

    for elem in layout.elements:
        if 'label_' in elem.id:
            labels.append(elem)
        elif elem.element_type.value == 'band':
            bands.append(elem)
        else:
            blocks.append(elem)

    print(f"\n--- LAYER LABELS ({len(labels)}) ---")
    for elem in labels:
        text = elem.text
        print(f"  {elem.id}:")
        print(f"    Position: x={elem.x_inches:.2f}, y={elem.y_inches:.2f}")
        print(f"    Size: {elem.width_inches:.2f}\" x {elem.height_inches:.2f}\"")
        print(f"    Text: '{text.content}' @ {text.font_size_pt}pt")
        print(f"    Text lines: {text.lines}")
        print(f"    Alignment: {text.alignment}")

    print(f"\n--- BLOCKS ({len(blocks)}) ---")
    # Group blocks by y-position (layer)
    blocks_by_y = {}
    for elem in blocks:
        y_key = round(elem.y_inches, 1)
        if y_key not in blocks_by_y:
            blocks_by_y[y_key] = []
        blocks_by_y[y_key].append(elem)

    for y_pos in sorted(blocks_by_y.keys()):
        print(f"\n  Layer at y={y_pos}\":")
        for elem in blocks_by_y[y_pos]:
            text = elem.text
            print(f"    {elem.id}: '{text.content}' @ {text.font_size_pt}pt")
            print(f"      Position: ({elem.x_inches:.2f}, {elem.y_inches:.2f})")
            print(f"      Size: {elem.width_inches:.2f}\" x {elem.height_inches:.2f}\"")


def diagnose_test2():
    """Diagnose Test 2 - Connectors."""
    print("\n" + "=" * 70)
    print("TEST 2 DIAGNOSIS: Connectors")
    print("=" * 70)

    result = create_layout(
        title="Microservices Platform",
        subtitle="Event-Driven Architecture",
        blocks=[
            {"id": "gateway", "label": "API Gateway", "layer_id": "edge"},
            {"id": "web", "label": "Web Frontend", "layer_id": "edge"},
            {"id": "auth", "label": "Auth Service", "layer_id": "services"},
            {"id": "users", "label": "User Service", "layer_id": "services"},
            {"id": "orders", "label": "Order Service", "layer_id": "services"},
            {"id": "kafka", "label": "Kafka", "layer_id": "messaging"},
            {"id": "postgres", "label": "PostgreSQL", "layer_id": "data"},
            {"id": "mongo", "label": "MongoDB", "layer_id": "data"},
        ],
        layers=[
            {"id": "edge", "label": "Edge Layer"},
            {"id": "services", "label": "Microservices"},
            {"id": "messaging", "label": "Event Bus"},
            {"id": "data", "label": "Data Stores"},
        ],
        connectors=[
            {"from_id": "gateway", "to_id": "auth"},
            {"from_id": "gateway", "to_id": "users"},
            {"from_id": "auth", "to_id": "kafka"},
            {"from_id": "users", "to_id": "postgres"},
            {"from_id": "orders", "to_id": "mongo"},
        ]
    )

    layout = result.layout

    # Build element position lookup
    elem_lookup = {}
    for elem in layout.elements:
        elem_lookup[elem.id] = elem

    print(f"\n--- BLOCKS ---")
    for elem in layout.elements:
        if elem.text and 'label_' not in elem.id:
            print(f"  {elem.id}: '{elem.text.content}'")
            print(f"    Bounds: x=[{elem.x_inches:.2f}, {elem.right_edge:.2f}], y=[{elem.y_inches:.2f}, {elem.bottom_edge:.2f}]")
            print(f"    Center: ({elem.center_x:.2f}, {elem.center_y:.2f})")

    print(f"\n--- CONNECTORS ({len(layout.connectors)}) ---")
    for conn in layout.connectors:
        from_elem = elem_lookup.get(conn.from_element_id)
        to_elem = elem_lookup.get(conn.to_element_id)

        print(f"\n  {conn.from_element_id} -> {conn.to_element_id}:")
        print(f"    Start: ({conn.start_x:.2f}, {conn.start_y:.2f})")
        print(f"    End: ({conn.end_x:.2f}, {conn.end_y:.2f})")

        if from_elem:
            print(f"    From block bounds: x=[{from_elem.x_inches:.2f}, {from_elem.right_edge:.2f}], y=[{from_elem.y_inches:.2f}, {from_elem.bottom_edge:.2f}]")
            # Check if start point is on block edge
            on_left = abs(conn.start_x - from_elem.x_inches) < 0.01
            on_right = abs(conn.start_x - from_elem.right_edge) < 0.01
            on_top = abs(conn.start_y - from_elem.y_inches) < 0.01
            on_bottom = abs(conn.start_y - from_elem.bottom_edge) < 0.01
            if on_left or on_right or on_top or on_bottom:
                print(f"    Start is on edge: OK")
            else:
                print(f"    WARNING: Start NOT on block edge!")

        if to_elem:
            print(f"    To block bounds: x=[{to_elem.x_inches:.2f}, {to_elem.right_edge:.2f}], y=[{to_elem.y_inches:.2f}, {to_elem.bottom_edge:.2f}]")
            # Check if end point is on block edge
            on_left = abs(conn.end_x - to_elem.x_inches) < 0.01
            on_right = abs(conn.end_x - to_elem.right_edge) < 0.01
            on_top = abs(conn.end_y - to_elem.y_inches) < 0.01
            on_bottom = abs(conn.end_y - to_elem.bottom_edge) < 0.01
            if on_left or on_right or on_top or on_bottom:
                print(f"    End is on edge: OK")
            else:
                print(f"    WARNING: End NOT on block edge!")


if __name__ == "__main__":
    diagnose_test1()
    diagnose_test2()
