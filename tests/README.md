# Test Suite

This directory contains all tests for the FPGA synthesis tool.

## Directory Structure

```
tests/
├── test_netlist_ir.py       # Tests for netlist IR and basic parser
└── parser/                   # Parser-specific tests (to be added)
    ├── lexer/               # Lexer tests
    ├── expressions/         # Expression parsing tests
    ├── statements/          # Statement parsing tests
    ├── declarations/        # Declaration parsing tests
    ├── modules/             # Module-level tests
    ├── edge_cases/          # Edge case tests
    └── error_cases/         # Error handling tests
```

## Running Tests

### Run all tests
```bash
python3 tests/test_netlist_ir.py
```

### Run with pytest (if available)
```bash
pytest tests/ -v
```

### Run specific test file
```bash
python3 tests/test_netlist_ir.py
```

## Test Coverage

Current test coverage:
- ✅ Lexer: Basic tokens, numbers, operators, comments
- ✅ Number resolution: All formats (decimal, hex, binary)
- ✅ Parser: Modules, ports, assigns, always blocks, case statements
- ✅ Netlist IR: Cell/net creation, graph operations, topological sort
- ✅ AST: Expression and statement nodes

## Adding New Tests

1. Create test file in appropriate directory
2. Follow naming convention: `test_*.py`
3. Use descriptive test function names: `test_<feature>_<scenario>`
4. Include docstrings explaining what is being tested
5. Run tests to ensure they pass

## Test Philosophy

- **Test-driven development**: Write tests before or alongside implementation
- **Comprehensive coverage**: Aim for >95% code coverage
- **Real-world examples**: Include tests from actual Verilog designs
- **Edge cases**: Test boundary conditions and error cases
- **Regression prevention**: Add tests for every bug fix

## See Also

- See `TODO.md` Phase 3 for detailed test plan
- See `examples/` for sample Verilog files used in testing
