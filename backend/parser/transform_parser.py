"""Extract transformation properties from PowerPoint shapes.

Parses <a:xfrm> XML to extract rotation, flip_h, flip_v attributes.
Rotation is stored in 60,000ths of a degree in PPTX and converted to degrees.
"""

from typing import Any

from backend.dsl.schema import Transform


# XML namespaces for Office Open XML
NAMESPACES = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


class TransformParser:
    """Extracts transformation properties from PPTX shape XML."""

    def extract_transform(self, shape: Any) -> Transform:
        """Extract transform properties from a shape.

        Reads the <a:xfrm> element to get rotation, flipH, and flipV attributes.

        Args:
            shape: The python-pptx shape object.

        Returns:
            Transform object with rotation and flip properties.

        XML structure example:
            <a:xfrm rot="5400000" flipH="1" flipV="0">
                <a:off x="914400" y="914400"/>
                <a:ext cx="2743200" cy="914400"/>
            </a:xfrm>
        """
        rotation = 0.0
        flip_h = False
        flip_v = False
        scale_x = 1.0
        scale_y = 1.0

        # Try to get rotation from python-pptx API first
        if hasattr(shape, "rotation"):
            try:
                rotation = float(shape.rotation) if shape.rotation else 0.0
            except (TypeError, ValueError):
                pass

        # Access XML for flip properties (not exposed by python-pptx API)
        try:
            element = shape._element

            # Find the <a:xfrm> element
            # It can be in different locations depending on shape type
            xfrm = self._find_xfrm_element(element)

            if xfrm is not None:
                # Extract rotation if not already got from API
                rot_attr = xfrm.get("rot")
                if rot_attr is not None:
                    # Rotation is in 60,000ths of a degree
                    rotation = float(rot_attr) / 60000.0

                # Extract flip attributes
                flip_h_attr = xfrm.get("flipH")
                flip_v_attr = xfrm.get("flipV")

                # "1" or "true" means flipped
                flip_h = flip_h_attr in ("1", "true")
                flip_v = flip_v_attr in ("1", "true")

        except (AttributeError, TypeError):
            # Shape doesn't support XML access
            pass

        return Transform(
            rotation=rotation,
            flip_h=flip_h,
            flip_v=flip_v,
            scale_x=scale_x,
            scale_y=scale_y,
        )

    def _find_xfrm_element(self, element: Any) -> Any | None:
        """Find the <a:xfrm> element in a shape's XML.

        The xfrm element can be in different locations depending on the shape type:
        - <p:sp><p:spPr><a:xfrm> for normal shapes
        - <p:pic><p:spPr><a:xfrm> for pictures
        - <p:grpSp><p:grpSpPr><a:xfrm> for groups

        Args:
            element: The shape's XML element.

        Returns:
            The xfrm element or None if not found.
        """
        # Try different locations for xfrm
        search_paths = [
            ".//a:xfrm",  # General search
            "p:spPr/a:xfrm",  # Standard shape
            "p:nvSpPr/p:spPr/a:xfrm",  # Another structure
            "p:grpSpPr/a:xfrm",  # Group shape
        ]

        for path in search_paths:
            xfrm = element.find(path, NAMESPACES)
            if xfrm is not None:
                return xfrm

        return None

    def extract_group_transform(self, group_shape: Any) -> tuple[Transform, dict]:
        """Extract transform from a group shape, including child offsets.

        Group shapes have both their own transform and a coordinate system
        that affects how child shapes are positioned.

        Args:
            group_shape: The python-pptx group shape object.

        Returns:
            Tuple of (Transform, offset_dict) where offset_dict contains
            'child_offset_x' and 'child_offset_y' for adjusting children.
        """
        transform = self.extract_transform(group_shape)
        offsets = {"child_offset_x": 0, "child_offset_y": 0}

        try:
            element = group_shape._element

            # Groups have <a:chOff> and <a:chExt> for child coordinate space
            grp_sp_pr = element.find("p:grpSpPr", NAMESPACES)
            if grp_sp_pr is not None:
                xfrm = grp_sp_pr.find("a:xfrm", NAMESPACES)
                if xfrm is not None:
                    ch_off = xfrm.find("a:chOff", NAMESPACES)
                    if ch_off is not None:
                        offsets["child_offset_x"] = int(ch_off.get("x", "0"))
                        offsets["child_offset_y"] = int(ch_off.get("y", "0"))

        except (AttributeError, TypeError):
            pass

        return transform, offsets


def normalize_rotation(degrees: float) -> float:
    """Normalize rotation to 0-360 range.

    Args:
        degrees: Rotation in degrees (may be negative or >360).

    Returns:
        Normalized rotation in 0-360 range.
    """
    normalized = degrees % 360.0
    if normalized < 0:
        normalized += 360.0
    return normalized
