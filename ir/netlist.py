"""
Netlist — The core graph intermediate representation.

The netlist is a directed hypergraph:
  - Nodes (Cells) perform operations (AND, ADD, MUX, DFF, etc.)
  - Hyperedges (Nets) connect one driver (source pin) to one or more sink pins.
  - Each Cell has named input/output Pins.
  - Each Pin connects to exactly one Net.

Graph properties we maintain:
  - Topological ordering (for dataflow analysis, STA)
  - Fanin/fanout adjacency (for traversal, optimization)
  - The combinational portion is a DAG; sequential elements (DFF) create cycles
    that are broken at register boundaries for analysis.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Iterator
from collections import defaultdict
import itertools

from fpga_synth.ir.types import CellOp, BitWidth, PortDir


# ---------------------------------------------------------------------------
# Unique ID generation
# ---------------------------------------------------------------------------

_id_counter = itertools.count(1)


def _new_id() -> int:
    return next(_id_counter)


def reset_ids():
    """Reset the global ID counter (useful for tests)."""
    global _id_counter
    _id_counter = itertools.count(1)


# ---------------------------------------------------------------------------
# Pin — A connection point on a Cell
# ---------------------------------------------------------------------------

@dataclass
class Pin:
    """A named connection point on a cell.
    
    Each pin belongs to one cell and connects to one net.
    """
    id: int = field(default_factory=_new_id, repr=False)
    name: str = ""
    direction: PortDir = PortDir.INPUT
    width: BitWidth = field(default_factory=lambda: BitWidth(0, 0))
    cell: Optional[Cell] = field(default=None, repr=False)
    net: Optional[Net] = field(default=None, repr=False)
    
    def __hash__(self):
        return self.id
    
    def __eq__(self, other):
        return isinstance(other, Pin) and self.id == other.id


# ---------------------------------------------------------------------------
# Net — A hyperedge connecting one driver to N sinks
# ---------------------------------------------------------------------------

@dataclass
class Net:
    """A signal net — a hyperedge in the netlist graph.
    
    A net has exactly one driver pin and zero or more sink pins.
    This models the physical reality: one wire is driven by one source.
    """
    id: int = field(default_factory=_new_id)
    name: str = ""
    width: BitWidth = field(default_factory=lambda: BitWidth(0, 0))
    driver: Optional[Pin] = field(default=None, repr=False)
    sinks: list[Pin] = field(default_factory=list, repr=False)
    
    def __hash__(self):
        return self.id
    
    def __eq__(self, other):
        return isinstance(other, Net) and self.id == other.id
    
    @property
    def fanout(self) -> int:
        return len(self.sinks)
    
    def add_sink(self, pin: Pin):
        self.sinks.append(pin)
        pin.net = self
    
    def remove_sink(self, pin: Pin):
        self.sinks.remove(pin)
        if pin.net is self:
            pin.net = None
    
    def set_driver(self, pin: Pin):
        self.driver = pin
        pin.net = self


# ---------------------------------------------------------------------------
# Cell — A node in the netlist DAG
# ---------------------------------------------------------------------------

@dataclass
class Cell:
    """A logic cell — a node in the netlist graph.
    
    Each cell performs an operation (CellOp) and has named input/output pins.
    Attributes can store extra info (constant value, slice range, etc.)
    """
    id: int = field(default_factory=_new_id)
    name: str = ""
    op: CellOp = CellOp.BUF
    inputs: dict[str, Pin] = field(default_factory=dict)
    outputs: dict[str, Pin] = field(default_factory=dict)
    attributes: dict[str, object] = field(default_factory=dict)
    
    def __hash__(self):
        return self.id
    
    def __eq__(self, other):
        return isinstance(other, Cell) and self.id == other.id
    
    def add_input(self, name: str, width: BitWidth = None) -> Pin:
        if width is None:
            width = BitWidth(0, 0)
        pin = Pin(name=name, direction=PortDir.INPUT, width=width, cell=self)
        self.inputs[name] = pin
        return pin
    
    def add_output(self, name: str, width: BitWidth = None) -> Pin:
        if width is None:
            width = BitWidth(0, 0)
        pin = Pin(name=name, direction=PortDir.OUTPUT, width=width, cell=self)
        self.outputs[name] = pin
        return pin
    
    @property
    def output(self) -> Pin:
        """Convenience: return the single output pin (most cells have exactly one)."""
        assert len(self.outputs) == 1, f"Cell {self.name} has {len(self.outputs)} outputs"
        return next(iter(self.outputs.values()))
    
    def fanin_cells(self) -> list[Cell]:
        """Return all cells driving this cell's inputs (graph predecessors)."""
        result = []
        for pin in self.inputs.values():
            if pin.net and pin.net.driver and pin.net.driver.cell:
                result.append(pin.net.driver.cell)
        return result
    
    def fanout_cells(self) -> list[Cell]:
        """Return all cells driven by this cell's outputs (graph successors)."""
        result = []
        for pin in self.outputs.values():
            if pin.net:
                for sink in pin.net.sinks:
                    if sink.cell:
                        result.append(sink.cell)
        return result


# ---------------------------------------------------------------------------
# Netlist — The top-level graph container
# ---------------------------------------------------------------------------

class Netlist:
    """The top-level netlist graph.
    
    Contains all cells, nets, and module I/O.
    Provides graph operations: traversal, topological sort, etc.
    """
    
    def __init__(self, name: str = "top"):
        self.name = name
        self.cells: dict[int, Cell] = {}
        self.nets: dict[int, Net] = {}
        
        # Module-level I/O cells
        self.inputs: dict[str, Cell] = {}    # name → MODULE_INPUT cell
        self.outputs: dict[str, Cell] = {}   # name → MODULE_OUTPUT cell
        
        # Cached topological order (invalidated on modification)
        self._topo_order: Optional[list[Cell]] = None
        self._topo_dirty = True
    
    # ---- Construction API ----
    
    def add_cell(self, cell: Cell) -> Cell:
        """Add a cell to the netlist."""
        self.cells[cell.id] = cell
        self._topo_dirty = True
        return cell
    
    def add_net(self, net: Net) -> Net:
        """Add a net to the netlist."""
        self.nets[net.id] = net
        return net
    
    def create_cell(self, op: CellOp, name: str = "",
                     input_names: list[str] = None,
                     output_names: list[str] = None,
                     width: BitWidth = None,
                     **attributes) -> Cell:
        """Create and add a cell with the given ports."""
        cell = Cell(name=name, op=op, attributes=attributes)
        
        if width is None:
            width = BitWidth(0, 0)
        
        if input_names:
            for iname in input_names:
                cell.add_input(iname, width)
        
        if output_names:
            for oname in output_names:
                cell.add_output(oname, width)
        else:
            cell.add_output("Y", width)
        
        return self.add_cell(cell)
    
    def create_net(self, name: str = "", width: BitWidth = None) -> Net:
        """Create and add a net."""
        net = Net(name=name, width=width or BitWidth(0, 0))
        return self.add_net(net)
    
    def connect(self, driver_pin: Pin, sink_pin: Pin, net: Net = None) -> Net:
        """Connect a driver pin to a sink pin via a net.
        
        If no net is given and the driver already has one, reuse it.
        Otherwise create a new net.
        """
        if net is None:
            if driver_pin.net is not None:
                net = driver_pin.net
            else:
                net = self.create_net(
                    name=f"n{driver_pin.id}_{sink_pin.id}",
                    width=driver_pin.width
                )
        
        if net.driver is None:
            net.set_driver(driver_pin)
        
        net.add_sink(sink_pin)
        
        if net.id not in self.nets:
            self.add_net(net)
        
        self._topo_dirty = True
        return net
    
    def add_module_input(self, name: str, width: BitWidth) -> Cell:
        """Add a primary input port to the design."""
        cell = self.create_cell(
            CellOp.MODULE_INPUT, name=name,
            output_names=["Y"], width=width
        )
        self.inputs[name] = cell
        return cell
    
    def add_module_output(self, name: str, width: BitWidth) -> Cell:
        """Add a primary output port to the design."""
        cell = self.create_cell(
            CellOp.MODULE_OUTPUT, name=name,
            input_names=["A"], width=width
        )
        self.outputs[name] = cell
        return cell
    
    # ---- Removal ----
    
    def remove_cell(self, cell: Cell):
        """Remove a cell and disconnect all its pins."""
        for pin in list(cell.inputs.values()):
            if pin.net:
                pin.net.remove_sink(pin)
        for pin in list(cell.outputs.values()):
            if pin.net:
                # Disconnect all sinks of this net
                for sink in list(pin.net.sinks):
                    pin.net.remove_sink(sink)
                net = pin.net
                net.driver = None
                # Remove orphan net
                if net.id in self.nets:
                    del self.nets[net.id]
        
        if cell.id in self.cells:
            del self.cells[cell.id]
        
        # Remove from I/O dicts if present
        self.inputs = {k: v for k, v in self.inputs.items() if v.id != cell.id}
        self.outputs = {k: v for k, v in self.outputs.items() if v.id != cell.id}
        self._topo_dirty = True
    
    # ---- Graph Traversal ----
    
    def topological_sort(self) -> list[Cell]:
        """Return cells in topological order (Kahn's algorithm).
        
        Sequential elements (DFF*) have their D-input edges ignored for
        ordering purposes — they break combinational cycles.
        
        Returns cells from inputs toward outputs.
        """
        if not self._topo_dirty and self._topo_order is not None:
            return self._topo_order
        
        # Compute in-degree for each cell (combinational edges only)
        in_degree: dict[int, int] = defaultdict(int)
        for cell in self.cells.values():
            if cell.id not in in_degree:
                in_degree[cell.id] = 0
            for fanin in cell.fanin_cells():
                # Skip back-edges through DFFs
                if fanin.op not in (CellOp.DFF, CellOp.DFFR, CellOp.DFFRE, CellOp.DFFS):
                    in_degree[cell.id] += 1
        
        # Seed with zero in-degree cells
        queue = [cid for cid, deg in in_degree.items() if deg == 0]
        order = []
        
        while queue:
            cid = queue.pop(0)
            cell = self.cells[cid]
            order.append(cell)
            
            for succ in cell.fanout_cells():
                if succ.op in (CellOp.DFF, CellOp.DFFR, CellOp.DFFRE, CellOp.DFFS):
                    # DFFs are always "ready" from the combinational perspective
                    # but we still want them in the order
                    continue
                in_degree[succ.id] -= 1
                if in_degree[succ.id] == 0:
                    queue.append(succ.id)
        
        # Add any DFFs not yet in order
        dff_ops = {CellOp.DFF, CellOp.DFFR, CellOp.DFFRE, CellOp.DFFS}
        ordered_ids = {c.id for c in order}
        for cell in self.cells.values():
            if cell.id not in ordered_ids:
                order.append(cell)
        
        self._topo_order = order
        self._topo_dirty = False
        return order
    
    def fanin_cone(self, cell: Cell) -> set[Cell]:
        """Return the transitive fanin cone of a cell (all predecessors in the DAG).
        
        This is a reverse-reachability search — fundamental for cut enumeration
        and cone-based optimization.
        """
        visited = set()
        stack = [cell]
        while stack:
            c = stack.pop()
            if c.id in visited:
                continue
            visited.add(c.id)
            for pred in c.fanin_cells():
                stack.append(pred)
        return {self.cells[cid] for cid in visited}
    
    def fanout_cone(self, cell: Cell) -> set[Cell]:
        """Return the transitive fanout cone of a cell."""
        visited = set()
        stack = [cell]
        while stack:
            c = stack.pop()
            if c.id in visited:
                continue
            visited.add(c.id)
            for succ in c.fanout_cells():
                stack.append(succ)
        return {self.cells[cid] for cid in visited}
    
    def find_dead_cells(self) -> set[Cell]:
        """Find cells not reachable from any output (dead logic).
        
        Uses reverse BFS from all outputs — any cell not visited is dead.
        """
        live = set()
        stack = list(self.outputs.values())
        while stack:
            cell = stack.pop()
            if cell.id in live:
                continue
            live.add(cell.id)
            for pred in cell.fanin_cells():
                stack.append(pred)
        
        return {c for c in self.cells.values() if c.id not in live}
    
    def remove_dead_logic(self) -> int:
        """Remove all dead cells. Returns count of cells removed."""
        dead = self.find_dead_cells()
        for cell in dead:
            self.remove_cell(cell)
        return len(dead)
    
    def detect_combinational_loops(self) -> list[list[Cell]]:
        """Detect combinational loops (illegal in synthesis).
        
        Uses Tarjan's SCC algorithm on the combinational subgraph.
        Any SCC with more than one node is a combinational loop.
        """
        dff_ops = {CellOp.DFF, CellOp.DFFR, CellOp.DFFRE, CellOp.DFFS}
        
        index_counter = [0]
        stack = []
        lowlink = {}
        index = {}
        on_stack = set()
        sccs = []
        
        def strongconnect(cell: Cell):
            index[cell.id] = index_counter[0]
            lowlink[cell.id] = index_counter[0]
            index_counter[0] += 1
            stack.append(cell)
            on_stack.add(cell.id)
            
            for succ in cell.fanout_cells():
                if succ.op in dff_ops:
                    continue  # Don't follow through sequential elements
                if succ.id not in index:
                    strongconnect(succ)
                    lowlink[cell.id] = min(lowlink[cell.id], lowlink[succ.id])
                elif succ.id in on_stack:
                    lowlink[cell.id] = min(lowlink[cell.id], index[succ.id])
            
            if lowlink[cell.id] == index[cell.id]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w.id)
                    scc.append(w)
                    if w.id == cell.id:
                        break
                if len(scc) > 1:
                    sccs.append(scc)
        
        for cell in self.cells.values():
            if cell.id not in index:
                strongconnect(cell)
        
        return sccs
    
    # ---- Statistics ----
    
    def stats(self) -> dict:
        """Return summary statistics about the netlist."""
        op_counts = defaultdict(int)
        for cell in self.cells.values():
            op_counts[cell.op.name] += 1
        
        return {
            "name": self.name,
            "cells": len(self.cells),
            "nets": len(self.nets),
            "inputs": len(self.inputs),
            "outputs": len(self.outputs),
            "ops": dict(op_counts),
        }
    
    def __repr__(self):
        s = self.stats()
        return (f"Netlist('{s['name']}', "
                f"cells={s['cells']}, nets={s['nets']}, "
                f"inputs={s['inputs']}, outputs={s['outputs']})")
