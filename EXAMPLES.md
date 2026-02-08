# Usage Examples

Practical examples showing how to use the FPGA synthesis tool for various tasks.

---

## Table of Contents

1. [Basic Parsing](#1-basic-parsing)
2. [Error Checking](#2-error-checking)
3. [AST Analysis](#3-ast-analysis)
4. [Code Transformation](#4-code-transformation)
5. [Elaboration](#5-elaboration)
6. [Tool Integration](#6-tool-integration)

---

## 1. Basic Parsing

### 1.1 Parse from String

```python
from fpga_synth.hdl_parser.parser import parse_verilog

verilog = """
module adder(
    input [7:0] a,
    input [7:0] b,
    output [7:0] sum
);
    assign sum = a + b;
endmodule
"""

ast = parse_verilog(verilog)
print(f"Parsed module: {ast.modules[0].name}")
```

---

### 1.2 Parse from File

```python
with open('examples/counter.v', 'r') as f:
    verilog = f.read()

ast = parse_verilog(verilog, filename='counter.v')

# Explore the AST
module = ast.modules[0]
print(f"Module: {module.name}")
print(f"Parameters: {len(module.params)}")
print(f"Ports: {len(module.ports)}")
print(f"Body items: {len(module.body)}")
```

---

### 1.3 Parse Multiple Modules

```python
verilog = """
module top(input a, output b);
    sub u1(a, b);
endmodule

module sub(input x, output y);
    assign y = ~x;
endmodule
"""

ast = parse_verilog(verilog)
for module in ast.modules:
    print(f"Module: {module.name}")
```

---

## 2. Error Checking

### 2.1 Validate Verilog Syntax

```python
def validate_verilog(code):
    """Check if Verilog code is syntactically valid."""
    try:
        ast = parse_verilog(code)
        return True, "Valid"
    except Exception as e:
        return False, str(e)

# Test valid code
valid, msg = validate_verilog("module test; endmodule")
print(f"Valid: {valid}")

# Test invalid code
valid, msg = validate_verilog("module test wire a; endmodule")
print(f"Valid: {valid}")
print(f"Error: {msg}")
```

---

### 2.2 Batch File Validation

```python
import glob

def validate_directory(pattern):
    """Validate all Verilog files matching pattern."""
    results = []
    for filepath in glob.glob(pattern):
        try:
            with open(filepath, 'r') as f:
                ast = parse_verilog(f.read(), filepath)
            results.append((filepath, True, None))
        except Exception as e:
            results.append((filepath, False, str(e)))

    return results

# Validate all .v files
results = validate_directory('examples/*.v')
for filepath, valid, error in results:
    status = "✓" if valid else "✗"
    print(f"{status} {filepath}")
    if error:
        print(f"  Error: {error}")
```

---

## 3. AST Analysis

### 3.1 Count Module Complexity

```python
from fpga_synth.hdl_parser.ast_visitor import StatisticsVisitor

def analyze_complexity(verilog):
    """Analyze design complexity."""
    ast = parse_verilog(verilog)

    stats = StatisticsVisitor()
    stats.visit(ast)

    complexity = {
        'total_nodes': stats.total_nodes,
        'always_blocks': stats.node_counts.get('AlwaysBlock', 0),
        'assigns': stats.node_counts.get('ContinuousAssign', 0),
        'expressions': (
            stats.node_counts.get('BinaryOp', 0) +
            stats.node_counts.get('UnaryOp', 0) +
            stats.node_counts.get('TernaryOp', 0)
        )
    }

    return complexity

# Analyze a design
with open('examples/alu.v', 'r') as f:
    complexity = analyze_complexity(f.read())

print(f"Complexity metrics:")
for metric, value in complexity.items():
    print(f"  {metric}: {value}")
```

---

### 3.2 Find All Module Instantiations

```python
from fpga_synth.hdl_parser.ast_visitor import ASTVisitor
from fpga_synth.hdl_parser.ast_nodes import ModuleInstance

class InstanceFinder(ASTVisitor):
    def __init__(self):
        self.instances = []

    def visit_ModuleInstance(self, node):
        self.instances.append({
            'module': node.module_name,
            'instance': node.instance_name,
            'params': len(node.params),
            'ports': len(node.ports)
        })
        return self.generic_visit(node)

# Find all instances
ast = parse_verilog("...")
finder = InstanceFinder()
finder.visit(ast)

for inst in finder.instances:
    print(f"Instance {inst['instance']} of {inst['module']}")
```

---

### 3.3 Extract Signal Names

```python
from fpga_synth.hdl_parser.ast_visitor import IdentifierCollector
from fpga_synth.hdl_parser.ast_nodes import NetDecl, PortDecl

def extract_signals(verilog):
    """Extract all signal names from a module."""
    ast = parse_verilog(verilog)
    module = ast.modules[0]

    signals = {
        'inputs': [],
        'outputs': [],
        'wires': [],
        'regs': []
    }

    # Extract from ports
    for port in module.ports:
        if port.direction == 'input':
            signals['inputs'].append(port.name)
        elif port.direction == 'output':
            signals['outputs'].append(port.name)

    # Extract from body
    for item in module.body:
        if isinstance(item, NetDecl):
            if item.net_type == 'wire':
                signals['wires'].append(item.name)
            elif item.net_type == 'reg':
                signals['regs'].append(item.name)

    return signals

signals = extract_signals("...")
print("Input ports:", signals['inputs'])
print("Output ports:", signals['outputs'])
print("Internal wires:", signals['wires'])
print("Registers:", signals['regs'])
```

---

## 4. Code Transformation

### 4.1 Rename All Signals

```python
from fpga_synth.hdl_parser.ast_visitor import ASTTransformer
from fpga_synth.hdl_parser.ast_nodes import Identifier, NetDecl, PortDecl
from fpga_synth.hdl_parser.codegen import generate_verilog

class SignalRenamer(ASTTransformer):
    def __init__(self, mapping):
        self.mapping = mapping  # old_name → new_name

    def visit_Identifier(self, node):
        if node.name in self.mapping:
            node.name = self.mapping[node.name]
        return node

    def visit_NetDecl(self, node):
        if node.name in self.mapping:
            node.name = self.mapping[node.name]
        return self.generic_visit(node)

    def visit_PortDecl(self, node):
        if node.name in self.mapping:
            node.name = self.mapping[node.name]
        return self.generic_visit(node)

# Rename signals
ast = parse_verilog("module test; wire a; endmodule")

renamer = SignalRenamer({'a': 'data_signal'})
new_ast = renamer.visit(ast)

# Generate new Verilog
print(generate_verilog(new_ast))
```

---

### 4.2 Insert Debug Statements

```python
from fpga_synth.hdl_parser.ast_nodes import SystemTaskCall, StringLiteral

class DebugInserter(ASTTransformer):
    def visit_AlwaysBlock(self, node):
        # Insert $display at start of always block
        debug = SystemTaskCall(
            name="$display",
            args=[StringLiteral(value=f"Always block executing")]
        )
        node.body.insert(0, debug)
        return self.generic_visit(node)

ast = parse_verilog("...")
debugger = DebugInserter()
new_ast = debugger.visit(ast)
```

---

### 4.3 Constant Folding

```python
from fpga_synth.hdl_parser.ast_nodes import BinaryOp, NumberLiteral

class ConstantFolder(ASTTransformer):
    def visit_BinaryOp(self, node):
        # First, fold children
        node = self.generic_visit(node)

        # Check if both operands are constants
        if isinstance(node.left, NumberLiteral) and isinstance(node.right, NumberLiteral):
            # Evaluate
            ops = {
                '+': lambda a, b: a + b,
                '-': lambda a, b: a - b,
                '*': lambda a, b: a * b,
                '&': lambda a, b: a & b,
                '|': lambda a, b: a | b,
                '^': lambda a, b: a ^ b,
            }

            if node.op in ops:
                result = ops[node.op](node.left.value, node.right.value)
                return NumberLiteral(
                    raw=str(result),
                    value=result,
                    width=max(node.left.width, node.right.width)
                )

        return node
```

---

## 5. Elaboration

### 5.1 Generate Netlist

```python
from fpga_synth.hdl_parser.elaborator import elaborate

verilog = """
module full_adder(
    input a, b, cin,
    output sum, cout
);
    assign sum = a ^ b ^ cin;
    assign cout = (a & b) | (cin & (a ^ b));
endmodule
"""

ast = parse_verilog(verilog)
netlist = elaborate(ast)

print(f"Design: {netlist.name}")
print(f"Primary inputs: {len(netlist.inputs)}")
print(f"Primary outputs: {len(netlist.outputs)}")
print(f"Total cells: {len(netlist.cells)}")
print(f"Total nets: {len(netlist.nets)}")

# Analyze cells by type
from collections import Counter
cell_types = Counter(cell.op.name for cell in netlist.cells.values())
print("\nCell breakdown:")
for cell_type, count in cell_types.most_common():
    print(f"  {cell_type}: {count}")
```

---

### 5.2 Visualize Netlist Graph

```python
def print_netlist_graph(netlist):
    """Print netlist as a simple text graph."""
    print("Netlist Graph:")
    print("=" * 50)

    # Show primary inputs
    print("\nPrimary Inputs:")
    for name, cell in netlist.inputs.items():
        print(f"  {name} → {cell.output.net.name}")

    # Show logic cells
    print("\nLogic Cells:")
    for cell in netlist.cells.values():
        if cell.op.name not in ('MODULE_INPUT', 'MODULE_OUTPUT'):
            inputs = [f"{pin.net.name}" for pin in cell.inputs.values() if pin.net]
            output = cell.output.net.name if hasattr(cell, 'output') else "?"
            print(f"  {cell.name} ({cell.op.name})")
            print(f"    inputs: {inputs}")
            print(f"    output: {output}")

    # Show primary outputs
    print("\nPrimary Outputs:")
    for name, cell in netlist.outputs.items():
        in_pin = list(cell.inputs.values())[0]
        driver = in_pin.net.name if in_pin.net else "?"
        print(f"  {driver} → {name}")

netlist = elaborate(parse_verilog("..."))
print_netlist_graph(netlist)
```

---

### 5.3 Extract Critical Paths

```python
def find_logic_depth(netlist):
    """Calculate logic depth for each cell."""
    depth = {}

    # Initialize: primary inputs have depth 0
    for cell in netlist.inputs.values():
        depth[cell] = 0

    # Topological traversal
    def visit(cell, memo=None):
        if memo is None:
            memo = {}

        if cell in memo:
            return memo[cell]

        if cell in netlist.inputs.values():
            memo[cell] = 0
            return 0

        # Get max depth of predecessors
        max_input_depth = 0
        for in_pin in cell.inputs.values():
            if in_pin.net and in_pin.net.driver:
                driver_cell = in_pin.net.driver.cell
                if driver_cell:
                    d = visit(driver_cell, memo)
                    max_input_depth = max(max_input_depth, d)

        memo[cell] = max_input_depth + 1
        return memo[cell]

    # Visit all cells
    for cell in netlist.cells.values():
        visit(cell, depth)

    return depth

netlist = elaborate(parse_verilog("..."))
depths = find_logic_depth(netlist)

print("Logic depths:")
for cell, d in sorted(depths.items(), key=lambda x: x[1], reverse=True):
    print(f"  {cell.name}: depth {d}")
```

---

### 5.4 Memory Inference

```python
from fpga_synth.hdl_parser.elaborator import elaborate
from fpga_synth.ir.types import CellOp

verilog = """
module dual_port_ram(
    input clk,
    input we,
    input [7:0] waddr, raddr,
    input [7:0] din,
    output [7:0] dout
);
    reg [7:0] mem [0:255];

    always @(posedge clk) begin
        if (we)
            mem[waddr] <= din;
    end

    assign dout = mem[raddr];
endmodule
"""

ast = parse_verilog(verilog)
netlist = elaborate(ast)

# Find memory cells
memrd_cells = [c for c in netlist.cells.values() if c.op == CellOp.MEMRD]
memwr_cells = [c for c in netlist.cells.values() if c.op == CellOp.MEMWR]

print(f"Memory reads: {len(memrd_cells)}")
print(f"Memory writes: {len(memwr_cells)}")

for cell in memwr_cells:
    print(f"\nMemory write: {cell.name}")
    print(f"  Memory: {cell.attributes['memory']}")
    print(f"  Depth: {cell.attributes['depth']}")
    print(f"  Pins: {list(cell.inputs.keys())}")
```

**Output:**
```
Memory reads: 1
Memory writes: 1

Memory write: memwr_mem_6
  Memory: mem
  Depth: 256
  Pins: ['CLK', 'ADDR', 'DATA', 'EN']
```

---

## 6. Tool Integration

### 6.1 Export to JSON for External Tools

```python
from fpga_synth.hdl_parser.ast_json import ast_to_json_file

# Parse and export
ast = parse_verilog(open('design.v').read())
ast_to_json_file(ast, 'design.json', indent=2)

# Now external tools can read design.json
print("AST exported to design.json")
```

---

### 6.2 Generate Documentation

```python
def generate_module_doc(verilog):
    """Generate markdown documentation for a module."""
    ast = parse_verilog(verilog)
    module = ast.modules[0]

    doc = f"# Module: {module.name}\n\n"

    # Parameters
    if module.params:
        doc += "## Parameters\n\n"
        doc += "| Name | Default |\n"
        doc += "|------|----------|\n"
        for param in module.params:
            default = param.value.raw if param.value else "N/A"
            doc += f"| {param.name} | {default} |\n"
        doc += "\n"

    # Ports
    if module.ports:
        doc += "## Ports\n\n"
        doc += "| Name | Direction | Width |\n"
        doc += "|------|-----------|-------|\n"
        for port in module.ports:
            width = f"[{port.range.msb.value}:{port.range.lsb.value}]" if port.range else "1"
            doc += f"| {port.name} | {port.direction} | {width} |\n"
        doc += "\n"

    return doc

doc = generate_module_doc(open('examples/adder.v').read())
print(doc)
```

---

### 6.3 Convert Between Formats

```python
def verilog_to_json(input_file, output_file):
    """Convert Verilog to JSON."""
    with open(input_file, 'r') as f:
        ast = parse_verilog(f.read(), input_file)

    ast_to_json_file(ast, output_file)
    print(f"Converted {input_file} → {output_file}")

def json_to_verilog(input_file, output_file):
    """Convert JSON to Verilog."""
    ast = ast_from_json_file(input_file)
    verilog = generate_verilog(ast)

    with open(output_file, 'w') as f:
        f.write(verilog)

    print(f"Converted {input_file} → {output_file}")

# Round-trip conversion
verilog_to_json('design.v', 'design.json')
json_to_verilog('design.json', 'design_out.v')
```

---

### 6.4 Create a Linter

```python
class VerilogLinter(ASTVisitor):
    def __init__(self):
        self.warnings = []

    def visit_Identifier(self, node):
        # Check naming conventions
        if not node.name.islower() and not node.name.isupper():
            self.warnings.append(
                f"Mixed case identifier: {node.name}"
            )
        return self.generic_visit(node)

    def visit_AlwaysBlock(self, node):
        # Warn about combinational @(*) with non-blocking
        if node.is_star:
            for stmt in node.body:
                if isinstance(stmt, NonBlockingAssign):
                    self.warnings.append(
                        "Non-blocking assign in combinational block"
                    )
        return self.generic_visit(node)

# Run linter
ast = parse_verilog("...")
linter = VerilogLinter()
linter.visit(ast)

print(f"Linter found {len(linter.warnings)} warnings:")
for warning in linter.warnings:
    print(f"  ⚠ {warning}")
```

---

## Summary

These examples demonstrate:

✅ **Parsing**: From strings, files, multiple modules
✅ **Validation**: Syntax checking, batch validation
✅ **Analysis**: Complexity metrics, signal extraction, statistics
✅ **Transformation**: Renaming, debug insertion, optimization
✅ **Elaboration**: Netlist generation, graph analysis
✅ **Integration**: JSON export, documentation, linting

**The tool provides a complete API for Verilog analysis and transformation!**
