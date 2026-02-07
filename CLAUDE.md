# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an FPGA synthesis tool being built from scratch. It transforms hardware description language (Verilog subset) into FPGA configuration through a series of graph transformations. The tool implements a complete compiler pipeline where the "instruction set" is configurable FPGA logic blocks.

## Commands

### Running Tests

```bash
# Run all tests in test_chunk1.py
python test_chunk1.py

# Run with pytest (if available)
python -m pytest test_chunk1.py -v
```

### Testing Individual Components

```bash
# Test lexer directly
python -c "from lexer import lex; print(lex('module foo; endmodule'))"

# Test parser
python -c "from parser import parse_verilog; print(parse_verilog('module foo; endmodule'))"
```

## Architecture

### Pipeline Overview

The synthesis pipeline is a series of graph-to-graph transformations:

```
Verilog Source → [Lexer] → Tokens
              → [Parser] → AST
              → [Elaboration] → Netlist DAG
              → [Optimization] → Optimized Netlist
              → [Tech Mapping] → LUT Network
              → [Packing] → Clustered Netlist
              → [Placement] → Placed Design
              → [Routing] → Routed Design
              → [Bitstream] → FPGA Configuration
```

Currently implemented: Lexer, Parser, AST, and core Netlist IR (first three stages).

### Core Data Structures

**AST (Abstract Syntax Tree)**
- Location: `ast_nodes.py`
- A tree representation that mirrors Verilog source structure
- Root is `SourceFile` containing one or more `Module` nodes
- Expression nodes: `NumberLiteral`, `Identifier`, `BinaryOp`, `TernaryOp`, `Concat`, etc.
- Statement nodes: `BlockingAssign`, `NonBlockingAssign`, `IfStatement`, `CaseStatement`, `AlwaysBlock`
- Each node has `line` and `col` for error reporting

**Netlist (DAG Intermediate Representation)**
- Location: `netlist.py`
- The central data structure used throughout synthesis
- A directed hypergraph where:
  - **Cells** are nodes representing logic operations (`CellOp` enum: AND, OR, XOR, ADD, MUX, DFF, etc.)
  - **Nets** are hyperedges connecting one driver pin to multiple sink pins
  - **Pins** are connection points on cells
- Graph properties maintained:
  - Topological ordering (via `topological_sort()`)
  - Fanin/fanout traversal (via `fanin_cells()`, `fanout_cells()`)
  - Fanin/fanout cones (via `fanin_cone()`, `fanout_cone()`)
  - Dead logic detection (via `find_dead_cells()`, `remove_dead_logic()`)
  - Combinational loop detection (via `detect_combinational_loops()` using Tarjan's SCC algorithm)

### Graph Theory Foundation

Every transformation is fundamentally a graph operation:

- **Topological Sort**: Used for levelization, dataflow analysis, static timing analysis
- **Cone Extraction**: Transitive fanin/fanout for cut enumeration and optimization
- **Dead Logic Removal**: Reverse reachability from primary outputs (BFS/DFS)
- **Combinational Loop Detection**: Strongly Connected Components (Tarjan's algorithm)
- Sequential elements (DFF*) break combinational cycles at register boundaries

### Module Organization

```
fpga_synth/
├── hdl_parser/
│   ├── tokens.py      - Token types and keyword lookup table
│   ├── lexer.py       - Hand-written lexer for Verilog subset
│   ├── parser.py      - Recursive-descent parser producing AST
│   └── ast_nodes.py   - AST node definitions (tree structure)
├── ir/
│   ├── types.py       - Core types: CellOp, BitWidth, PortDir, PortSpec
│   └── netlist.py     - Netlist DAG: Cell, Net, Pin, graph operations
├── backend/
│   └── blif_writer.py - Export netlist to BLIF for verification
└── test_chunk1.py     - Test suite for lexer, parser, AST, and netlist
```

### Import Paths

The codebase uses absolute imports from `fpga_synth` package root:

```python
from fpga_synth.hdl_parser.lexer import lex
from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.ir.netlist import Netlist, Cell, Net
from fpga_synth.ir.types import CellOp, BitWidth
```

Test files add the parent directory to `sys.path` to enable these imports.

### Supported Verilog Subset

**Module-level constructs:**
- Module declarations with parameters and ports
- Port declarations (ANSI-style): `input [7:0] data`
- Wire/reg/integer declarations
- Parameter/localparam declarations
- Continuous assignments: `assign y = a + b;`
- Always blocks: `always @(posedge clk)`, `always @(*)`
- Module instantiation with named ports
- Generate blocks (for-generate)

**Expressions:**
- Number literals: decimal (42), sized hex/bin/oct/dec (8'hFF, 4'b1010, 3'd7)
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Bitwise: `&`, `|`, `^`, `~`
- Logical: `&&`, `||`, `!`
- Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Shifts: `<<`, `>>`, `>>>`
- Ternary: `cond ? a : b`
- Concatenation: `{a, b}`
- Replication: `{4{a}}`
- Bit-select/part-select: `sig[7]`, `sig[7:0]`

**Statements:**
- Blocking assignment: `a = b;`
- Non-blocking assignment: `a <= b;`
- if/else conditionals
- case/casex/casez statements
- begin/end blocks
- for loops (in generate blocks)

### Key Implementation Details

**Lexer (`lexer.py`):**
- Hand-written, not generated
- Handles Verilog number formats: `8'hFF`, `4'b1010`, `3'd7`, plain decimals
- Strips comments (`//` and `/* */`) and compiler directives (`` `define``, `` `include``, etc.)
- No preprocessing/macro expansion yet

**Parser (`parser.py`):**
- Recursive descent parser
- Operator precedence climbing for expressions
- Number resolution in `Parser.resolve_number()`: returns `(value, width, signed)`
- Produces complete AST with line/column information for error reporting

**Netlist (`netlist.py`):**
- ID generation via `itertools.count()` - call `reset_ids()` in tests for deterministic IDs
- Cells have attributes dict for extra data (constant values, slice ranges, etc.)
- Sequential elements (DFF*) are treated specially in topological sort to break cycles
- Graph traversals are DFS/BFS-based

**BLIF Writer (`blif_writer.py`):**
- Exports netlists to Berkeley Logic Interchange Format
- Used for verification against Yosys/ABC
- Supports common cell types: AND, OR, XOR, NOT, MUX, BUF, CONST, DFF*
- Falls back to `.subckt` for unsupported cells

### Testing Philosophy

Tests in `test_chunk1.py` cover:
- Lexer: tokenization, number formats, operators, comments
- Number resolution: unsized, hex, binary, decimal literals
- Parser: modules, ports, assigns, always blocks, case statements, expressions
- Netlist: cell/net creation, connections, topological sort, dead logic removal, fanin cones, combinational loop detection

Run tests before and after changes to verify correctness.

## References

See `fpga_synthesis_tool_guide.md` for comprehensive theoretical background on:
- Graph algorithms used in synthesis (cuts, cones, max-flow, SCC, etc.)
- Technology mapping algorithms (FlowMap, CutMap)
- Placement algorithms (simulated annealing, analytical placement)
- Routing algorithms (PathFinder, A*)
- Static timing analysis (longest-path on timing DAG)
- Logic optimization techniques (AIG rewriting, retiming, etc.)
