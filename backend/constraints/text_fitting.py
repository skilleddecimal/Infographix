"""Text fitting constraints for text-safe zones and overflow handling."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from backend.dsl.schema import BoundingBox, Shape, ShapeType, TextContent, TextRun


class OverflowAction(str, Enum):
    """Action to take when text overflows."""

    SHRINK_TEXT = "shrink_text"
    TRUNCATE = "truncate"
    EXPAND_SHAPE = "expand_shape"
    WRAP = "wrap"
    NONE = "none"


class TextFitResult(str, Enum):
    """Result of text fitting check."""

    FITS = "fits"
    OVERFLOW_WIDTH = "overflow_width"
    OVERFLOW_HEIGHT = "overflow_height"
    OVERFLOW_BOTH = "overflow_both"


@dataclass
class TextMetrics:
    """Estimated text dimensions."""

    width: int
    height: int
    line_count: int
    avg_char_width: int
    line_height: int


@dataclass
class TextSafeZone:
    """Defines a text-safe area within a shape."""

    padding_left: int = 91440  # 0.1 inch
    padding_right: int = 91440
    padding_top: int = 45720  # 0.05 inch
    padding_bottom: int = 45720
    min_font_size: int = 800  # 8pt in hundredths of a point
    max_font_size: int = 4400  # 44pt

    @property
    def horizontal_padding(self) -> int:
        """Total horizontal padding."""
        return self.padding_left + self.padding_right

    @property
    def vertical_padding(self) -> int:
        """Total vertical padding."""
        return self.padding_top + self.padding_bottom


@dataclass
class TextFittingConstraint:
    """Constraint for fitting text within shapes."""

    safe_zone: TextSafeZone
    overflow_action: OverflowAction = OverflowAction.SHRINK_TEXT
    # Approximate EMUs per character at 1400 (14pt) font size
    emu_per_char_base: int = 91440  # ~1 inch for ~10 chars

    def check_text_fit(self, shape: Shape) -> tuple[TextFitResult, TextMetrics | None]:
        """Check if text fits within shape bounds.

        Args:
            shape: Shape with text content.

        Returns:
            Tuple of (fit result, text metrics).
        """
        if not shape.text or not shape.text.runs:
            return TextFitResult.FITS, None

        metrics = self._estimate_text_metrics(shape.text, shape.bbox)
        available_width = shape.bbox.width - self.safe_zone.horizontal_padding
        available_height = shape.bbox.height - self.safe_zone.vertical_padding

        overflow_width = metrics.width > available_width
        overflow_height = metrics.height > available_height

        if overflow_width and overflow_height:
            return TextFitResult.OVERFLOW_BOTH, metrics
        elif overflow_width:
            return TextFitResult.OVERFLOW_WIDTH, metrics
        elif overflow_height:
            return TextFitResult.OVERFLOW_HEIGHT, metrics

        return TextFitResult.FITS, metrics

    def fix_text_overflow(self, shape: Shape) -> Shape:
        """Fix text overflow in a shape.

        Args:
            shape: Shape with potential text overflow.

        Returns:
            Fixed shape.
        """
        fit_result, metrics = self.check_text_fit(shape)

        if fit_result == TextFitResult.FITS or metrics is None:
            return shape

        if self.overflow_action == OverflowAction.SHRINK_TEXT:
            return self._shrink_text(shape, metrics)
        elif self.overflow_action == OverflowAction.TRUNCATE:
            return self._truncate_text(shape, metrics)
        elif self.overflow_action == OverflowAction.EXPAND_SHAPE:
            return self._expand_shape(shape, metrics)
        elif self.overflow_action == OverflowAction.WRAP:
            return self._wrap_text(shape, metrics)

        return shape

    def _estimate_text_metrics(
        self, text_content: TextContent, bbox: BoundingBox
    ) -> TextMetrics:
        """Estimate text dimensions based on content and font size.

        Args:
            text_content: Text content with runs.
            bbox: Shape bounding box.

        Returns:
            Estimated text metrics.
        """
        if not text_content.runs:
            return TextMetrics(
                width=0, height=0, line_count=0, avg_char_width=0, line_height=0
            )

        # Get average font size across runs
        total_chars = 0
        weighted_font_size = 0

        for run in text_content.runs:
            char_count = len(run.text)
            total_chars += char_count
            weighted_font_size += run.font_size * char_count

        avg_font_size = weighted_font_size // total_chars if total_chars > 0 else 1400

        # Calculate character width based on font size
        # Rough approximation: char width = font_size * 0.6 * EMU_per_point
        # Where EMU_per_point = 12700
        emu_per_point = 12700
        avg_char_width = int(avg_font_size * 0.006 * emu_per_point)
        line_height = int(avg_font_size * 0.012 * emu_per_point * 1.2)  # 1.2 line spacing

        # Calculate total text
        total_text = "".join(run.text for run in text_content.runs)
        lines = total_text.split("\n")

        # Calculate dimensions
        max_line_width = max(
            len(line) * avg_char_width for line in lines
        ) if lines else 0
        total_height = len(lines) * line_height

        return TextMetrics(
            width=max_line_width,
            height=total_height,
            line_count=len(lines),
            avg_char_width=avg_char_width,
            line_height=line_height,
        )

    def _shrink_text(self, shape: Shape, metrics: TextMetrics) -> Shape:
        """Shrink text to fit within shape.

        Args:
            shape: Shape with text.
            metrics: Current text metrics.

        Returns:
            Shape with shrunk text.
        """
        if not shape.text or not shape.text.runs:
            return shape

        available_width = shape.bbox.width - self.safe_zone.horizontal_padding
        available_height = shape.bbox.height - self.safe_zone.vertical_padding

        # Calculate scale factor
        width_scale = available_width / metrics.width if metrics.width > 0 else 1.0
        height_scale = available_height / metrics.height if metrics.height > 0 else 1.0
        scale = min(width_scale, height_scale, 1.0)

        if scale >= 1.0:
            return shape

        # Shrink all text runs
        new_runs = []
        for run in shape.text.runs:
            new_font_size = max(
                self.safe_zone.min_font_size,
                int(run.font_size * scale)
            )
            new_run = TextRun(
                text=run.text,
                font_family=run.font_family,
                font_size=new_font_size,
                bold=run.bold,
                italic=run.italic,
                underline=run.underline,
                color=run.color,
            )
            new_runs.append(new_run)

        new_text = TextContent(
            runs=new_runs,
            alignment=shape.text.alignment,
        )

        shape_dict = shape.model_dump()
        shape_dict["text"] = new_text
        return Shape(**shape_dict)

    def _truncate_text(self, shape: Shape, metrics: TextMetrics) -> Shape:
        """Truncate text to fit within shape.

        Args:
            shape: Shape with text.
            metrics: Current text metrics.

        Returns:
            Shape with truncated text.
        """
        if not shape.text or not shape.text.runs:
            return shape

        available_width = shape.bbox.width - self.safe_zone.horizontal_padding

        # Calculate max characters per line
        max_chars = max(1, available_width // metrics.avg_char_width) if metrics.avg_char_width > 0 else 100

        # Truncate runs
        new_runs = []
        total_chars = 0

        for run in shape.text.runs:
            remaining = max_chars - total_chars
            if remaining <= 0:
                break

            if len(run.text) <= remaining:
                new_runs.append(run)
                total_chars += len(run.text)
            else:
                # Truncate this run
                truncated_text = run.text[:remaining - 3] + "..." if remaining > 3 else "..."
                new_run = TextRun(
                    text=truncated_text,
                    font_family=run.font_family,
                    font_size=run.font_size,
                    bold=run.bold,
                    italic=run.italic,
                    underline=run.underline,
                    color=run.color,
                )
                new_runs.append(new_run)
                break

        new_text = TextContent(
            runs=new_runs,
            alignment=shape.text.alignment,
        )

        shape_dict = shape.model_dump()
        shape_dict["text"] = new_text
        return Shape(**shape_dict)

    def _expand_shape(self, shape: Shape, metrics: TextMetrics) -> Shape:
        """Expand shape to fit text.

        Args:
            shape: Shape with text.
            metrics: Current text metrics.

        Returns:
            Shape with expanded bounding box.
        """
        needed_width = metrics.width + self.safe_zone.horizontal_padding
        needed_height = metrics.height + self.safe_zone.vertical_padding

        new_width = max(shape.bbox.width, needed_width)
        new_height = max(shape.bbox.height, needed_height)

        # Keep shape centered
        width_diff = new_width - shape.bbox.width
        height_diff = new_height - shape.bbox.height

        new_bbox = BoundingBox(
            x=shape.bbox.x - width_diff // 2,
            y=shape.bbox.y - height_diff // 2,
            width=new_width,
            height=new_height,
        )

        shape_dict = shape.model_dump()
        shape_dict["bbox"] = new_bbox
        return Shape(**shape_dict)

    def _wrap_text(self, shape: Shape, metrics: TextMetrics) -> Shape:
        """Wrap text to fit within shape width.

        Note: This modifies the text content by adding line breaks.

        Args:
            shape: Shape with text.
            metrics: Current text metrics.

        Returns:
            Shape with wrapped text.
        """
        if not shape.text or not shape.text.runs:
            return shape

        available_width = shape.bbox.width - self.safe_zone.horizontal_padding
        chars_per_line = max(1, available_width // metrics.avg_char_width) if metrics.avg_char_width > 0 else 50

        # Simple word wrapping
        new_runs = []
        for run in shape.text.runs:
            words = run.text.split(" ")
            lines = []
            current_line = ""

            for word in words:
                if len(current_line) + len(word) + 1 <= chars_per_line:
                    current_line += (" " if current_line else "") + word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

            wrapped_text = "\n".join(lines)
            new_run = TextRun(
                text=wrapped_text,
                font_family=run.font_family,
                font_size=run.font_size,
                bold=run.bold,
                italic=run.italic,
                underline=run.underline,
                color=run.color,
            )
            new_runs.append(new_run)

        new_text = TextContent(
            runs=new_runs,
            alignment=shape.text.alignment,
        )

        shape_dict = shape.model_dump()
        shape_dict["text"] = new_text
        return Shape(**shape_dict)


def check_text_overflow(shapes: list[Shape]) -> list[tuple[Shape, TextFitResult]]:
    """Check all shapes for text overflow.

    Args:
        shapes: Shapes to check.

    Returns:
        List of (shape, result) tuples for shapes with text.
    """
    constraint = TextFittingConstraint(safe_zone=TextSafeZone())
    results = []

    for shape in shapes:
        if shape.text and shape.text.runs:
            result, _ = constraint.check_text_fit(shape)
            results.append((shape, result))

    return results


def fix_text_overflow(
    shapes: list[Shape],
    overflow_action: OverflowAction = OverflowAction.SHRINK_TEXT,
) -> list[Shape]:
    """Fix text overflow in all shapes.

    Args:
        shapes: Shapes to fix.
        overflow_action: Action to take for overflow.

    Returns:
        Fixed shapes.
    """
    constraint = TextFittingConstraint(
        safe_zone=TextSafeZone(),
        overflow_action=overflow_action,
    )

    fixed = []
    for shape in shapes:
        if shape.text and shape.text.runs:
            fixed.append(constraint.fix_text_overflow(shape))
        else:
            fixed.append(shape)

    return fixed


def calculate_min_shape_size(
    text_content: TextContent,
    safe_zone: TextSafeZone | None = None,
) -> tuple[int, int]:
    """Calculate minimum shape size for text content.

    Args:
        text_content: Text content to fit.
        safe_zone: Safe zone settings.

    Returns:
        Tuple of (min_width, min_height) in EMUs.
    """
    if safe_zone is None:
        safe_zone = TextSafeZone()

    # Create a temporary shape to estimate metrics
    constraint = TextFittingConstraint(safe_zone=safe_zone)

    # Use a large bbox for estimation
    temp_bbox = BoundingBox(x=0, y=0, width=12192000, height=6858000)
    metrics = constraint._estimate_text_metrics(text_content, temp_bbox)

    min_width = metrics.width + safe_zone.horizontal_padding
    min_height = metrics.height + safe_zone.vertical_padding

    return min_width, min_height


def get_text_safe_area(shape: Shape, safe_zone: TextSafeZone | None = None) -> BoundingBox:
    """Get the text-safe area within a shape.

    Args:
        shape: Shape to get safe area for.
        safe_zone: Safe zone settings.

    Returns:
        Bounding box of the text-safe area.
    """
    if safe_zone is None:
        safe_zone = TextSafeZone()

    return BoundingBox(
        x=shape.bbox.x + safe_zone.padding_left,
        y=shape.bbox.y + safe_zone.padding_top,
        width=max(0, shape.bbox.width - safe_zone.horizontal_padding),
        height=max(0, shape.bbox.height - safe_zone.vertical_padding),
    )
