"""
layout_strategies — Pluggable layout computation strategies.

This package contains the six core layout strategies that cover all diagram patterns:

- GridStrategy: Rows/columns (Comparison, Matrix, Card Grid)
- StackStrategy: Vertical/horizontal stacking (Funnel, Pyramid, Timeline)
- RadialStrategy: Circular arrangement (Hub-Spoke, Cycle, Target)
- TreeStrategy: Hierarchical (Org Chart, Tree Diagram)
- FlowStrategy: Sequential with connectors (Process Flow, Pipeline, Chevron)
- FreeformStrategy: Arbitrary positioning (Canvas, Custom)

Each strategy implements the BaseLayoutStrategy interface and can be selected
dynamically based on the ArchetypeRules.
"""

from .base_strategy import BaseLayoutStrategy, StrategyResult, ElementPosition, ContentBounds, ConnectorPosition
from .grid_strategy import GridStrategy
from .stack_strategy import StackStrategy
from .radial_strategy import RadialStrategy
from .tree_strategy import TreeStrategy
from .flow_strategy import FlowStrategy
from .freeform_strategy import FreeformStrategy

__all__ = [
    'BaseLayoutStrategy',
    'StrategyResult',
    'ElementPosition',
    'ContentBounds',
    'ConnectorPosition',
    'GridStrategy',
    'StackStrategy',
    'RadialStrategy',
    'TreeStrategy',
    'FlowStrategy',
    'FreeformStrategy',
    'get_strategy',
    'STRATEGIES',
]


# Strategy registry for lookup by name
STRATEGIES = {
    'grid': GridStrategy,
    'stack': StackStrategy,
    'radial': RadialStrategy,
    'tree': TreeStrategy,
    'flow': FlowStrategy,
    'freeform': FreeformStrategy,
}


def get_strategy(strategy_name: str) -> BaseLayoutStrategy:
    """Get a strategy instance by name."""
    strategy_class = STRATEGIES.get(strategy_name.lower())
    if not strategy_class:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(STRATEGIES.keys())}")
    return strategy_class()
