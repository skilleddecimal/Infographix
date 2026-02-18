"""
test_phase1.py — Test Phase 1 implementation.

Generates a sample marketecture diagram to verify:
1. Layout engine works
2. Text measurement works
3. PPTX renderer produces valid output
"""

import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir.parent))  # Add Infographix dir
sys.path.insert(0, str(backend_dir))  # Add backend dir

from backend.archetypes import (
    MarketectureArchetype,
    DiagramInput,
    BlockData,
    LayerData,
    ColorPalette,
    create_simple_marketecture,
)
from backend.engine import (
    create_layout,
    quick_layout,
    render_to_pptx,
    PPTXRenderer,
)


def test_simple_marketecture():
    """Test creating a simple marketecture diagram."""
    print("=" * 60)
    print("TEST 1: Simple Marketecture with create_simple_marketecture()")
    print("=" * 60)

    layout = create_simple_marketecture(
        title="Web Application Architecture",
        layers={
            "Frontend": ["React App", "Admin Portal", "Mobile Web"],
            "API Layer": ["REST API", "GraphQL Gateway"],
            "Services": ["Auth Service", "User Service", "Order Service", "Payment Service"],
            "Data": ["PostgreSQL", "Redis Cache", "S3 Storage"],
        },
        subtitle="3-Tier Architecture with Microservices",
        cross_cutting=["Security"]
    )

    # Validate layout
    warnings = layout.validate()
    print(f"Layout generated successfully!")
    print(f"  - Elements: {len(layout.elements)}")
    print(f"  - Connectors: {len(layout.connectors)}")
    print(f"  - Title: {layout.title.text.content if layout.title else 'None'}")

    if warnings:
        print(f"  - Warnings: {warnings}")

    # Render to PPTX
    output_path = Path(__file__).parent / "output_v3_test1.pptx"
    render_to_pptx(layout, str(output_path))
    print(f"  - Saved to: {output_path}")
    print()

    return layout


def test_create_layout_api():
    """Test the create_layout() convenience API."""
    print("=" * 60)
    print("TEST 2: create_layout() API with dicts")
    print("=" * 60)

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

    print(f"Layout result:")
    print(f"  - Success: {result.success}")
    print(f"  - Archetype: {result.archetype_used}")
    print(f"  - Elements: {len(result.layout.elements)}")
    print(f"  - Connectors: {len(result.layout.connectors)}")

    if result.warnings:
        print(f"  - Warnings: {result.warnings}")

    # Render
    output_path = Path(__file__).parent / "output_v3_test2.pptx"
    render_to_pptx(result.layout, str(output_path))
    print(f"  - Saved to: {output_path}")
    print()

    return result


def test_quick_layout():
    """Test the quick_layout() convenience function."""
    print("=" * 60)
    print("TEST 3: quick_layout() for simple grids")
    print("=" * 60)

    result = quick_layout(
        title="Our Core Services",
        items=[
            "Authentication",
            "Authorization",
            "User Management",
            "Billing",
            "Notifications",
            "Analytics"
        ],
        subtitle="Platform Capabilities"
    )

    print(f"Quick layout result:")
    print(f"  - Success: {result.success}")
    print(f"  - Elements: {len(result.layout.elements)}")

    # Render
    output_path = Path(__file__).parent / "output_v3_test3.pptx"
    render_to_pptx(result.layout, str(output_path))
    print(f"  - Saved to: {output_path}")
    print()

    return result


def test_text_measurement():
    """Test text measurement and fitting."""
    print("=" * 60)
    print("TEST 4: Text Measurement")
    print("=" * 60)

    from backend.engine.text_measure import fit_text_to_width, measure_text

    # Test single line
    result = fit_text_to_width("Short Label", max_width_inches=2.0)
    print(f"'Short Label' (max 2.0 inches):")
    print(f"  - Font size: {result.font_size}pt")
    print(f"  - Lines: {result.lines}")
    print(f"  - Fits: {result.fits}")

    # Test long text
    result = fit_text_to_width(
        "This is a very long label that will need to wrap to multiple lines",
        max_width_inches=2.0
    )
    print(f"\nLong text (max 2.0 inches):")
    print(f"  - Font size: {result.font_size}pt")
    print(f"  - Lines: {result.lines}")
    print(f"  - Fits: {result.fits}")
    print()


def test_element_positions():
    """Verify element positions are computed correctly."""
    print("=" * 60)
    print("TEST 5: Element Position Verification")
    print("=" * 60)

    layout = create_simple_marketecture(
        title="Position Test",
        layers={
            "Layer A": ["Block 1", "Block 2"],
            "Layer B": ["Block 3", "Block 4", "Block 5"],
        }
    )

    print("Element positions:")
    for elem in layout.elements:
        print(f"  {elem.id}:")
        print(f"    Position: ({elem.x_inches:.2f}, {elem.y_inches:.2f})")
        print(f"    Size: {elem.width_inches:.2f} x {elem.height_inches:.2f}")
        if elem.text:
            print(f"    Text: {elem.text.lines}")
            print(f"    Font: {elem.text.font_size_pt}pt")
    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("InfographAI Phase 1 Tests")
    print("=" * 60 + "\n")

    try:
        test_text_measurement()
        test_element_positions()
        test_simple_marketecture()
        test_create_layout_api()
        test_quick_layout()

        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nGenerated PPTX files:")
        print("  - output_v3_test1.pptx (Simple marketecture)")
        print("  - output_v3_test2.pptx (create_layout API)")
        print("  - output_v3_test3.pptx (quick_layout)")
        print("\nOpen these files in PowerPoint to verify visual output.")

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
