# Verilog Parser Examples

This directory contains example Verilog files demonstrating the supported language subset and a tool to parse them.

## Example Files

### counter.v
An 8-bit counter with synchronous reset and enable.

**Demonstrates:**
- Parameterized modules
- Sequential logic (`always @(posedge clk)`)
- If/else statements
- Blocking and non-blocking assignments

### simple_alu.v
A simple arithmetic logic unit with 8 operations.

**Demonstrates:**
- Combinational logic (`always @(*)`)
- Case statements
- Continuous assignments (`assign`)
- Arithmetic, bitwise, and shift operations

### mux.v
A 4-to-1 multiplexer using ternary operators.

**Demonstrates:**
- Ternary operators (nested)
- Bit-select notation
- Pure combinational logic

## Using the Parser

### Basic Usage

Parse a Verilog file and display summary:
```bash
python3 parse_verilog.py examples/counter.v
```

### Verbose Mode

Show detailed AST information:
```bash
python3 parse_verilog.py examples/simple_alu.v --verbose
```

### Example Output

```
============================================================
Parsing: counter.v
============================================================

Module: counter
  Location: Line 4, Col 1

  Parameters (1):
    - WIDTH = 8

  Ports (5):
    - input  clk
    - input  rst
    - input  enable
    - output [WIDTH-1:0] count reg
    - output overflow reg

  Body Items (1):
    Always Blocks: 1
      1. always @(posedge clk) (Line 14)
         Statements: 1

============================================================
✓ Parsing successful!
============================================================
```

## Supported Verilog Features

The parser currently supports a synthesizable subset of Verilog:

- **Module declarations** with parameters and ports
- **Data types**: `wire`, `reg`, `integer`
- **Port directions**: `input`, `output`, `inout`
- **Assignments**:
  - Continuous: `assign`
  - Blocking: `=`
  - Non-blocking: `<=`
- **Always blocks**:
  - `always @(posedge clk)`
  - `always @(*)`
- **Control flow**:
  - `if`/`else`
  - `case`/`casex`/`casez`
  - `for` loops (in generate blocks)
- **Operators**:
  - Arithmetic: `+`, `-`, `*`, `/`, `%`
  - Bitwise: `&`, `|`, `^`, `~`
  - Logical: `&&`, `||`, `!`
  - Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
  - Shift: `<<`, `>>`, `>>>`
  - Ternary: `? :`
- **Bit manipulation**:
  - Concatenation: `{a, b}`
  - Replication: `{4{a}}`
  - Bit-select: `signal[3]`
  - Part-select: `signal[7:0]`
- **Number formats**:
  - Decimal: `42`
  - Sized hex: `8'hFF`
  - Sized binary: `4'b1010`
  - Sized decimal: `3'd7`

## Next Steps

After parsing, the AST can be:
1. Elaborated into a netlist (DAG)
2. Optimized using graph transformations
3. Technology mapped to FPGA primitives (LUTs, FFs)
4. Exported to BLIF format for verification

See the main project README for the full synthesis pipeline.
