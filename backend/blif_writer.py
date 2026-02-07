"""
BLIF (Berkeley Logic Interchange Format) writer.

Exports a Netlist to BLIF format for verification against other tools
like ABC and Yosys. This is a simplified writer that handles the most
common cell types.
"""

from fpga_synth.ir.netlist import Netlist, Cell, Net
from fpga_synth.ir.types import CellOp


def netlist_to_blif(netlist: Netlist) -> str:
    """Convert a netlist to BLIF format string."""
    lines = []
    lines.append(f".model {netlist.name}")
    
    # Inputs
    input_names = list(netlist.inputs.keys())
    if input_names:
        lines.append(f".inputs {' '.join(input_names)}")
    
    # Outputs
    output_names = list(netlist.outputs.keys())
    if output_names:
        lines.append(f".outputs {' '.join(output_names)}")
    
    lines.append("")
    
    # Helper: get net name for a pin
    def pin_net_name(pin) -> str:
        if pin and pin.net:
            if pin.net.name:
                return pin.net.name
            return f"_n{pin.net.id}"
        return "?"
    
    # Emit cells
    topo = netlist.topological_sort()
    for cell in topo:
        if cell.op == CellOp.MODULE_INPUT:
            continue  # Primary inputs are declared above
        
        if cell.op == CellOp.MODULE_OUTPUT:
            # Connect output signal to output name
            a_pin = cell.inputs.get("A")
            if a_pin and a_pin.net:
                src = pin_net_name(a_pin)
                lines.append(f"# output {cell.name}")
                lines.append(f".names {src} {cell.name}")
                lines.append("1 1")
                lines.append("")
            continue
        
        if cell.op == CellOp.CONST:
            val = cell.attributes.get("value", 0)
            out = pin_net_name(cell.output)
            lines.append(f".names {out}")
            if val:
                lines.append("1")
            else:
                lines.append("")  # No lines = constant 0
            lines.append("")
            continue
        
        if cell.op == CellOp.BUF:
            a = pin_net_name(cell.inputs["A"])
            y = pin_net_name(cell.output)
            lines.append(f".names {a} {y}")
            lines.append("1 1")
            lines.append("")
            continue
        
        if cell.op == CellOp.NOT:
            a = pin_net_name(cell.inputs["A"])
            y = pin_net_name(cell.output)
            lines.append(f".names {a} {y}")
            lines.append("0 1")
            lines.append("")
            continue
        
        if cell.op == CellOp.AND:
            a = pin_net_name(cell.inputs["A"])
            b = pin_net_name(cell.inputs["B"])
            y = pin_net_name(cell.output)
            lines.append(f".names {a} {b} {y}")
            lines.append("11 1")
            lines.append("")
            continue
        
        if cell.op == CellOp.OR:
            a = pin_net_name(cell.inputs["A"])
            b = pin_net_name(cell.inputs["B"])
            y = pin_net_name(cell.output)
            lines.append(f".names {a} {b} {y}")
            lines.append("1- 1")
            lines.append("-1 1")
            lines.append("")
            continue
        
        if cell.op == CellOp.XOR:
            a = pin_net_name(cell.inputs["A"])
            b = pin_net_name(cell.inputs["B"])
            y = pin_net_name(cell.output)
            lines.append(f".names {a} {b} {y}")
            lines.append("10 1")
            lines.append("01 1")
            lines.append("")
            continue
        
        if cell.op == CellOp.MUX:
            s = pin_net_name(cell.inputs["S"])
            a = pin_net_name(cell.inputs["A"])
            b = pin_net_name(cell.inputs["B"])
            y = pin_net_name(cell.output)
            lines.append(f"# MUX: S ? B : A")
            lines.append(f".names {s} {a} {b} {y}")
            lines.append("01- 1")  # sel=0, a=1
            lines.append("1-1 1")  # sel=1, b=1
            lines.append("")
            continue
        
        dff_ops = {CellOp.DFF, CellOp.DFFR, CellOp.DFFRE, CellOp.DFFS}
        if cell.op in dff_ops:
            d = pin_net_name(cell.inputs["D"])
            q = pin_net_name(cell.output)
            lines.append(f".latch {d} {q} re clk 0")
            lines.append("")
            continue
        
        # Generic fallback: emit as subcircuit
        ins = " ".join(f"{n}={pin_net_name(p)}" for n, p in cell.inputs.items())
        outs = " ".join(f"{n}={pin_net_name(p)}" for n, p in cell.outputs.items())
        lines.append(f".subckt {cell.op.name} {ins} {outs}")
        lines.append("")
    
    lines.append(".end")
    return "\n".join(lines)
