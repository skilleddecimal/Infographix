"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_slide_scene() -> dict:
    """Create a sample SlideScene for testing."""
    return {
        "canvas": {
            "width": 12192000,
            "height": 6858000,
            "background": {"type": "solid", "color": "#FFFFFF", "alpha": 1.0},
        },
        "shapes": [
            {
                "id": "shape_1_abc123",
                "type": "autoShape",
                "name": "Rectangle 1",
                "group_path": ["root"],
                "z_index": 1,
                "bbox": {
                    "x": 914400,
                    "y": 914400,
                    "width": 2743200,
                    "height": 914400,
                },
                "transform": {
                    "rotation": 0.0,
                    "flip_h": False,
                    "flip_v": False,
                    "scale_x": 1.0,
                    "scale_y": 1.0,
                },
                "auto_shape_type": "roundRect",
                "fill": {"type": "solid", "color": "#0D9488", "alpha": 1.0},
                "stroke": {
                    "color": "#000000",
                    "width": 12700,
                    "alpha": 1.0,
                    "dash_style": "solid",
                    "cap": "flat",
                    "join": "miter",
                },
                "effects": {},
            }
        ],
        "theme": {
            "dark1": "#000000",
            "light1": "#FFFFFF",
            "dark2": "#1F497D",
            "light2": "#EEECE1",
            "accent1": "#0D9488",
            "accent2": "#14B8A6",
            "accent3": "#2DD4BF",
            "accent4": "#5EEAD4",
            "accent5": "#99F6E4",
            "accent6": "#CCFBF1",
            "hyperlink": "#0563C1",
            "followed_hyperlink": "#954F72",
        },
        "metadata": {
            "slide_number": 1,
            "tags": [],
        },
    }
