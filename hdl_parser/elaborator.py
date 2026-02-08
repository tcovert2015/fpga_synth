"""
Elaborator — Converts AST to Netlist IR.

Takes a parsed Verilog AST and elaborates it into a flattened netlist:
- Resolves parameters and localparams
- Expands generate blocks
- Converts expressions to netlist cells
- Handles module hierarchy (for now, single module)

This is the first graph transformation: Tree (AST) → DAG (Netlist).
"""

from __future__ import annotations
from typing import Optional, Dict
from fpga_synth.hdl_parser.ast_nodes import *
from fpga_synth.ir.netlist import Netlist, Cell, Net, Pin
from fpga_synth.ir.types import CellOp, BitWidth, PortDir, NetType


class ElaborationError(Exception):
    """Error during elaboration."""
    pass


class Elaborator:
    """
    Elaborates an AST into a netlist.

    Current scope: Single module, basic combinational logic.
    Future: Module hierarchy, sequential logic, memories.
    """

    def __init__(self):
        self.netlist: Optional[Netlist] = None
        self.net_map: Dict[str, Net] = {}  # signal name → Net
        self.parameters: Dict[str, int] = {}  # parameter name → value
        self.memories: Dict[str, tuple[BitWidth, int]] = {}  # memory name → (data_width, depth)

    def elaborate(self, ast: SourceFile) -> Netlist:
        """
        Elaborate an AST into a netlist.

        Args:
            ast: Parsed Verilog source

        Returns:
            Elaborated netlist

        Raises:
            ElaborationError: If elaboration fails
        """
        if len(ast.modules) == 0:
            raise ElaborationError("No modules found in AST")

        # For now, elaborate only the first module
        # TODO: Handle module hierarchy
        module = ast.modules[0]
        return self.elaborate_module(module)

    def elaborate_module(self, module: Module) -> Netlist:
        """Elaborate a single module."""
        self.netlist = Netlist(name=module.name)
        self.net_map = {}
        self.parameters = {}
        self.memories = {}

        # Phase 1: Resolve parameters
        self._resolve_parameters(module)

        # Phase 2: Create primary I/O
        self._elaborate_ports(module)

        # Phase 3: Create nets for declared signals
        self._elaborate_declarations(module)

        # Phase 4: Elaborate module body
        self._elaborate_body(module)

        return self.netlist

    def _resolve_parameters(self, module: Module):
        """Resolve all parameter values."""
        # Module-level parameters
        for param in module.params:
            if param.value:
                self.parameters[param.name] = self._eval_const_expr(param.value)

        # Body parameters (localparam)
        for item in module.body:
            if isinstance(item, ParamDecl) and item.value:
                self.parameters[item.name] = self._eval_const_expr(item.value)

    def _elaborate_ports(self, module: Module):
        """Create MODULE_INPUT and MODULE_OUTPUT cells for ports."""
        for port in module.ports:
            width = self._get_width(port.range)

            if port.direction == "input":
                # Create input cell
                cell = Cell(name=port.name, op=CellOp.MODULE_INPUT)
                out_pin = cell.add_output("Y", width)
                self.netlist.add_cell(cell)
                self.netlist.inputs[port.name] = cell

                # Create net for this input
                net = Net(name=port.name, width=width)
                net.set_driver(out_pin)
                self.netlist.add_net(net)
                self.net_map[port.name] = net

            elif port.direction == "output":
                # Create output cell (will be connected later)
                cell = Cell(name=port.name, op=CellOp.MODULE_OUTPUT)
                in_pin = cell.add_input("A", width)
                self.netlist.add_cell(cell)
                self.netlist.outputs[port.name] = cell

                # Note: Output net is created when the driving logic is elaborated

    def _elaborate_declarations(self, module: Module):
        """Create nets for wire/reg declarations and detect memory arrays."""
        for item in module.body:
            if isinstance(item, NetDecl):
                width = self._get_width(item.range)

                # Check if this is a memory array (has unpacked dimensions)
                if item.array_dims:
                    # This is a memory array: reg [7:0] mem [0:255]
                    # Extract depth from first dimension
                    depth_range = item.array_dims[0]
                    dim_high = self._eval_const_expr(depth_range.msb)
                    dim_low = self._eval_const_expr(depth_range.lsb)
                    depth = abs(dim_high - dim_low) + 1

                    # Register as memory
                    self.memories[item.name] = (width, depth)
                    # Note: We don't create a single net for the memory
                    # Instead, each access creates MEMRD/MEMWR cells
                else:
                    # Regular signal - create net if not already created (e.g., by port)
                    if item.name not in self.net_map:
                        net = Net(name=item.name, width=width)
                        self.netlist.add_net(net)
                        self.net_map[item.name] = net

    def _elaborate_body(self, module: Module):
        """Elaborate all module body items."""
        for item in module.body:
            if isinstance(item, ContinuousAssign):
                self._elaborate_assign(item)
            elif isinstance(item, AlwaysBlock):
                self._elaborate_always_block(item)
            # TODO: InitialBlock, ModuleInstance, etc.

    def _elaborate_assign(self, assign: ContinuousAssign):
        """
        Elaborate a continuous assignment.

        Creates cells for the RHS expression and connects to LHS net.
        """
        # Get the LHS net
        if not isinstance(assign.lhs, Identifier):
            raise ElaborationError(f"LHS of assign must be identifier, got {type(assign.lhs).__name__}")

        lhs_name = assign.lhs.name
        if lhs_name not in self.net_map:
            # Create net if it doesn't exist (implicit wire declaration)
            net = Net(name=lhs_name, width=BitWidth(0, 0))
            self.netlist.add_net(net)
            self.net_map[lhs_name] = net

        lhs_net = self.net_map[lhs_name]

        # Elaborate RHS expression to get output net
        rhs_net = self._elaborate_expr(assign.rhs)

        # Connect RHS output to LHS
        # If RHS driver exists, connect it to LHS net
        if rhs_net.driver:
            lhs_net.set_driver(rhs_net.driver)
            # Update driver pin's net to point to LHS net
            rhs_net.driver.net = lhs_net

    def _elaborate_always_block(self, always: AlwaysBlock):
        """
        Elaborate an always block.

        Detects sequential vs combinational based on sensitivity list:
        - @(posedge clk) or @(negedge rst) → Sequential (creates DFF cells)
        - @(*) → Combinational (elaborates as continuous logic)
        """
        # Check if this is sequential (has edge-sensitive signals)
        has_edge = any(sens.edge in ('posedge', 'negedge') for sens in always.sensitivity)

        if has_edge:
            self._elaborate_sequential_always(always)
        else:
            # Combinational always block - elaborate as continuous assignments
            self._elaborate_combinational_always(always)

    def _elaborate_sequential_always(self, always: AlwaysBlock):
        """Elaborate sequential always block with flip-flops."""
        # Find clock and reset signals
        clk_signal = None
        rst_signal = None
        rst_polarity = None  # 'posedge' or 'negedge'

        for sens in always.sensitivity:
            if sens.edge == 'posedge':
                if 'clk' in sens.signal.name.lower():
                    clk_signal = sens.signal.name
                else:
                    # Assume first posedge is clock
                    if clk_signal is None:
                        clk_signal = sens.signal.name
            elif sens.edge == 'negedge':
                # Usually reset
                rst_signal = sens.signal.name
                rst_polarity = 'negedge'

        if not clk_signal:
            raise ElaborationError("Sequential always block must have a clock signal")

        # Analyze the always block body to find register assignments
        # For now, simple case: direct non-blocking assignments
        for stmt in always.body:
            if isinstance(stmt, NonBlockingAssign):
                self._create_dff(stmt, clk_signal, rst_signal, rst_polarity)
            elif isinstance(stmt, IfStatement):
                # Handle if statement (possibly reset logic)
                self._elaborate_sequential_if(stmt, clk_signal, rst_signal, rst_polarity)

    def _elaborate_sequential_if(self, if_stmt: IfStatement, clk_signal: str,
                                   rst_signal: Optional[str], rst_polarity: Optional[str]):
        """Elaborate if statement in sequential context (handles reset)."""
        # Check if condition is reset check
        is_reset_check = False
        if rst_signal and isinstance(if_stmt.cond, UnaryOp):
            if if_stmt.cond.op == '!' and isinstance(if_stmt.cond.operand, Identifier):
                if if_stmt.cond.operand.name == rst_signal:
                    is_reset_check = True

        if is_reset_check:
            # Then branch is reset, else branch is normal operation
            # Process else branch recursively
            self._elaborate_sequential_body(if_stmt.else_body, clk_signal, rst_signal, rst_polarity)
        else:
            # Not a reset check - this could be enable logic
            # Process then branch recursively
            self._elaborate_sequential_body(if_stmt.then_body, clk_signal, rst_signal, rst_polarity)
            # Note: For proper enable, we'd need DFFRE (DFF with reset and enable)

    def _elaborate_sequential_body(self, stmts: list, clk_signal: str,
                                     rst_signal: Optional[str], rst_polarity: Optional[str]):
        """Recursively elaborate statements in a sequential context."""
        for stmt in stmts:
            if isinstance(stmt, NonBlockingAssign):
                self._create_dff(stmt, clk_signal, rst_signal, rst_polarity)
            elif isinstance(stmt, IfStatement):
                self._elaborate_sequential_if(stmt, clk_signal, rst_signal, rst_polarity)

    def _create_dff(self, assign: NonBlockingAssign, clk_signal: str,
                    rst_signal: Optional[str], rst_polarity: Optional[str]):
        """Create a DFF cell for a register assignment or memory write."""
        # Check if LHS is a memory write: mem[addr] <= data
        if isinstance(assign.lhs, BitSelect):
            if isinstance(assign.lhs.target, Identifier) and assign.lhs.target.name in self.memories:
                # This is a memory write
                self._elaborate_memory_write(
                    mem_name=assign.lhs.target.name,
                    addr_expr=assign.lhs.msb,
                    data_expr=assign.rhs,
                    clk_signal=clk_signal
                )
                return

        if not isinstance(assign.lhs, Identifier):
            return  # Skip other complex LHS for now

        reg_name = assign.lhs.name

        # Determine DFF type
        if rst_signal:
            cell_op = CellOp.DFFR  # DFF with reset
        else:
            cell_op = CellOp.DFF   # Simple DFF

        # Create DFF cell
        cell = Cell(name=f"dff_{reg_name}", op=cell_op)

        # Get register net (should already exist from declaration)
        if reg_name not in self.net_map:
            # Create net if not declared
            net = Net(name=reg_name, width=BitWidth(0, 0))
            self.netlist.add_net(net)
            self.net_map[reg_name] = net

        reg_net = self.net_map[reg_name]

        # Add pins
        clk_pin = cell.add_input("CLK", BitWidth(0, 0))
        d_pin = cell.add_input("D", reg_net.width)
        q_pin = cell.add_output("Q", reg_net.width)

        if rst_signal:
            rst_pin = cell.add_input("RST", BitWidth(0, 0))
            # Connect reset signal
            if rst_signal in self.net_map:
                self.net_map[rst_signal].add_sink(rst_pin)

        # Connect clock
        if clk_signal in self.net_map:
            self.net_map[clk_signal].add_sink(clk_pin)

        # Elaborate RHS to get D input
        rhs_net = self._elaborate_expr(assign.rhs)
        rhs_net.add_sink(d_pin)

        # Connect Q output to register net
        reg_net.set_driver(q_pin)

        self.netlist.add_cell(cell)

    def _elaborate_combinational_always(self, always: AlwaysBlock):
        """Elaborate combinational always block."""
        # For now, treat as continuous assignments
        # TODO: Handle more complex statements
        for stmt in always.body:
            if isinstance(stmt, BlockingAssign):
                # Convert to continuous assignment form
                self._elaborate_blocking_assign(stmt)

    def _elaborate_blocking_assign(self, assign: BlockingAssign):
        """Elaborate blocking assignment (in combinational context)."""
        if not isinstance(assign.lhs, Identifier):
            return

        lhs_name = assign.lhs.name

        # Get or create LHS net
        if lhs_name not in self.net_map:
            net = Net(name=lhs_name, width=BitWidth(0, 0))
            self.netlist.add_net(net)
            self.net_map[lhs_name] = net

        lhs_net = self.net_map[lhs_name]

        # Elaborate RHS
        rhs_net = self._elaborate_expr(assign.rhs)

        # Connect
        if rhs_net.driver:
            lhs_net.set_driver(rhs_net.driver)
            rhs_net.driver.net = lhs_net

    def _elaborate_expr(self, expr: Expr) -> Net:
        """
        Elaborate an expression into cells.

        Returns the net containing the expression's output.
        """
        if isinstance(expr, NumberLiteral):
            return self._elaborate_const(expr)

        elif isinstance(expr, Identifier):
            # Reference to existing signal
            if expr.name not in self.net_map:
                raise ElaborationError(f"Undefined signal: {expr.name}")
            return self.net_map[expr.name]

        elif isinstance(expr, BinaryOp):
            return self._elaborate_binary_op(expr)

        elif isinstance(expr, UnaryOp):
            return self._elaborate_unary_op(expr)

        elif isinstance(expr, TernaryOp):
            return self._elaborate_ternary_op(expr)

        elif isinstance(expr, Concat):
            return self._elaborate_concat(expr)

        elif isinstance(expr, BitSelect):
            return self._elaborate_bit_select(expr)

        else:
            raise ElaborationError(f"Unsupported expression type: {type(expr).__name__}")

    def _elaborate_const(self, lit: NumberLiteral) -> Net:
        """Create a CONST cell for a number literal."""
        cell = Cell(name=f"const_{lit.value}", op=CellOp.CONST)
        cell.attributes["value"] = lit.value
        cell.attributes["width"] = lit.width

        width = BitWidth.from_width(lit.width)
        out_pin = cell.add_output("Y", width)

        self.netlist.add_cell(cell)

        # Create output net
        net = Net(name=f"_const_{cell.id}", width=width)
        net.set_driver(out_pin)
        self.netlist.add_net(net)

        return net

    def _elaborate_binary_op(self, expr: BinaryOp) -> Net:
        """Elaborate a binary operation."""
        # Map Verilog operators to CellOp
        op_map = {
            "&": CellOp.AND,
            "|": CellOp.OR,
            "^": CellOp.XOR,
            "+": CellOp.ADD,
            "-": CellOp.SUB,
            "*": CellOp.MUL,
            "==": CellOp.EQ,
            "!=": CellOp.NEQ,
            "<": CellOp.LT,
            "<=": CellOp.LE,
            ">": CellOp.GT,
            ">=": CellOp.GE,
            "<<": CellOp.SHL,
            ">>": CellOp.SHR,
        }

        if expr.op not in op_map:
            raise ElaborationError(f"Unsupported binary operator: {expr.op}")

        cell_op = op_map[expr.op]

        # Elaborate operands
        left_net = self._elaborate_expr(expr.left)
        right_net = self._elaborate_expr(expr.right)

        # Create cell
        cell = Cell(name=f"{cell_op.name.lower()}_{left_net.name}_{right_net.name}", op=cell_op)

        # Determine output width (simplified - needs proper width inference)
        out_width = max(left_net.width.width, right_net.width.width)
        if cell_op in (CellOp.EQ, CellOp.NEQ, CellOp.LT, CellOp.LE, CellOp.GT, CellOp.GE):
            out_width = 1  # Comparison operators return 1 bit

        # Add pins
        a_pin = cell.add_input("A", left_net.width)
        b_pin = cell.add_input("B", right_net.width)
        y_pin = cell.add_output("Y", BitWidth.from_width(out_width))

        # Connect inputs
        left_net.add_sink(a_pin)
        right_net.add_sink(b_pin)

        self.netlist.add_cell(cell)

        # Create output net
        out_net = Net(name=f"_{cell.op.name.lower()}_{cell.id}", width=BitWidth.from_width(out_width))
        out_net.set_driver(y_pin)
        self.netlist.add_net(out_net)

        return out_net

    def _elaborate_unary_op(self, expr: UnaryOp) -> Net:
        """Elaborate a unary operation."""
        op_map = {
            "~": CellOp.NOT,
            "!": CellOp.NOT,  # Logical NOT - same as bitwise for single bit
            "-": CellOp.NEG,
            "&": CellOp.REDUCE_AND,
            "|": CellOp.REDUCE_OR,
            "^": CellOp.REDUCE_XOR,
        }

        if expr.op not in op_map:
            raise ElaborationError(f"Unsupported unary operator: {expr.op}")

        cell_op = op_map[expr.op]

        # Elaborate operand
        operand_net = self._elaborate_expr(expr.operand)

        # Create cell
        cell = Cell(name=f"{cell_op.name.lower()}_{operand_net.name}", op=cell_op)

        # Determine output width
        if cell_op in (CellOp.REDUCE_AND, CellOp.REDUCE_OR, CellOp.REDUCE_XOR):
            out_width = 1
        else:
            out_width = operand_net.width.width

        # Add pins
        a_pin = cell.add_input("A", operand_net.width)
        y_pin = cell.add_output("Y", BitWidth.from_width(out_width))

        # Connect input
        operand_net.add_sink(a_pin)

        self.netlist.add_cell(cell)

        # Create output net
        out_net = Net(name=f"_{cell.op.name.lower()}_{cell.id}", width=BitWidth.from_width(out_width))
        out_net.set_driver(y_pin)
        self.netlist.add_net(out_net)

        return out_net

    def _elaborate_ternary_op(self, expr: TernaryOp) -> Net:
        """Elaborate a ternary (conditional) operation as a MUX."""
        # Elaborate condition and operands
        cond_net = self._elaborate_expr(expr.cond)
        true_net = self._elaborate_expr(expr.true_val)
        false_net = self._elaborate_expr(expr.false_val)

        # Create MUX cell: out = sel ? true : false
        cell = Cell(name=f"mux_{cond_net.name}", op=CellOp.MUX)

        # MUX(sel, false, true) - note the order!
        sel_pin = cell.add_input("S", cond_net.width)
        a_pin = cell.add_input("A", false_net.width)
        b_pin = cell.add_input("B", true_net.width)

        out_width = max(true_net.width.width, false_net.width.width)
        y_pin = cell.add_output("Y", BitWidth.from_width(out_width))

        # Connect
        cond_net.add_sink(sel_pin)
        false_net.add_sink(a_pin)
        true_net.add_sink(b_pin)

        self.netlist.add_cell(cell)

        # Create output net
        out_net = Net(name=f"_mux_{cell.id}", width=BitWidth.from_width(out_width))
        out_net.set_driver(y_pin)
        self.netlist.add_net(out_net)

        return out_net

    def _elaborate_concat(self, expr: Concat) -> Net:
        """Elaborate concatenation {a, b, c}."""
        # Elaborate all parts
        part_nets = [self._elaborate_expr(part) for part in expr.parts]

        # Create CONCAT cell
        cell = Cell(name=f"concat_{len(part_nets)}", op=CellOp.CONCAT)

        # Add input pins for each part
        total_width = 0
        for i, pnet in enumerate(part_nets):
            pin = cell.add_input(f"A{i}", pnet.width)
            pnet.add_sink(pin)
            total_width += pnet.width.width

        # Add output
        y_pin = cell.add_output("Y", BitWidth.from_width(total_width))

        self.netlist.add_cell(cell)

        # Create output net
        out_net = Net(name=f"_concat_{cell.id}", width=BitWidth.from_width(total_width))
        out_net.set_driver(y_pin)
        self.netlist.add_net(out_net)

        return out_net

    def _elaborate_bit_select(self, expr: BitSelect) -> Net:
        """Elaborate bit select, part select, or memory access."""
        # Check if target is a memory array
        if isinstance(expr.target, Identifier) and expr.target.name in self.memories:
            # This is a memory read: mem[addr]
            return self._elaborate_memory_read(expr.target.name, expr.msb)

        # Regular bit select/part select
        # Elaborate target
        target_net = self._elaborate_expr(expr.target)

        # Create SLICE cell
        cell = Cell(name=f"slice_{target_net.name}", op=CellOp.SLICE)

        # Evaluate bit indices
        msb = self._eval_const_expr(expr.msb)
        if expr.lsb is not None:
            lsb = self._eval_const_expr(expr.lsb)
        else:
            lsb = msb  # Single bit select

        # Store slice range in attributes
        cell.attributes["msb"] = msb
        cell.attributes["lsb"] = lsb

        # Determine output width
        out_width = msb - lsb + 1

        # Add pins
        in_pin = cell.add_input("A", target_net.width)
        out_pin = cell.add_output("Y", BitWidth.from_width(out_width))

        # Connect
        target_net.add_sink(in_pin)

        self.netlist.add_cell(cell)

        # Create output net
        out_net = Net(name=f"_slice_{cell.id}", width=BitWidth.from_width(out_width))
        out_net.set_driver(out_pin)
        self.netlist.add_net(out_net)

        return out_net

    def _elaborate_memory_read(self, mem_name: str, addr_expr: Expr) -> Net:
        """Elaborate a memory read: data = mem[addr]"""
        # Get memory info
        data_width, depth = self.memories[mem_name]

        # Elaborate address expression
        addr_net = self._elaborate_expr(addr_expr)

        # Create MEMRD cell
        next_id = len(self.netlist.cells)
        cell = Cell(name=f"memrd_{mem_name}_{next_id}", op=CellOp.MEMRD)
        cell.attributes["memory"] = mem_name
        cell.attributes["depth"] = depth

        # Add pins: address input, data output
        addr_pin = cell.add_input("ADDR", addr_net.width)
        data_pin = cell.add_output("DATA", data_width)

        # Connect address
        addr_net.add_sink(addr_pin)

        self.netlist.add_cell(cell)

        # Create output net for read data
        out_net = Net(name=f"_memrd_{mem_name}_{cell.id}", width=data_width)
        out_net.set_driver(data_pin)
        self.netlist.add_net(out_net)

        return out_net

    def _elaborate_memory_write(self, mem_name: str, addr_expr: Expr,
                                  data_expr: Expr, clk_signal: str,
                                  enable_expr: Optional[Expr] = None):
        """Elaborate a memory write: mem[addr] <= data"""
        # Get memory info
        data_width, depth = self.memories[mem_name]

        # Elaborate address and data expressions
        addr_net = self._elaborate_expr(addr_expr)
        data_net = self._elaborate_expr(data_expr)

        # Create MEMWR cell
        next_id = len(self.netlist.cells)
        cell = Cell(name=f"memwr_{mem_name}_{next_id}", op=CellOp.MEMWR)
        cell.attributes["memory"] = mem_name
        cell.attributes["depth"] = depth

        # Add pins: clock, address, data, enable
        clk_pin = cell.add_input("CLK", BitWidth(0, 0))
        addr_pin = cell.add_input("ADDR", addr_net.width)
        data_pin = cell.add_input("DATA", data_width)

        # Connect address and data
        addr_net.add_sink(addr_pin)
        data_net.add_sink(data_pin)

        # Connect clock
        if clk_signal in self.net_map:
            clk_net = self.net_map[clk_signal]
            clk_net.add_sink(clk_pin)

        # Handle write enable
        if enable_expr:
            en_net = self._elaborate_expr(enable_expr)
            en_pin = cell.add_input("EN", BitWidth(0, 0))
            en_net.add_sink(en_pin)
        else:
            # Always enabled - create constant 1
            const_one = self._elaborate_const(NumberLiteral(raw="1", value=1, width=1))
            en_pin = cell.add_input("EN", BitWidth(0, 0))
            const_one.add_sink(en_pin)

        self.netlist.add_cell(cell)

    def _get_width(self, range_node: Optional[Range]) -> BitWidth:
        """Extract bit width from a Range node."""
        if range_node is None:
            return BitWidth(0, 0)  # Single bit

        msb = self._eval_const_expr(range_node.msb)
        lsb = self._eval_const_expr(range_node.lsb)
        return BitWidth(msb, lsb)

    def _eval_const_expr(self, expr: Expr) -> int:
        """Evaluate a constant expression (for parameters, ranges)."""
        if isinstance(expr, NumberLiteral):
            return expr.value

        elif isinstance(expr, Identifier):
            # Look up parameter
            if expr.name in self.parameters:
                return self.parameters[expr.name]
            raise ElaborationError(f"Undefined parameter: {expr.name}")

        elif isinstance(expr, BinaryOp):
            left = self._eval_const_expr(expr.left)
            right = self._eval_const_expr(expr.right)

            ops = {
                "+": lambda a, b: a + b,
                "-": lambda a, b: a - b,
                "*": lambda a, b: a * b,
                "/": lambda a, b: a // b,
                "%": lambda a, b: a % b,
                "&": lambda a, b: a & b,
                "|": lambda a, b: a | b,
                "^": lambda a, b: a ^ b,
                "<<": lambda a, b: a << b,
                ">>": lambda a, b: a >> b,
            }

            if expr.op in ops:
                return ops[expr.op](left, right)

        raise ElaborationError(f"Cannot evaluate non-constant expression: {type(expr).__name__}")


def elaborate(ast: SourceFile) -> Netlist:
    """
    Convenience function to elaborate an AST.

    Args:
        ast: Parsed Verilog source

    Returns:
        Elaborated netlist
    """
    elaborator = Elaborator()
    return elaborator.elaborate(ast)
