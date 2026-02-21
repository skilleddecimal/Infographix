"""Extract Bezier path commands from PowerPoint freeform shapes.

Parses <a:custGeom><a:pathLst> XML to extract moveTo, lineTo, cubicBezTo,
quadBezTo, arcTo, and close commands. Coordinates are scaled from path
space to shape EMUs.
"""

from typing import Any
from xml.etree.ElementTree import Element

from backend.dsl.schema import PathCommand, PathCommandType


# XML namespaces for Office Open XML
NAMESPACES = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


class PathParser:
    """Extracts path commands from PPTX freeform shape XML."""

    def extract_path_commands(
        self,
        shape: Any,
        shape_width: int,
        shape_height: int,
    ) -> list[PathCommand]:
        """Extract path commands from a freeform shape.

        Args:
            shape: The python-pptx shape object with _element access.
            shape_width: Shape width in EMUs for coordinate scaling.
            shape_height: Shape height in EMUs for coordinate scaling.

        Returns:
            List of PathCommand objects defining the shape's path.
        """
        commands: list[PathCommand] = []

        try:
            # Access the underlying XML element
            element = shape._element

            # Find the custom geometry element
            cust_geom = element.find(".//a:custGeom", NAMESPACES)
            if cust_geom is None:
                return commands

            # Find the path list
            path_lst = cust_geom.find("a:pathLst", NAMESPACES)
            if path_lst is None:
                return commands

            # Process each path in the list
            for path_elem in path_lst.findall("a:path", NAMESPACES):
                path_commands = self._parse_path_element(
                    path_elem, shape_width, shape_height
                )
                commands.extend(path_commands)

        except (AttributeError, TypeError):
            # Shape doesn't support XML access or has no custom geometry
            pass

        return commands

    def _parse_path_element(
        self,
        path_elem: Element,
        shape_width: int,
        shape_height: int,
    ) -> list[PathCommand]:
        """Parse a single <a:path> element.

        Args:
            path_elem: The <a:path> XML element.
            shape_width: Shape width in EMUs.
            shape_height: Shape height in EMUs.

        Returns:
            List of PathCommand objects.
        """
        commands: list[PathCommand] = []

        # Get path coordinate space dimensions
        path_width = int(path_elem.get("w", "1"))
        path_height = int(path_elem.get("h", "1"))

        # Calculate scale factors
        scale_x = shape_width / path_width if path_width > 0 else 1.0
        scale_y = shape_height / path_height if path_height > 0 else 1.0

        # Process each child element in order
        for child in path_elem:
            tag = self._get_local_tag(child)
            cmd = self._parse_command(child, tag, scale_x, scale_y)
            if cmd:
                commands.append(cmd)

        return commands

    def _get_local_tag(self, elem: Element) -> str:
        """Get the local tag name without namespace.

        Args:
            elem: XML element.

        Returns:
            Local tag name (e.g., 'moveTo' from '{namespace}moveTo').
        """
        tag = elem.tag
        if "}" in tag:
            return tag.split("}")[1]
        return tag

    def _parse_command(
        self,
        elem: Element,
        tag: str,
        scale_x: float,
        scale_y: float,
    ) -> PathCommand | None:
        """Parse a single path command element.

        Args:
            elem: The path command XML element.
            tag: The local tag name.
            scale_x: X coordinate scale factor.
            scale_y: Y coordinate scale factor.

        Returns:
            PathCommand or None if unsupported.
        """
        if tag == "moveTo":
            return self._parse_move_to(elem, scale_x, scale_y)
        elif tag == "lnTo":
            return self._parse_line_to(elem, scale_x, scale_y)
        elif tag == "cubicBezTo":
            return self._parse_cubic_bezier(elem, scale_x, scale_y)
        elif tag == "quadBezTo":
            return self._parse_quad_bezier(elem, scale_x, scale_y)
        elif tag == "arcTo":
            return self._parse_arc_to(elem, scale_x, scale_y)
        elif tag == "close":
            return PathCommand(type=PathCommandType.CLOSE)

        return None

    def _parse_move_to(
        self,
        elem: Element,
        scale_x: float,
        scale_y: float,
    ) -> PathCommand | None:
        """Parse moveTo command.

        XML structure:
        <a:moveTo><a:pt x="0" y="0"/></a:moveTo>
        """
        pt = elem.find("a:pt", NAMESPACES)
        if pt is None:
            return None

        x = int(float(pt.get("x", "0")) * scale_x)
        y = int(float(pt.get("y", "0")) * scale_y)

        return PathCommand(type=PathCommandType.MOVE_TO, x=x, y=y)

    def _parse_line_to(
        self,
        elem: Element,
        scale_x: float,
        scale_y: float,
    ) -> PathCommand | None:
        """Parse lineTo command.

        XML structure:
        <a:lnTo><a:pt x="1000" y="500"/></a:lnTo>
        """
        pt = elem.find("a:pt", NAMESPACES)
        if pt is None:
            return None

        x = int(float(pt.get("x", "0")) * scale_x)
        y = int(float(pt.get("y", "0")) * scale_y)

        return PathCommand(type=PathCommandType.LINE_TO, x=x, y=y)

    def _parse_cubic_bezier(
        self,
        elem: Element,
        scale_x: float,
        scale_y: float,
    ) -> PathCommand | None:
        """Parse cubic Bezier curve command.

        XML structure:
        <a:cubicBezTo>
            <a:pt x="100" y="200"/>  <!-- Control point 1 -->
            <a:pt x="300" y="400"/>  <!-- Control point 2 -->
            <a:pt x="500" y="500"/>  <!-- End point -->
        </a:cubicBezTo>
        """
        points = elem.findall("a:pt", NAMESPACES)
        if len(points) < 3:
            return None

        # Control point 1
        x1 = int(float(points[0].get("x", "0")) * scale_x)
        y1 = int(float(points[0].get("y", "0")) * scale_y)

        # Control point 2
        x2 = int(float(points[1].get("x", "0")) * scale_x)
        y2 = int(float(points[1].get("y", "0")) * scale_y)

        # End point
        x = int(float(points[2].get("x", "0")) * scale_x)
        y = int(float(points[2].get("y", "0")) * scale_y)

        return PathCommand(
            type=PathCommandType.CURVE_TO,
            x=x,
            y=y,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
        )

    def _parse_quad_bezier(
        self,
        elem: Element,
        scale_x: float,
        scale_y: float,
    ) -> PathCommand | None:
        """Parse quadratic Bezier curve command.

        XML structure:
        <a:quadBezTo>
            <a:pt x="100" y="200"/>  <!-- Control point -->
            <a:pt x="500" y="500"/>  <!-- End point -->
        </a:quadBezTo>
        """
        points = elem.findall("a:pt", NAMESPACES)
        if len(points) < 2:
            return None

        # Control point
        x1 = int(float(points[0].get("x", "0")) * scale_x)
        y1 = int(float(points[0].get("y", "0")) * scale_y)

        # End point
        x = int(float(points[1].get("x", "0")) * scale_x)
        y = int(float(points[1].get("y", "0")) * scale_y)

        return PathCommand(
            type=PathCommandType.QUAD_TO,
            x=x,
            y=y,
            x1=x1,
            y1=y1,
        )

    def _parse_arc_to(
        self,
        elem: Element,
        scale_x: float,
        scale_y: float,
    ) -> PathCommand | None:
        """Parse arc command.

        XML structure:
        <a:arcTo wR="100000" hR="50000" stAng="0" swAng="5400000"/>

        Attributes:
            wR: Width radius in EMUs
            hR: Height radius in EMUs
            stAng: Start angle in 60,000ths of a degree
            swAng: Swing angle in 60,000ths of a degree
        """
        width_radius = int(float(elem.get("wR", "0")) * scale_x)
        height_radius = int(float(elem.get("hR", "0")) * scale_y)

        # Convert from 60,000ths of a degree to degrees
        start_angle_raw = float(elem.get("stAng", "0"))
        swing_angle_raw = float(elem.get("swAng", "0"))

        start_angle = start_angle_raw / 60000.0
        swing_angle = swing_angle_raw / 60000.0

        return PathCommand(
            type=PathCommandType.ARC_TO,
            width_radius=width_radius,
            height_radius=height_radius,
            start_angle=start_angle,
            swing_angle=swing_angle,
        )


def extract_preset_geometry_path(shape: Any) -> list[PathCommand]:
    """Extract path from preset geometry shapes.

    Some shapes use <a:prstGeom> instead of <a:custGeom>.
    This extracts the adjustment values for standard shapes.

    Args:
        shape: The python-pptx shape object.

    Returns:
        List of PathCommand objects (empty for non-custom shapes).
    """
    # Preset geometries are handled by the auto_shape_type in DSL,
    # not by explicit path commands. Return empty list.
    return []
