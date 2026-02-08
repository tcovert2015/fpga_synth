# FPGA Synthesis Tool

A complete FPGA synthesis toolchain built from scratch in Python, transforming Verilog HDL into synthesizable netlists.

[![Tests](https://img.shields.io/badge/tests-149%20passing-brightgreen)]()
[![Verilog](https://img.shields.io/badge/Verilog-2005-blue)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)]()

---

## 🚀 Quick Start

```bash
# Parse Verilog to AST
./parse_verilog.py examples/simple_and.v

# View AST as JSON
python3 -c "
from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_json import ast_to_json

ast = parse_verilog(open('examples/simple_and.v').read())
print(ast_to_json(ast, indent=2))
"

# Elaborate to netlist
python3 -c "
from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.elaborator import elaborate

verilog = open('examples/simple_and.v').read()
ast = parse_verilog(verilog)
netlist = elaborate(ast)
print(f'Netlist: {len(netlist.cells)} cells, {len(netlist.nets)} nets')
"
```

---

## ✨ Features

### Complete Verilog-2005 Parser
- ✅ **All synthesizable constructs**: modules, ports, parameters
- ✅ **Declarations**: wire, reg, integer, real, time, event
- ✅ **Operators**: arithmetic, bitwise, logical, comparison, shifts, ternary
- ✅ **Statements**: if/else, case/casex/casez, for/while loops
- ✅ **Procedural blocks**: always, initial, tasks, functions
- ✅ **Generate constructs**: generate if/for/case
- ✅ **Arrays**: unpacked arrays, multi-dimensional memories
- ✅ **Advanced features**: attributes, hierarchical names, part-select

### Excellent Error Messages
```verilog
module test;
    wire a
    wire b;
endmodule
```
```
Parse error at L3:5: Expected SEMICOLON (got WIRE = 'wire')

     3 |     wire b;
       |     ^

Suggestion: Add a semicolon ';' to end the statement
```

### AST Manipulation
- **Visitor Pattern**: Traverse and transform AST with ease
- **JSON Export**: Serialize AST for debugging and tool integration
- **Code Generation**: Pretty-print AST back to Verilog
- **Statistics**: Analyze AST structure and complexity

### Elaboration (AST → Netlist)
- Converts AST tree to synthesizable netlist DAG
- Resolves parameters and generates blocks
- Creates cells for all operations (AND, ADD, MUX, etc.)
- Builds hypergraph with cells, nets, and pins

---

## 📊 Pipeline Overview

```
Verilog Source
    ↓
[Lexer] → Tokens
    ↓
[Parser] → Abstract Syntax Tree (AST)
    ↓
[Elaborator] → Netlist (DAG of cells)
    ↓
[Optimizer] → Optimized netlist (TODO)
    ↓
[Technology Mapper] → LUT network (TODO)
    ↓
[Placer] → Placed design (TODO)
    ↓
[Router] → Routed design (TODO)
    ↓
[Bitstream Generator] → FPGA configuration (TODO)
```

**Status**: ✅ Frontend complete (Lexer, Parser, AST, Elaborator)

---

## 📚 Documentation

### Parser API

```python
from fpga_synth.hdl_parser.parser import parse_verilog

# Parse Verilog source
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
print(f"Module: {ast.modules[0].name}")
print(f"Ports: {len(ast.modules[0].ports)}")
```

### AST Visitor

```python
from fpga_synth.hdl_parser.ast_visitor import ASTVisitor

class ModuleFinder(ASTVisitor):
    def __init__(self):
        self.modules = []

    def visit_Module(self, node):
        self.modules.append(node.name)
        return self.generic_visit(node)

visitor = ModuleFinder()
visitor.visit(ast)
print(f"Found modules: {visitor.modules}")
```

### JSON Export

```python
from fpga_synth.hdl_parser.ast_json import ast_to_json, ast_to_json_file

# Export to JSON string
json_str = ast_to_json(ast, indent=2)

# Save to file
ast_to_json_file(ast, "design.json")
```

### Code Generation

```python
from fpga_synth.hdl_parser.codegen import generate_verilog

# Generate Verilog from AST
verilog_output = generate_verilog(ast)
print(verilog_output)
```

### Elaboration

```python
from fpga_synth.hdl_parser.elaborator import elaborate

# Elaborate AST to netlist
netlist = elaborate(ast)

print(f"Cells: {len(netlist.cells)}")
print(f"Nets: {len(netlist.nets)}")

# Inspect cells
for cell in netlist.cells.values():
    print(f"  {cell.name}: {cell.op.name}")
```

---

## 🧪 Testing

```bash
# Run all tests (149 tests)
for test in tests/parser/*.py tests/test_elaborator.py; do
    python3 "$test"
done

# Run specific test suite
python3 tests/parser/test_integration.py
python3 tests/parser/test_ast_visitor.py
python3 tests/test_elaborator.py
```

### Test Coverage
- **Parser**: 136 tests across 15 test files
- **Elaborator**: 13 tests
- **Integration**: Real-world designs (UART, FIFO, counter, mux)
- **Edge Cases**: Empty constructs, max sizes, error messages

---

## 📁 Project Structure

```
fpga_synth/
├── hdl_parser/           # Frontend (Lexer, Parser, AST)
│   ├── lexer.py         # Tokenization
│   ├── tokens.py        # Token definitions
│   ├── parser.py        # Recursive descent parser
│   ├── ast_nodes.py     # AST node definitions
│   ├── ast_visitor.py   # Visitor pattern for AST
│   ├── ast_json.py      # JSON serialization
│   ├── codegen.py       # Verilog code generation
│   └── elaborator.py    # AST → Netlist conversion
├── ir/                   # Intermediate representations
│   ├── netlist.py       # Netlist graph (DAG)
│   └── types.py         # Core types (CellOp, BitWidth, etc.)
├── backend/              # Backend (TODO)
├── tests/                # Test suite
│   ├── parser/          # Parser tests (136 tests)
│   ├── integration/     # Integration test designs
│   └── test_elaborator.py  # Elaboration tests
├── examples/             # Example Verilog designs
├── parse_verilog.py     # CLI tool
└── README.md            # This file
```

---

## 🎯 Supported Verilog Constructs

### ✅ Fully Supported
- Module declarations with parameters
- Port declarations (input, output, inout)
- Wire, reg, integer, real, time, event types
- Packed and unpacked arrays
- All operators (arithmetic, bitwise, logical, comparison, shift)
- Continuous assignments (assign)
- Always blocks (@(posedge clk), @(*))
- Initial blocks
- If/else statements
- Case/casex/casez statements
- For/while/repeat/forever loops
- Tasks and functions
- Generate blocks (if, for, case)
- Module instantiation
- System tasks ($display, $finish, etc.)
- Attributes (* key = value *)
- Hierarchical names (top.sub.signal)
- Indexed part-select ([base +: width])

### ⏳ Partial Support
- Always blocks: Elaborated for combinational only (sequential TODO)
- Memories: Declarations parsed, inference TODO

### ❌ Not Supported (Non-synthesizable)
- Delays and timing (#10, @(#10))
- Fork/join (parallel blocks)
- User-defined primitives (UDP)

---

## 🌟 Example Designs

See `examples/` directory for complete examples:

- **simple_and.v**: Basic AND gate
- **adder.v**: 8-bit adder
- **counter.v**: Counter with reset and enable
- **mux.v**: Parametric multiplexer
- **alu.v**: Simple ALU
- **uart_tx.v**: UART transmitter (production-quality)

---

## 🔧 Development

### Adding New Features

1. **Lexer**: Add tokens to `hdl_parser/tokens.py`
2. **Parser**: Add parsing logic to `hdl_parser/parser.py`
3. **AST**: Add node types to `hdl_parser/ast_nodes.py`
4. **Tests**: Create tests in `tests/parser/`
5. **Elaborator**: Add elaboration logic to `hdl_parser/elaborator.py`

### Code Style
- Type hints for all functions
- Docstrings for public APIs
- Descriptive variable names
- Keep functions focused and small

---

## 📈 Roadmap

### Frontend (Complete ✅)
- [x] Lexer and tokenization
- [x] Recursive descent parser
- [x] Complete AST representation
- [x] Error handling and suggestions
- [x] Visitor pattern
- [x] JSON serialization
- [x] Code generation
- [x] Basic elaboration

### Optimization (TODO)
- [ ] Constant propagation
- [ ] Dead code elimination
- [ ] Common subexpression elimination
- [ ] AIG (And-Inverter Graph) conversion
- [ ] AIG rewriting and refactoring

### Backend (TODO)
- [ ] Technology mapping (LUT mapping)
- [ ] Packing (cluster formation)
- [ ] Placement (simulated annealing)
- [ ] Routing (pathfinding algorithms)
- [ ] Bitstream generation

---

## 🤝 Contributing

Contributions welcome! Areas of interest:
- Sequential logic elaboration (flip-flops, FSMs)
- Memory inference
- Logic optimization algorithms
- Technology mapping
- Placement and routing

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

Built following synthesis principles from:
- Yosys synthesis framework
- ABC logic optimization tool
- VPR place and route tool
- IEEE 1364-2005 Verilog standard

---

## 📞 Contact

For questions, issues, or contributions, please open an issue on GitHub.

**Project Status**: Alpha - Frontend complete, backend in development

**Test Suite**: 149 tests passing ✅
