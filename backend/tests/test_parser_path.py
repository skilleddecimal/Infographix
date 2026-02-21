"""Tests for path parsing from PPTX freeform shapes.

Tests the PathParser class which extracts Bezier path commands
from <a:custGeom><a:pathLst> XML structures.
"""

import pytest
from unittest.mock import MagicMock, PropertyMock
from xml.etree.ElementTree import Element, SubElement

from backend.dsl.schema import PathCommand, PathCommandType
from backend.parser.path_parser import PathParser, NAMESPACES


class TestPathParser:
    """Tests for PathParser class."""

    @pytest.fixture
    def parser(self) -> PathParser:
        """Create a PathParser instance."""
        return PathParser()

    @pytest.fixture
    def mock_shape_with_path(self) -> MagicMock:
        """Create a mock shape with custom geometry path."""
        # Build the XML structure
        # <p:sp>
        #   <p:spPr>
        #     <a:custGeom>
        #       <a:pathLst>
        #         <a:path w="1000000" h="500000">
        #           <a:moveTo><a:pt x="0" y="0"/></a:moveTo>
        #           <a:lnTo><a:pt x="1000000" y="0"/></a:lnTo>
        #           <a:cubicBezTo>
        #             <a:pt x="1100000" y="100000"/>
        #             <a:pt x="1100000" y="400000"/>
        #             <a:pt x="1000000" y="500000"/>
        #           </a:cubicBezTo>
        #           <a:close/>
        #         </a:path>
        #       </a:pathLst>
        #     </a:custGeom>
        #   </p:spPr>
        # </p:sp>

        ns_a = NAMESPACES["a"]

        # Create root element
        root = Element("sp")

        # Create custGeom structure
        cust_geom = SubElement(root, f"{{{ns_a}}}custGeom")
        path_lst = SubElement(cust_geom, f"{{{ns_a}}}pathLst")
        path = SubElement(path_lst, f"{{{ns_a}}}path")
        path.set("w", "1000000")
        path.set("h", "500000")

        # moveTo
        move_to = SubElement(path, f"{{{ns_a}}}moveTo")
        pt = SubElement(move_to, f"{{{ns_a}}}pt")
        pt.set("x", "0")
        pt.set("y", "0")

        # lnTo
        ln_to = SubElement(path, f"{{{ns_a}}}lnTo")
        pt = SubElement(ln_to, f"{{{ns_a}}}pt")
        pt.set("x", "1000000")
        pt.set("y", "0")

        # cubicBezTo
        cubic = SubElement(path, f"{{{ns_a}}}cubicBezTo")
        pt1 = SubElement(cubic, f"{{{ns_a}}}pt")
        pt1.set("x", "1100000")
        pt1.set("y", "100000")
        pt2 = SubElement(cubic, f"{{{ns_a}}}pt")
        pt2.set("x", "1100000")
        pt2.set("y", "400000")
        pt3 = SubElement(cubic, f"{{{ns_a}}}pt")
        pt3.set("x", "1000000")
        pt3.set("y", "500000")

        # close
        SubElement(path, f"{{{ns_a}}}close")

        shape = MagicMock()
        shape._element = root
        return shape

    @pytest.fixture
    def mock_shape_with_arc(self) -> MagicMock:
        """Create a mock shape with arc path command."""
        ns_a = NAMESPACES["a"]

        root = Element("sp")
        cust_geom = SubElement(root, f"{{{ns_a}}}custGeom")
        path_lst = SubElement(cust_geom, f"{{{ns_a}}}pathLst")
        path = SubElement(path_lst, f"{{{ns_a}}}path")
        path.set("w", "100000")
        path.set("h", "100000")

        # moveTo
        move_to = SubElement(path, f"{{{ns_a}}}moveTo")
        pt = SubElement(move_to, f"{{{ns_a}}}pt")
        pt.set("x", "50000")
        pt.set("y", "0")

        # arcTo
        arc = SubElement(path, f"{{{ns_a}}}arcTo")
        arc.set("wR", "50000")
        arc.set("hR", "50000")
        arc.set("stAng", "0")
        arc.set("swAng", "5400000")  # 90 degrees in 60000ths

        shape = MagicMock()
        shape._element = root
        return shape

    @pytest.fixture
    def mock_shape_with_quad_bezier(self) -> MagicMock:
        """Create a mock shape with quadratic Bezier."""
        ns_a = NAMESPACES["a"]

        root = Element("sp")
        cust_geom = SubElement(root, f"{{{ns_a}}}custGeom")
        path_lst = SubElement(cust_geom, f"{{{ns_a}}}pathLst")
        path = SubElement(path_lst, f"{{{ns_a}}}path")
        path.set("w", "100000")
        path.set("h", "100000")

        # moveTo
        move_to = SubElement(path, f"{{{ns_a}}}moveTo")
        pt = SubElement(move_to, f"{{{ns_a}}}pt")
        pt.set("x", "0")
        pt.set("y", "0")

        # quadBezTo
        quad = SubElement(path, f"{{{ns_a}}}quadBezTo")
        pt1 = SubElement(quad, f"{{{ns_a}}}pt")
        pt1.set("x", "50000")
        pt1.set("y", "100000")
        pt2 = SubElement(quad, f"{{{ns_a}}}pt")
        pt2.set("x", "100000")
        pt2.set("y", "0")

        shape = MagicMock()
        shape._element = root
        return shape

    def test_extract_move_to(self, parser: PathParser, mock_shape_with_path: MagicMock) -> None:
        """Test extraction of moveTo command."""
        # Shape dimensions match path dimensions for 1:1 scaling
        commands = parser.extract_path_commands(mock_shape_with_path, 1000000, 500000)

        assert len(commands) >= 1
        assert commands[0].type == PathCommandType.MOVE_TO
        assert commands[0].x == 0
        assert commands[0].y == 0

    def test_extract_line_to(self, parser: PathParser, mock_shape_with_path: MagicMock) -> None:
        """Test extraction of lineTo command."""
        commands = parser.extract_path_commands(mock_shape_with_path, 1000000, 500000)

        assert len(commands) >= 2
        assert commands[1].type == PathCommandType.LINE_TO
        assert commands[1].x == 1000000
        assert commands[1].y == 0

    def test_extract_cubic_bezier(self, parser: PathParser, mock_shape_with_path: MagicMock) -> None:
        """Test extraction of cubic Bezier curve."""
        commands = parser.extract_path_commands(mock_shape_with_path, 1000000, 500000)

        assert len(commands) >= 3
        cubic = commands[2]
        assert cubic.type == PathCommandType.CURVE_TO
        # Control point 1
        assert cubic.x1 == 1100000
        assert cubic.y1 == 100000
        # Control point 2
        assert cubic.x2 == 1100000
        assert cubic.y2 == 400000
        # End point
        assert cubic.x == 1000000
        assert cubic.y == 500000

    def test_extract_close(self, parser: PathParser, mock_shape_with_path: MagicMock) -> None:
        """Test extraction of close command."""
        commands = parser.extract_path_commands(mock_shape_with_path, 1000000, 500000)

        assert len(commands) == 4
        assert commands[3].type == PathCommandType.CLOSE

    def test_extract_arc_to(self, parser: PathParser, mock_shape_with_arc: MagicMock) -> None:
        """Test extraction of arcTo command."""
        commands = parser.extract_path_commands(mock_shape_with_arc, 100000, 100000)

        assert len(commands) >= 2
        arc = commands[1]
        assert arc.type == PathCommandType.ARC_TO
        assert arc.width_radius == 50000
        assert arc.height_radius == 50000
        assert arc.start_angle == 0.0
        assert arc.swing_angle == 90.0  # 5400000 / 60000 = 90

    def test_extract_quad_bezier(
        self, parser: PathParser, mock_shape_with_quad_bezier: MagicMock
    ) -> None:
        """Test extraction of quadratic Bezier curve."""
        commands = parser.extract_path_commands(mock_shape_with_quad_bezier, 100000, 100000)

        assert len(commands) >= 2
        quad = commands[1]
        assert quad.type == PathCommandType.QUAD_TO
        # Control point
        assert quad.x1 == 50000
        assert quad.y1 == 100000
        # End point
        assert quad.x == 100000
        assert quad.y == 0

    def test_coordinate_scaling(self, parser: PathParser, mock_shape_with_path: MagicMock) -> None:
        """Test that coordinates are scaled correctly."""
        # Path is 1000000 x 500000, shape is 2000000 x 1000000 (2x scale)
        commands = parser.extract_path_commands(mock_shape_with_path, 2000000, 1000000)

        # lineTo point should be scaled 2x
        assert commands[1].x == 2000000
        assert commands[1].y == 0

    def test_empty_path_no_custom_geom(self, parser: PathParser) -> None:
        """Test handling of shape without custom geometry."""
        shape = MagicMock()
        shape._element = Element("sp")  # Empty element

        commands = parser.extract_path_commands(shape, 100000, 100000)
        assert commands == []

    def test_shape_without_element_access(self, parser: PathParser) -> None:
        """Test handling of shape that doesn't support XML access."""
        shape = MagicMock()
        type(shape)._element = PropertyMock(side_effect=AttributeError)

        commands = parser.extract_path_commands(shape, 100000, 100000)
        assert commands == []

    def test_command_order_preserved(
        self, parser: PathParser, mock_shape_with_path: MagicMock
    ) -> None:
        """Test that command order matches XML order."""
        commands = parser.extract_path_commands(mock_shape_with_path, 1000000, 500000)

        command_types = [cmd.type for cmd in commands]
        assert command_types == [
            PathCommandType.MOVE_TO,
            PathCommandType.LINE_TO,
            PathCommandType.CURVE_TO,
            PathCommandType.CLOSE,
        ]


class TestPathCommandIntegration:
    """Integration tests for PathCommand creation."""

    def test_path_command_move_to_immutable(self) -> None:
        """Test that PathCommand objects are immutable (frozen)."""
        cmd = PathCommand(type=PathCommandType.MOVE_TO, x=100, y=200)

        with pytest.raises(Exception):  # Pydantic frozen model
            cmd.x = 300

    def test_path_command_curve_with_control_points(self) -> None:
        """Test creation of curve command with all control points."""
        cmd = PathCommand(
            type=PathCommandType.CURVE_TO,
            x=500,
            y=500,
            x1=100,
            y1=200,
            x2=300,
            y2=400,
        )

        assert cmd.x == 500
        assert cmd.y == 500
        assert cmd.x1 == 100
        assert cmd.y1 == 200
        assert cmd.x2 == 300
        assert cmd.y2 == 400

    def test_path_command_arc_with_angles(self) -> None:
        """Test creation of arc command with radii and angles."""
        cmd = PathCommand(
            type=PathCommandType.ARC_TO,
            width_radius=100000,
            height_radius=50000,
            start_angle=45.0,
            swing_angle=90.0,
        )

        assert cmd.width_radius == 100000
        assert cmd.height_radius == 50000
        assert cmd.start_angle == 45.0
        assert cmd.swing_angle == 90.0
