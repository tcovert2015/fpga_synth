"""
Netlist optimization passes.

Provides various optimization transformations on the netlist IR:
- Constant propagation
- Dead code elimination
- Common subexpression elimination
"""

from typing import Set, Dict, Optional
from fpga_synth.ir.netlist import Netlist, Cell, Net, Pin
from fpga_synth.ir.types import CellOp, BitWidth


class NetlistOptimizer:
    """
    Applies optimization passes to a netlist.

    Optimizations are applied in-place to the netlist.
    """

    def __init__(self, netlist: Netlist):
        self.netlist = netlist

    def optimize(self, passes: list[str] = None) -> Dict[str, int]:
        """
        Run optimization passes on the netlist.

        Args:
            passes: List of passes to run. If None, runs all passes in default order.
                   Available: "constant_prop", "dead_code", "cse", "identity",
                             "algebraic", "strength_reduce"

        Returns:
            Dictionary of optimization statistics
        """
        if passes is None:
            passes = ["identity", "algebraic", "constant_prop", "strength_reduce", "dead_code", "cse"]

        stats = {}

        for pass_name in passes:
            if pass_name == "constant_prop":
                stats["constants_propagated"] = self.constant_propagation()
            elif pass_name == "dead_code":
                stats["dead_cells_removed"] = self.dead_code_elimination()
            elif pass_name == "cse":
                stats["common_subexprs_eliminated"] = self.common_subexpression_elimination()
            elif pass_name == "identity":
                stats["identities_eliminated"] = self.identity_elimination()
            elif pass_name == "algebraic":
                stats["algebraic_simplified"] = self.algebraic_simplification()
            elif pass_name == "strength_reduce":
                stats["strength_reduced"] = self.strength_reduction()

        return stats

    def constant_propagation(self) -> int:
        """
        Propagate constants through the netlist.

        Replaces cells whose inputs are all constants with constant cells.

        Returns:
            Number of cells replaced with constants
        """
        propagated = 0
        changed = True

        # Iterate until no more changes
        while changed:
            changed = False
            cells_to_replace = []

            for cell_id, cell in list(self.netlist.cells.items()):
                if cell.op == CellOp.CONST:
                    continue  # Already a constant

                if cell.op in (CellOp.MODULE_INPUT, CellOp.MODULE_OUTPUT):
                    continue  # Don't optimize I/O

                # Check if all inputs are constants
                const_inputs = self._get_constant_inputs(cell)
                if const_inputs is not None and len(const_inputs) == len(cell.inputs):
                    # All inputs are constants - evaluate and replace
                    result = self._evaluate_cell(cell, const_inputs)
                    if result is not None:
                        cells_to_replace.append((cell, result))
                        changed = True

            # Apply replacements
            for cell, const_value in cells_to_replace:
                self._replace_with_constant(cell, const_value)
                propagated += 1

        return propagated

    def _get_constant_inputs(self, cell: Cell) -> Optional[Dict[str, int]]:
        """Get constant values for all inputs, or None if any input is non-constant."""
        const_inputs = {}

        for pin_name, pin in cell.inputs.items():
            if not pin.net or not pin.net.driver:
                return None

            driver_cell = pin.net.driver.cell
            if driver_cell.op != CellOp.CONST:
                return None

            # Get constant value from driver
            const_value = driver_cell.attributes.get("value", 0)
            const_inputs[pin_name] = const_value

        return const_inputs

    def _evaluate_cell(self, cell: Cell, const_inputs: Dict[str, int]) -> Optional[int]:
        """Evaluate a cell with constant inputs."""
        op = cell.op

        # Unary operations
        if op == CellOp.NOT:
            a = const_inputs.get("A", 0)
            width = cell.output.width.width
            mask = (1 << width) - 1
            return (~a) & mask

        elif op == CellOp.BUF:
            return const_inputs.get("A", 0)

        elif op == CellOp.NEG:
            a = const_inputs.get("A", 0)
            width = cell.output.width.width
            mask = (1 << width) - 1
            return (-a) & mask

        # Binary operations
        elif op == CellOp.AND:
            return const_inputs.get("A", 0) & const_inputs.get("B", 0)

        elif op == CellOp.OR:
            return const_inputs.get("A", 0) | const_inputs.get("B", 0)

        elif op == CellOp.XOR:
            return const_inputs.get("A", 0) ^ const_inputs.get("B", 0)

        elif op == CellOp.NAND:
            a = const_inputs.get("A", 0)
            b = const_inputs.get("B", 0)
            width = cell.output.width.width
            mask = (1 << width) - 1
            return (~(a & b)) & mask

        elif op == CellOp.NOR:
            a = const_inputs.get("A", 0)
            b = const_inputs.get("B", 0)
            width = cell.output.width.width
            mask = (1 << width) - 1
            return (~(a | b)) & mask

        elif op == CellOp.XNOR:
            a = const_inputs.get("A", 0)
            b = const_inputs.get("B", 0)
            width = cell.output.width.width
            mask = (1 << width) - 1
            return (~(a ^ b)) & mask

        elif op == CellOp.ADD:
            a = const_inputs.get("A", 0)
            b = const_inputs.get("B", 0)
            width = cell.output.width.width
            mask = (1 << width) - 1
            return (a + b) & mask

        elif op == CellOp.SUB:
            a = const_inputs.get("A", 0)
            b = const_inputs.get("B", 0)
            width = cell.output.width.width
            mask = (1 << width) - 1
            return (a - b) & mask

        elif op == CellOp.EQ:
            return 1 if const_inputs.get("A", 0) == const_inputs.get("B", 0) else 0

        elif op == CellOp.NEQ:
            return 1 if const_inputs.get("A", 0) != const_inputs.get("B", 0) else 0

        elif op == CellOp.LT:
            return 1 if const_inputs.get("A", 0) < const_inputs.get("B", 0) else 0

        elif op == CellOp.LE:
            return 1 if const_inputs.get("A", 0) <= const_inputs.get("B", 0) else 0

        elif op == CellOp.GT:
            return 1 if const_inputs.get("A", 0) > const_inputs.get("B", 0) else 0

        elif op == CellOp.GE:
            return 1 if const_inputs.get("A", 0) >= const_inputs.get("B", 0) else 0

        # Shift operations
        elif op == CellOp.SHL:
            a = const_inputs.get("A", 0)
            b = const_inputs.get("B", 0)
            width = cell.output.width.width
            mask = (1 << width) - 1
            return (a << b) & mask

        elif op == CellOp.SHR:
            return const_inputs.get("A", 0) >> const_inputs.get("B", 0)

        # MUX
        elif op == CellOp.MUX:
            sel = const_inputs.get("S", 0)
            return const_inputs.get("B", 0) if sel else const_inputs.get("A", 0)

        # Can't evaluate this cell type
        return None

    def _replace_with_constant(self, cell: Cell, value: int):
        """Replace a cell with a constant."""
        # Create new constant cell
        const_cell = Cell(name=f"const_{value}", op=CellOp.CONST)
        const_cell.attributes["value"] = value

        # Get output net
        output_net = cell.output.net if hasattr(cell, 'output') and cell.output else None
        if not output_net:
            return

        # Create output pin for constant
        const_pin = const_cell.add_output("Y", output_net.width)

        # Reconnect output net to constant
        output_net.set_driver(const_pin)

        # Add constant cell to netlist
        self.netlist.add_cell(const_cell)

        # Remove old cell
        self.netlist.remove_cell(cell)

    def dead_code_elimination(self) -> int:
        """
        Remove cells that don't affect any outputs.

        Returns:
            Number of dead cells removed
        """
        # Find all live cells (reachable from outputs)
        live_cells = self._find_live_cells()

        # Remove dead cells
        dead_count = 0
        for cell_id in list(self.netlist.cells.keys()):
            if cell_id not in live_cells:
                cell = self.netlist.cells[cell_id]
                # Don't remove module I/O
                if cell.op not in (CellOp.MODULE_INPUT, CellOp.MODULE_OUTPUT):
                    self.netlist.remove_cell(cell)
                    dead_count += 1

        return dead_count

    def _find_live_cells(self) -> Set[int]:
        """Find all cells reachable from outputs (live cells)."""
        live = set()
        to_visit = []

        # Start from output cells
        for output_cell in self.netlist.outputs.values():
            to_visit.append(output_cell)

        # Backward traversal from outputs
        while to_visit:
            cell = to_visit.pop()

            if cell.id in live:
                continue

            live.add(cell.id)

            # Visit all cells driving inputs
            for pin in cell.inputs.values():
                if pin.net and pin.net.driver:
                    driver_cell = pin.net.driver.cell
                    if driver_cell and driver_cell.id not in live:
                        to_visit.append(driver_cell)

        return live

    def common_subexpression_elimination(self) -> int:
        """
        Eliminate common subexpressions.

        Finds cells with identical operations and inputs, and merges them.

        Returns:
            Number of cells eliminated
        """
        eliminated = 0

        # Build expression signatures
        signatures: Dict[str, Cell] = {}

        for cell_id, cell in list(self.netlist.cells.items()):
            if cell.op in (CellOp.MODULE_INPUT, CellOp.MODULE_OUTPUT, CellOp.CONST):
                continue  # Don't CSE these

            if cell.op in (CellOp.DFF, CellOp.DFFR, CellOp.MEMRD, CellOp.MEMWR):
                continue  # Don't CSE stateful elements

            # Create signature for this cell
            sig = self._cell_signature(cell)
            if not sig:
                continue

            if sig in signatures:
                # Found duplicate - merge
                original = signatures[sig]
                self._merge_cells(original, cell)
                eliminated += 1
            else:
                signatures[sig] = cell

        return eliminated

    def _cell_signature(self, cell: Cell) -> Optional[str]:
        """Create a unique signature for a cell based on operation and inputs."""
        # Sort input pins by name for determinism
        input_nets = []
        for pin_name in sorted(cell.inputs.keys()):
            pin = cell.inputs[pin_name]
            if not pin.net or not pin.net.driver:
                return None  # Can't create signature if inputs aren't connected
            input_nets.append(f"{pin_name}:{pin.net.driver.cell.id}")

        return f"{cell.op.name}({','.join(input_nets)})"

    def _merge_cells(self, keep: Cell, remove: Cell):
        """Merge two equivalent cells by redirecting outputs."""
        # Get output nets
        keep_out = keep.output if hasattr(keep, 'output') else None
        remove_out = remove.output if hasattr(remove, 'output') else None

        if not keep_out or not remove_out:
            return

        if not keep_out.net or not remove_out.net:
            return

        # Redirect all sinks from remove_out.net to keep_out.net
        if remove_out.net:
            for sink_pin in list(remove_out.net.sinks):
                # Disconnect from old net
                remove_out.net.sinks.remove(sink_pin)
                # Connect to new net
                keep_out.net.add_sink(sink_pin)

        # Remove the redundant cell
        self.netlist.remove_cell(remove)

    def identity_elimination(self) -> int:
        """
        Eliminate identity operations.

        Replaces operations like:
        - x & 1 = x (AND with all 1s)
        - x | 0 = x (OR with 0)
        - x + 0 = x (ADD with 0)
        - x ^ 0 = x (XOR with 0)
        - x << 0 = x (shift by 0)

        Returns:
            Number of identity operations eliminated
        """
        eliminated = 0
        cells_to_replace = []

        for cell_id, cell in list(self.netlist.cells.items()):
            replacement = None

            # Check for identity operations
            if cell.op in (CellOp.AND, CellOp.OR, CellOp.XOR, CellOp.ADD, CellOp.SUB,
                          CellOp.SHL, CellOp.SHR):
                # Check each input to see if any are constant identity elements
                for pin_name, pin in cell.inputs.items():
                    if not pin.net or not pin.net.driver:
                        continue

                    driver = pin.net.driver.cell
                    if driver.op != CellOp.CONST:
                        continue

                    const_value = driver.attributes.get("value", 0)

                    # Determine the other input pin
                    other_pin = None
                    if pin_name == "A" and "B" in cell.inputs:
                        other_pin = "B"
                    elif pin_name == "B" and "A" in cell.inputs:
                        other_pin = "A"

                    # Check if this is an identity element
                    if cell.op == CellOp.AND:
                        # x & all_1s = x
                        width = cell.output.width.width
                        all_ones = (1 << width) - 1
                        if const_value == all_ones and other_pin:
                            replacement = (other_pin, cell)
                            break

                    elif cell.op == CellOp.OR:
                        # x | 0 = x
                        if const_value == 0 and other_pin:
                            replacement = (other_pin, cell)
                            break

                    elif cell.op == CellOp.XOR:
                        # x ^ 0 = x
                        if const_value == 0 and other_pin:
                            replacement = (other_pin, cell)
                            break

                    elif cell.op == CellOp.ADD:
                        # x + 0 = x
                        if const_value == 0 and other_pin:
                            replacement = (other_pin, cell)
                            break

                    elif cell.op == CellOp.SUB:
                        # x - 0 = x (only when 0 is on the right)
                        if const_value == 0 and pin_name == "B" and other_pin:
                            replacement = (other_pin, cell)
                            break

                    elif cell.op in (CellOp.SHL, CellOp.SHR):
                        # x << 0 = x, x >> 0 = x (only when 0 is shift amount)
                        if const_value == 0 and pin_name == "B" and other_pin:
                            replacement = (other_pin, cell)
                            break

            if replacement:
                cells_to_replace.append(replacement)
                eliminated += 1

        # Apply replacements
        for pin_name, cell in cells_to_replace:
            self._replace_with_input(cell, pin_name)

        return eliminated

    def _replace_with_input(self, cell: Cell, input_pin_name: str):
        """Replace a cell with one of its inputs (bypass operation)."""
        # Get the input net
        input_pin = cell.inputs.get(input_pin_name)
        if not input_pin or not input_pin.net:
            return

        input_net = input_pin.net

        # Get output net
        output_net = cell.output.net if hasattr(cell, 'output') and cell.output else None
        if not output_net:
            return

        # Reconnect all sinks from output_net to input_net
        for sink_pin in list(output_net.sinks):
            output_net.sinks.remove(sink_pin)
            input_net.add_sink(sink_pin)

        # Remove the cell
        self.netlist.remove_cell(cell)

    def algebraic_simplification(self) -> int:
        """
        Perform algebraic simplifications.

        Simplifies operations like:
        - x & x = x
        - x | x = x
        - x ^ x = 0
        - x - x = 0

        Returns:
            Number of simplifications performed
        """
        simplified = 0
        cells_to_replace = []

        for cell_id, cell in list(self.netlist.cells.items()):
            # Check if both inputs are the same
            if len(cell.inputs) == 2:
                input_pins = list(cell.inputs.values())
                if len(input_pins) == 2:
                    pin_a, pin_b = input_pins
                    if (pin_a.net and pin_b.net and
                        pin_a.net.driver and pin_b.net.driver and
                        pin_a.net.driver.cell.id == pin_b.net.driver.cell.id):

                        # Same input on both sides
                        if cell.op in (CellOp.AND, CellOp.OR):
                            # x & x = x, x | x = x
                            cells_to_replace.append(("identity", cell, list(cell.inputs.keys())[0]))
                            simplified += 1
                        elif cell.op in (CellOp.XOR, CellOp.SUB):
                            # x ^ x = 0, x - x = 0
                            cells_to_replace.append(("zero", cell))
                            simplified += 1

        # Apply replacements
        for replacement_type, *args in cells_to_replace:
            if replacement_type == "identity":
                cell, pin_name = args
                self._replace_with_input(cell, pin_name)
            elif replacement_type == "zero":
                cell = args[0]
                self._replace_with_constant(cell, 0)

        return simplified

    def strength_reduction(self) -> int:
        """
        Reduce expensive operations to cheaper ones.

        Transforms:
        - x * 2^n → x << n (multiply by power of 2 to shift)
        - x / 2^n → x >> n (divide by power of 2 to shift)

        Returns:
            Number of reductions performed
        """
        reduced = 0
        cells_to_transform = []

        for cell_id, cell in list(self.netlist.cells.items()):
            if cell.op == CellOp.MUL:
                # Check if multiplying by a power of 2
                for pin_name, pin in cell.inputs.items():
                    if not pin.net or not pin.net.driver:
                        continue

                    driver = pin.net.driver.cell
                    if driver.op != CellOp.CONST:
                        continue

                    value = driver.attributes.get("value", 0)
                    if value > 0 and (value & (value - 1)) == 0:
                        # Value is a power of 2
                        shift_amount = (value - 1).bit_length()
                        other_pin = "B" if pin_name == "A" else "A"
                        cells_to_transform.append((cell, CellOp.SHL, other_pin, shift_amount))
                        reduced += 1
                        break

        # Apply transformations
        for cell, new_op, input_pin, shift_amount in cells_to_transform:
            self._transform_to_shift(cell, new_op, input_pin, shift_amount)

        return reduced

    def _transform_to_shift(self, cell: Cell, shift_op: CellOp, input_pin: str, shift_amount: int):
        """Transform a multiplication/division to a shift."""
        # Get input net
        input_net = cell.inputs[input_pin].net
        output_net = cell.output.net if hasattr(cell, 'output') and cell.output else None

        if not input_net or not output_net:
            return

        # Create new shift cell
        shift_cell = Cell(name=f"shift_{cell.name}", op=shift_op)

        # Add pins
        a_pin = shift_cell.add_input("A", input_net.width)
        input_net.add_sink(a_pin)

        # Create constant for shift amount
        const_cell = Cell(name=f"const_{shift_amount}", op=CellOp.CONST)
        const_cell.attributes["value"] = shift_amount
        const_pin = const_cell.add_output("Y", BitWidth(0, 0))
        const_net = Net(name=f"_shift_amt_{shift_amount}", width=BitWidth(0, 0))
        const_net.set_driver(const_pin)
        self.netlist.add_net(const_net)
        self.netlist.add_cell(const_cell)

        b_pin = shift_cell.add_input("B", const_net.width)
        const_net.add_sink(b_pin)

        out_pin = shift_cell.add_output("Y", output_net.width)

        # Reconnect output
        output_net.set_driver(out_pin)

        self.netlist.add_cell(shift_cell)

        # Remove old cell
        self.netlist.remove_cell(cell)


def optimize_netlist(netlist: Netlist, passes: list[str] = None) -> Dict[str, int]:
    """
    Convenience function to optimize a netlist.

    Args:
        netlist: The netlist to optimize (modified in-place)
        passes: List of optimization passes to run

    Returns:
        Dictionary of optimization statistics
    """
    optimizer = NetlistOptimizer(netlist)
    return optimizer.optimize(passes)
