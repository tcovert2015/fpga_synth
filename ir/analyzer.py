"""
Netlist analysis tools.

Provides various analysis capabilities:
- Resource usage estimation (LUT count, FF count, etc.)
- Critical path analysis
- Fanout analysis
- DOT graph export for visualization
"""

from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict
from fpga_synth.ir.netlist import Netlist, Cell, Net
from fpga_synth.ir.types import CellOp


class NetlistAnalyzer:
    """
    Analyzes netlist for various metrics and properties.
    """

    def __init__(self, netlist: Netlist):
        self.netlist = netlist

    def resource_usage(self) -> Dict[str, int]:
        """
        Estimate resource usage for the design.

        Returns:
            Dictionary with resource counts:
            - luts: Estimated LUT count (combinational cells)
            - ffs: Flip-flop count (sequential cells)
            - muxes: Multiplexer count
            - adders: Adder/subtractor count
            - memories: Memory block count
            - total_cells: Total cell count
        """
        stats = {
            "luts": 0,
            "ffs": 0,
            "muxes": 0,
            "adders": 0,
            "memories": 0,
            "total_cells": 0,
        }

        for cell in self.netlist.cells.values():
            if cell.op in (CellOp.MODULE_INPUT, CellOp.MODULE_OUTPUT):
                continue

            stats["total_cells"] += 1

            # Count flip-flops
            if cell.op in (CellOp.DFF, CellOp.DFFR, CellOp.DFFRE, CellOp.DFFS):
                stats["ffs"] += 1

            # Count memory blocks
            elif cell.op in (CellOp.MEMRD, CellOp.MEMWR):
                stats["memories"] += 1

            # Count multiplexers
            elif cell.op in (CellOp.MUX, CellOp.PMUX):
                stats["muxes"] += 1

            # Count adders/subtractors
            elif cell.op in (CellOp.ADD, CellOp.SUB):
                stats["adders"] += 1

            # Count LUTs (combinational logic)
            elif cell.op in (CellOp.AND, CellOp.OR, CellOp.XOR, CellOp.NOT,
                           CellOp.NAND, CellOp.NOR, CellOp.XNOR,
                           CellOp.EQ, CellOp.NEQ, CellOp.LT, CellOp.LE, CellOp.GT, CellOp.GE,
                           CellOp.REDUCE_AND, CellOp.REDUCE_OR, CellOp.REDUCE_XOR):
                stats["luts"] += 1

        return stats

    def cell_type_distribution(self) -> Dict[str, int]:
        """
        Get distribution of cell types in the design.

        Returns:
            Dictionary mapping cell type names to counts
        """
        distribution = Counter()

        for cell in self.netlist.cells.values():
            distribution[cell.op.name] += 1

        return dict(distribution)

    def fanout_analysis(self) -> Dict[str, int]:
        """
        Analyze fanout for all nets.

        Returns:
            Dictionary with fanout statistics:
            - max_fanout: Maximum fanout in design
            - avg_fanout: Average fanout
            - high_fanout_nets: Count of nets with fanout > 10
        """
        fanouts = []

        for net in self.netlist.nets.values():
            fanout = len(net.sinks)
            fanouts.append(fanout)

        if not fanouts:
            return {"max_fanout": 0, "avg_fanout": 0, "high_fanout_nets": 0}

        return {
            "max_fanout": max(fanouts),
            "avg_fanout": sum(fanouts) / len(fanouts),
            "high_fanout_nets": sum(1 for f in fanouts if f > 10)
        }

    def critical_path_depth(self) -> Dict[Cell, int]:
        """
        Calculate logic depth for each cell (longest path from inputs).

        Returns:
            Dictionary mapping cells to their logic depth
        """
        depth = {}

        # Initialize: primary inputs have depth 0
        for cell in self.netlist.inputs.values():
            depth[cell] = 0

        # Topological traversal
        def visit(cell, memo=None):
            if memo is None:
                memo = {}

            if cell in memo:
                return memo[cell]

            if cell in self.netlist.inputs.values():
                memo[cell] = 0
                return 0

            # Get max depth of predecessors
            max_input_depth = 0
            for pin in cell.inputs.values():
                if pin.net and pin.net.driver:
                    driver_cell = pin.net.driver.cell
                    if driver_cell:
                        d = visit(driver_cell, memo)
                        max_input_depth = max(max_input_depth, d)

            # Sequential elements don't add to combinational depth
            if cell.op in (CellOp.DFF, CellOp.DFFR, CellOp.DFFRE, CellOp.DFFS):
                memo[cell] = 0
            else:
                memo[cell] = max_input_depth + 1

            return memo[cell]

        # Visit all cells
        for cell in self.netlist.cells.values():
            visit(cell, depth)

        return depth

    def critical_path_summary(self) -> Dict[str, any]:
        """
        Get summary of critical path information.

        Returns:
            Dictionary with:
            - max_depth: Maximum combinational logic depth
            - critical_cells: List of cells on critical path
            - avg_depth: Average logic depth
        """
        depths = self.critical_path_depth()

        if not depths:
            return {"max_depth": 0, "critical_cells": [], "avg_depth": 0}

        max_depth = max(depths.values())
        critical_cells = [cell for cell, d in depths.items() if d == max_depth]
        avg_depth = sum(depths.values()) / len(depths)

        return {
            "max_depth": max_depth,
            "critical_cells": critical_cells,
            "avg_depth": avg_depth
        }

    def hierarchical_summary(self) -> Dict[str, List[str]]:
        """
        Summarize hierarchical instances in the design.

        Returns:
            Dictionary mapping hierarchy levels to cell names
        """
        hierarchy = defaultdict(list)

        for cell in self.netlist.cells.values():
            # Count dots in name to determine hierarchy level
            level = cell.name.count('.')
            hierarchy[f"level_{level}"].append(cell.name)

        return dict(hierarchy)

    def to_dot(self, output_file: str, include_constants: bool = False,
               include_io: bool = True, max_cells: int = 100):
        """
        Export netlist as DOT graph for visualization.

        Args:
            output_file: Path to output .dot file
            include_constants: Whether to include CONST cells
            include_io: Whether to include MODULE_INPUT/OUTPUT cells
            max_cells: Maximum number of cells to include (prevents huge graphs)

        The generated .dot file can be rendered with Graphviz:
            dot -Tpng output.dot -o output.png
        """
        cells_to_include = []

        for cell in self.netlist.cells.values():
            if not include_constants and cell.op == CellOp.CONST:
                continue
            if not include_io and cell.op in (CellOp.MODULE_INPUT, CellOp.MODULE_OUTPUT):
                continue
            cells_to_include.append(cell)

        # Limit cell count
        if len(cells_to_include) > max_cells:
            cells_to_include = cells_to_include[:max_cells]

        with open(output_file, 'w') as f:
            f.write("digraph netlist {\n")
            f.write("  rankdir=LR;\n")
            f.write("  node [shape=box];\n\n")

            # Define cell nodes with colors
            for cell in cells_to_include:
                color = self._get_cell_color(cell.op)
                label = f"{cell.name}\\n{cell.op.name}"
                f.write(f'  "{cell.name}" [label="{label}", fillcolor="{color}", style=filled];\n')

            f.write("\n")

            # Draw edges (net connections)
            for cell in cells_to_include:
                for pin in cell.inputs.values():
                    if pin.net and pin.net.driver:
                        driver = pin.net.driver.cell
                        if driver in cells_to_include:
                            f.write(f'  "{driver.name}" -> "{cell.name}";\n')

            f.write("}\n")

    def _get_cell_color(self, op: CellOp) -> str:
        """Get color for cell type in DOT graph."""
        if op in (CellOp.MODULE_INPUT, CellOp.MODULE_OUTPUT):
            return "lightblue"
        elif op in (CellOp.DFF, CellOp.DFFR, CellOp.DFFRE, CellOp.DFFS):
            return "lightgreen"
        elif op in (CellOp.MEMRD, CellOp.MEMWR):
            return "lightyellow"
        elif op == CellOp.CONST:
            return "lightgray"
        elif op in (CellOp.MUX, CellOp.PMUX):
            return "lightcoral"
        else:
            return "white"


def analyze_netlist(netlist: Netlist) -> Dict[str, any]:
    """
    Convenience function to get comprehensive netlist analysis.

    Args:
        netlist: The netlist to analyze

    Returns:
        Dictionary with all analysis results
    """
    analyzer = NetlistAnalyzer(netlist)

    return {
        "resource_usage": analyzer.resource_usage(),
        "cell_distribution": analyzer.cell_type_distribution(),
        "fanout": analyzer.fanout_analysis(),
        "critical_path": analyzer.critical_path_summary(),
    }
