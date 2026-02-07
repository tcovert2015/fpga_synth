# TODO: Complete Verilog/SystemVerilog Parser to AST

This document tracks the work needed to create a complete, fully-tested parser that outputs AST files.

**Ultimate Goal:** Full compliance with the **SystemVerilog IEEE 1800** specification (latest version available in this repository).

**Phased Approach:**
1. Complete Verilog-2005 (IEEE 1364-2005) synthesizable subset
2. Add SystemVerilog synthesizable features
3. Add SystemVerilog verification features (classes, assertions, etc.)
4. Full SystemVerilog spec compliance

## Current Status

✅ **Completed:**
- Basic lexer with number formats, operators, keywords
- Recursive descent parser
- AST data structures
- Module declarations with parameters and ports
- Continuous assignments (`assign`)
- Always blocks (`@(posedge clk)`, `@(*)`)
- Expressions: arithmetic, bitwise, logical, comparison, shifts, ternary
- Statements: if/else, case/casex/casez, blocking/non-blocking assignments
- Bit operations: concatenation, replication, bit-select, part-select
- Module instantiation with named ports
- Generate blocks (basic)
- AST file output (.ast)
- Example files and CLI tool

---

## Phase 1: Missing Verilog-2005 Features (High Priority)

### 1.1 Declarations & Data Types ✅ COMPLETE
- [x] **Array declarations** ✅
  - [x] Unpacked arrays: `reg [7:0] mem [0:255];`
  - [x] Multi-dimensional arrays: `reg [7:0] mem [0:15][0:31];`
  - [x] Test: Parse memory array declarations
  - [x] Test: Parse multi-dimensional arrays

- [ ] **Memory declarations**
  - [ ] `memory` keyword support (if needed for spec compliance)
  - [ ] Test: Various memory sizes and configurations

- [ ] **Real and realtime types**
  - [ ] Lexer: Real number literals (1.5, 3.14e-2)
  - [ ] Parser: `real` and `realtime` declarations
  - [ ] Test: Real number parsing and declarations

- [ ] **Time type**
  - [ ] Parser: `time` declarations
  - [ ] Test: Time variable declarations

- [ ] **Event type**
  - [ ] Parser: `event` declarations
  - [ ] Statements: `->` event trigger, `@(event)`
  - [ ] Test: Event declarations and usage

### 1.2 Procedural Blocks ✅ COMPLETE
- [x] **Initial blocks** ✅
  - [x] Parser: `initial begin ... end`
  - [x] Test: Initial block parsing with various statements
  - [x] Test: Multiple initial blocks in one module

- [x] **Forever loops** ✅
  - [x] Parser: `forever` statement
  - [x] Test: Forever loops in always/initial blocks

- [x] **Repeat loops** ✅
  - [x] Parser: `repeat (N)` statement
  - [x] Test: Repeat with constant and variable counts

- [x] **While loops** ✅
  - [x] Parser: `while (condition)` statement
  - [x] Test: While loops with various conditions

- [x] **Disable statements** ✅
  - [x] Parser: `disable` statement
  - [x] Test: Disabling named blocks

### 1.3 Tasks and Functions ✅ COMPLETE
- [x] **Task declarations** ✅
  - [x] Parser: `task` ... `endtask`
  - [x] Task inputs/outputs/inouts
  - [x] Task calls
  - [x] Test: Simple tasks
  - [x] Test: Tasks with multiple arguments
  - [x] Test: Recursive task calls (if supported)

- [x] **Function declarations** ✅
  - [x] Parser: `function` ... `endfunction`
  - [x] Function inputs
  - [x] Function return values
  - [x] Function calls in expressions
  - [x] Test: Simple functions
  - [x] Test: Functions returning different bit widths
  - [x] Test: Recursive functions

- [x] **Automatic tasks/functions** ✅
  - [x] Parser: `automatic` keyword
  - [x] Test: Automatic vs static task/function behavior

### 1.4 Generate Constructs ✅ COMPLETE
- [x] **Generate if-else** ✅
  - [x] Parser: `if (param) ... else ...` in generate
  - [x] Test: Conditional generation based on parameters

- [x] **Generate case** ✅
  - [x] Parser: `case (param)` in generate
  - [x] Test: Generate case statements

- [x] **Generate blocks with names** ✅
  - [x] Parser: `begin : name ... end`
  - [x] Test: Named generate blocks

- [x] **Genvar improvements** ✅
  - [x] Proper scope handling for genvar
  - [x] Test: Multiple genvars in nested loops
  - [x] Test: Nested generate constructs
  - [x] Test: Generate with module instances

### 1.5 Attributes ✅ COMPLETE
- [x] **Attribute syntax** ✅
  - [x] Lexer: `(* ... *)` attribute parsing with state tracking
  - [x] Parser: Attach attributes to declarations and statements
  - [x] AST: Store attributes in nodes (base ASTNode.attributes field)
  - [x] Test: Attributes on modules, nets, instances
  - [x] Test: Multiple attributes
  - [x] Test: Attributes with and without values
  - [x] Test: Numeric and string attribute values

### 1.6 Specify Blocks (Timing - Optional for Synthesis)
- [ ] **Specify blocks**
  - [ ] Parser: `specify ... endspecify`
  - [ ] Path declarations: `(a => b) = delay;`
  - [ ] Test: Basic specify blocks
  - Note: Low priority for synthesis flow

### 1.7 System Tasks
- [ ] **Common system tasks**
  - [ ] `$display`, `$write`, `$monitor`
  - [ ] `$finish`, `$stop`
  - [ ] `$time`, `$realtime`
  - [ ] `$random`, `$urandom`
  - [ ] Test: System task calls with various arguments

- [ ] **File I/O system tasks**
  - [ ] `$fopen`, `$fclose`, `$fwrite`, `$fread`
  - [ ] Test: File I/O task parsing

### 1.8 Compiler Directives (Preprocessor)
- [ ] **Macro definitions**
  - [ ] Lexer: `` `define`` directive
  - [ ] Preprocessor: Macro expansion
  - [ ] Macro arguments: `` `define ADD(a,b) ((a)+(b))``
  - [ ] Test: Simple macros
  - [ ] Test: Macros with arguments
  - [ ] Test: Nested macro expansion

- [ ] **Conditional compilation**
  - [ ] `` `ifdef``, `` `ifndef``, `` `elsif``, `` `else``, `` `endif``
  - [ ] Test: Conditional compilation blocks
  - [ ] Test: Nested ifdef

- [ ] **Include files**
  - [ ] `` `include "file.v"``
  - [ ] Test: Include file parsing
  - [ ] Test: Nested includes

- [ ] **Other directives**
  - [ ] `` `timescale``
  - [ ] `` `default_nettype``
  - [ ] `` `resetall``
  - [ ] `` `celldefine``, `` `endcelldefine``
  - [ ] `` `unconnected_drive``, `` `nounconnected_drive``
  - [ ] Test: Each directive individually

### 1.9 Port Connection Styles ✅ COMPLETE (except SystemVerilog .* wildcard)
- [x] **Positional port connections** ✅
  - [x] Parser: Module instances with positional ports
  - [x] Test: `mod inst (a, b, c);`

- [x] **Mixed port connections** ✅
  - [x] Parser: Mix of positional and named ports
  - [x] Test: `mod inst (a, .b(sig_b), c);`

- [x] **Implicit port connections** ✅
  - [x] Parser: `.port()` for unconnected
  - [x] Test: Unconnected ports
  - [x] Test: Port connections with expressions

- [ ] **SystemVerilog wildcard (deferred)**
  - [ ] Parser: `.*` for implicit connections (SystemVerilog)
  - [ ] Test: Implicit wildcard connections

### 1.10 Operators & Expressions (Complete)
- [ ] **Unary reduction operators**
  - [ ] Verify: `&vector`, `|vector`, `^vector`, `~&`, `~|`, `~^`
  - [ ] Test: All reduction operators

- [ ] **Signed arithmetic**
  - [ ] Parser: `signed` keyword (already partially supported)
  - [ ] Verify signed operation semantics in AST
  - [ ] Test: Signed vs unsigned operations

- [ ] **Part-select with +: and -:**
  - [ ] Parser: `vector[base +: width]`
  - [ ] Parser: `vector[base -: width]`
  - [ ] Test: Indexed part-select operations

- [ ] **String literals**
  - [ ] Lexer: String escape sequences (`\n`, `\t`, etc.)
  - [ ] Test: Strings with escapes

### 1.11 Hierarchical Names
- [ ] **Hierarchical references**
  - [ ] Parser: `top.sub1.sub2.signal`
  - [ ] Test: Hierarchical signal references
  - [ ] Test: Hierarchical parameter access

---

## Phase 2: Parser Robustness & Error Handling

### 2.1 Error Recovery
- [ ] **Better error messages**
  - [ ] Show context (line of code with error)
  - [ ] Suggest fixes for common mistakes
  - [ ] Test: Error message quality for various syntax errors

- [ ] **Error recovery**
  - [ ] Continue parsing after errors to find multiple errors
  - [ ] Synchronization points (`;`, `end`, `endmodule`)
  - [ ] Test: Multiple syntax errors in one file

- [ ] **Warnings**
  - [ ] Implicit net declarations
  - [ ] Unused variables
  - [ ] Width mismatches
  - [ ] Test: Warning generation

### 2.2 Edge Cases
- [ ] **Empty constructs**
  - [ ] Empty modules
  - [ ] Empty always blocks
  - [ ] Empty generate blocks
  - [ ] Test: All empty construct types

- [ ] **Maximum sizes**
  - [ ] Very long identifiers
  - [ ] Deep nesting
  - [ ] Large number literals
  - [ ] Test: Extreme sizes

- [ ] **Unicode and special characters**
  - [ ] Escaped identifiers: `\bus[0]`
  - [ ] Test: Escaped identifier parsing

---

## Phase 3: Comprehensive Test Suite

### 3.1 Test Organization
- [ ] **Create test structure**
  - [ ] `tests/parser/lexer/` - Lexer tests
  - [ ] `tests/parser/expressions/` - Expression tests
  - [ ] `tests/parser/statements/` - Statement tests
  - [ ] `tests/parser/declarations/` - Declaration tests
  - [ ] `tests/parser/modules/` - Module-level tests
  - [ ] `tests/parser/edge_cases/` - Edge case tests
  - [ ] `tests/parser/error_cases/` - Error handling tests

### 3.2 Lexer Tests
- [ ] **Token types**
  - [ ] Test: Every token type
  - [ ] Test: Multi-character operators
  - [ ] Test: Keywords vs identifiers

- [ ] **Number formats**
  - [ ] Test: All radix formats (binary, octal, decimal, hex)
  - [ ] Test: Sized and unsized numbers
  - [ ] Test: Underscores in numbers
  - [ ] Test: X and Z values
  - [ ] Test: Signed numbers

- [ ] **Comments**
  - [ ] Test: Line comments with various content
  - [ ] Test: Block comments
  - [ ] Test: Nested block comments (if supported)
  - [ ] Test: Comments at EOF

### 3.3 Parser Tests
- [ ] **Expression tests**
  - [ ] Test: Operator precedence (comprehensive)
  - [ ] Test: Associativity
  - [ ] Test: All binary operators
  - [ ] Test: All unary operators
  - [ ] Test: Ternary operators (nested)
  - [ ] Test: Function calls in expressions

- [ ] **Statement tests**
  - [ ] Test: All statement types
  - [ ] Test: Nested statements
  - [ ] Test: Statement blocks

- [ ] **Declaration tests**
  - [ ] Test: All declaration types
  - [ ] Test: Declaration with initialization
  - [ ] Test: Multiple declarations

- [ ] **Module tests**
  - [ ] Test: Module headers (all variations)
  - [ ] Test: Parameter overrides
  - [ ] Test: Module instances (all connection styles)

### 3.4 Integration Tests
- [ ] **Real-world designs**
  - [ ] Test: UART module
  - [ ] Test: Simple CPU
  - [ ] Test: SPI controller
  - [ ] Test: FIFO buffer
  - [ ] Test: AXI interface

- [ ] **Verilog test suites**
  - [ ] Integrate existing Verilog test suites
  - [ ] ivtest (Icarus Verilog tests)
  - [ ] Test: Common IP cores (if available)

### 3.5 Test Automation
- [ ] **Test runner**
  - [ ] Automated test discovery
  - [ ] Parallel test execution
  - [ ] Test coverage reporting
  - [ ] Regression test suite

- [ ] **Golden reference comparison**
  - [ ] Compare AST against known-good parsers (Yosys, Verilator)
  - [ ] Test: AST equivalence

---

## Phase 4: AST Improvements

### 4.1 AST Representation
- [ ] **Add source location to all nodes**
  - [ ] Verify all nodes have line/col
  - [ ] Add filename to nodes
  - [ ] Test: Source location accuracy

- [ ] **AST validation**
  - [ ] Check for malformed AST
  - [ ] Validate parent-child relationships
  - [ ] Test: AST validator

- [ ] **AST visitor pattern**
  - [ ] Implement visitor base class
  - [ ] Implement AST traversal utilities
  - [ ] Test: Visitor implementation

### 4.2 AST Serialization
- [ ] **JSON output**
  - [ ] Serialize AST to JSON
  - [ ] Deserialize AST from JSON
  - [ ] Test: Round-trip serialization

- [ ] **Compact AST format**
  - [ ] More efficient .ast file format
  - [ ] Optional: Binary AST format
  - [ ] Test: Format comparison

### 4.3 AST Pretty-Printing
- [ ] **Verilog code generation from AST**
  - [ ] Pretty-print AST back to Verilog
  - [ ] Configurable formatting
  - [ ] Test: AST → Verilog → AST round-trip

---

## Phase 5: Documentation

### 5.1 User Documentation
- [ ] **Parser usage guide**
  - [ ] Command-line options
  - [ ] API documentation
  - [ ] Examples for all features

- [ ] **Supported Verilog features**
  - [ ] Comprehensive feature list
  - [ ] Known limitations
  - [ ] Compatibility matrix

### 5.2 Developer Documentation
- [ ] **Parser architecture**
  - [ ] Lexer design
  - [ ] Parser design (recursive descent)
  - [ ] AST design

- [ ] **Extending the parser**
  - [ ] Adding new constructs
  - [ ] Adding new AST node types
  - [ ] Test writing guide

### 5.3 Grammar Documentation
- [ ] **Formal grammar**
  - [ ] EBNF grammar specification
  - [ ] Railroad diagrams
  - [ ] Grammar cross-reference with IEEE 1364-2005

---

## Phase 6: Performance & Optimization

### 6.1 Performance
- [ ] **Benchmark suite**
  - [ ] Small, medium, large file benchmarks
  - [ ] Performance tracking over time

- [ ] **Optimization**
  - [ ] Profile parser hotspots
  - [ ] Optimize token stream handling
  - [ ] Optimize AST node creation

### 6.2 Memory Usage
- [ ] **Memory profiling**
  - [ ] Track memory usage on large files
  - [ ] Optimize AST memory footprint

---

## Success Criteria

The Verilog parser is considered **complete** when:

1. ✅ **Feature Complete**: Supports all Verilog-2005 synthesizable constructs
2. ✅ **Fully Tested**: >95% code coverage, comprehensive test suite
3. ✅ **Spec Compliant**: Passes IEEE 1364-2005 compliance tests
4. ✅ **Error Handling**: Clear error messages, graceful error recovery
5. ✅ **Well Documented**: Complete user and developer documentation
6. ✅ **AST Output**: Generates correct, validated AST files
7. ✅ **Production Ready**: Used to parse real-world Verilog designs

---

## Phase 7: SystemVerilog Features

### 7.1 SystemVerilog Data Types
- [ ] **Logic type**
  - [ ] Parser: `logic` data type (4-state)
  - [ ] Parser: `bit` data type (2-state)
  - [ ] Parser: `byte`, `shortint`, `int`, `longint`
  - [ ] Test: All integer types

- [ ] **Packed and unpacked arrays**
  - [ ] Parser: Packed arrays: `logic [7:0][3:0] data;`
  - [ ] Parser: Unpacked arrays: `logic data [8][4];`
  - [ ] Parser: Dynamic arrays: `int queue[];`
  - [ ] Parser: Associative arrays: `int map[string];`
  - [ ] Parser: Queues: `int q[$];`
  - [ ] Test: All array types

- [ ] **Structures and unions**
  - [ ] Parser: `struct` declarations
  - [ ] Parser: `union` declarations
  - [ ] Parser: Packed structures
  - [ ] Parser: Tagged unions
  - [ ] Test: Structure and union usage

- [ ] **Enumerations**
  - [ ] Parser: `enum` declarations
  - [ ] Parser: Typed enums
  - [ ] Parser: Enum methods
  - [ ] Test: Enum usage in expressions

- [ ] **Typedef**
  - [ ] Parser: `typedef` declarations
  - [ ] Parser: Type references
  - [ ] Test: User-defined types

- [ ] **Strings**
  - [ ] Parser: `string` type
  - [ ] String methods and operators
  - [ ] Test: String manipulation

### 7.2 SystemVerilog Procedural Enhancements
- [ ] **Always_comb, always_ff, always_latch**
  - [ ] Parser: `always_comb`
  - [ ] Parser: `always_ff`
  - [ ] Parser: `always_latch`
  - [ ] Test: Specialized always blocks

- [ ] **Unique, unique0, priority**
  - [ ] Parser: `unique if`, `unique case`
  - [ ] Parser: `unique0 case`
  - [ ] Parser: `priority if`, `priority case`
  - [ ] Test: Decision coverage keywords

- [ ] **Enhanced for loops**
  - [ ] Parser: `for (int i = 0; ...)` with inline declarations
  - [ ] Parser: `foreach` loops
  - [ ] Test: Enhanced loop constructs

- [ ] **Do-while loops**
  - [ ] Parser: `do ... while (condition);`
  - [ ] Test: Do-while loops

- [ ] **Return statement**
  - [ ] Parser: `return` in tasks/functions
  - [ ] Test: Return usage

- [ ] **Break and continue**
  - [ ] Parser: `break` statement
  - [ ] Parser: `continue` statement
  - [ ] Test: Loop control statements

### 7.3 SystemVerilog Module Enhancements
- [ ] **Interface declarations**
  - [ ] Parser: `interface ... endinterface`
  - [ ] Parser: Modports
  - [ ] Parser: Interface instances
  - [ ] Parser: Virtual interfaces
  - [ ] Test: Interface-based connections

- [ ] **Packages**
  - [ ] Parser: `package ... endpackage`
  - [ ] Parser: Package imports: `import pkg::*;`
  - [ ] Parser: Package exports
  - [ ] Test: Package usage

- [ ] **Program blocks**
  - [ ] Parser: `program ... endprogram`
  - [ ] Test: Program blocks

- [ ] **Bind statement**
  - [ ] Parser: `bind` for assertion modules
  - [ ] Test: Bind usage

### 7.4 SystemVerilog Operators and Expressions
- [ ] **Enhanced operators**
  - [ ] Parser: Streaming operators: `<<`, `>>`
  - [ ] Parser: Set membership: `inside`
  - [ ] Parser: Wildcard equality: `==?`, `!=?`
  - [ ] Parser: Implication: `->`, `<->`
  - [ ] Test: All new operators

- [ ] **Assignment operators**
  - [ ] Parser: `+=`, `-=`, `*=`, `/=`, etc.
  - [ ] Test: Compound assignment operators

- [ ] **Casting**
  - [ ] Parser: Static cast: `int'(x)`
  - [ ] Parser: Dynamic cast: `$cast(dest, src)`
  - [ ] Test: Casting operations

### 7.5 SystemVerilog Constraints (Verification)
- [ ] **Constraint blocks**
  - [ ] Parser: `constraint` blocks in classes
  - [ ] Parser: Constraint expressions
  - [ ] Parser: `solve ... before`
  - [ ] Test: Constraint parsing

- [ ] **Randomization**
  - [ ] Parser: `rand`, `randc` variables
  - [ ] Parser: `randomize()` calls
  - [ ] Test: Randomization constructs

### 7.6 SystemVerilog Assertions
- [ ] **Immediate assertions**
  - [ ] Parser: `assert`, `assume`, `cover`
  - [ ] Test: Immediate assertions

- [ ] **Concurrent assertions (SVA)**
  - [ ] Parser: `property` declarations
  - [ ] Parser: `sequence` declarations
  - [ ] Parser: Temporal operators: `##`, `|->`, `|=>`, etc.
  - [ ] Parser: `assert property`, `assume property`, `cover property`
  - [ ] Test: SVA parsing (comprehensive)

### 7.7 SystemVerilog Classes (OOP)
- [ ] **Class declarations**
  - [ ] Parser: `class ... endclass`
  - [ ] Parser: Class properties
  - [ ] Parser: Class methods (tasks and functions)
  - [ ] Parser: Constructors: `new()`
  - [ ] Test: Basic classes

- [ ] **Inheritance**
  - [ ] Parser: `extends` keyword
  - [ ] Parser: `super` keyword
  - [ ] Parser: Virtual methods
  - [ ] Test: Class inheritance

- [ ] **Polymorphism**
  - [ ] Parser: Virtual classes
  - [ ] Parser: Virtual methods
  - [ ] Test: Polymorphic behavior

- [ ] **Parameterized classes**
  - [ ] Parser: Class parameters
  - [ ] Test: Parameterized class usage

- [ ] **Static members**
  - [ ] Parser: `static` properties and methods
  - [ ] Test: Static member access

- [ ] **Class scope resolution**
  - [ ] Parser: `::` operator for class scope
  - [ ] Test: Scope resolution

### 7.8 SystemVerilog Coverage
- [ ] **Covergroups**
  - [ ] Parser: `covergroup ... endgroup`
  - [ ] Parser: Coverpoints
  - [ ] Parser: Cross coverage
  - [ ] Parser: Coverage options
  - [ ] Test: Covergroup parsing

### 7.9 SystemVerilog Interprocess Communication
- [ ] **Semaphores**
  - [ ] Parser: Semaphore methods
  - [ ] Test: Semaphore usage

- [ ] **Mailboxes**
  - [ ] Parser: Mailbox methods
  - [ ] Test: Mailbox usage

- [ ] **Events**
  - [ ] Parser: Event control enhancements
  - [ ] Parser: `wait fork`, `disable fork`
  - [ ] Test: Event synchronization

### 7.10 SystemVerilog DPI (Direct Programming Interface)
- [ ] **DPI imports**
  - [ ] Parser: `import "DPI-C"` declarations
  - [ ] Parser: DPI function prototypes
  - [ ] Test: DPI import parsing

- [ ] **DPI exports**
  - [ ] Parser: `export "DPI-C"` declarations
  - [ ] Test: DPI export parsing

### 7.11 SystemVerilog Functional Coverage
- [ ] **Functional coverage constructs**
  - [ ] Complete covergroup syntax
  - [ ] Bins and crosses
  - [ ] Coverage options and methods
  - [ ] Test: Full coverage feature set

### 7.12 SystemVerilog Specialized Features
- [ ] **Clocking blocks**
  - [ ] Parser: `clocking ... endclocking`
  - [ ] Parser: Clocking skews
  - [ ] Test: Clocking block usage

- [ ] **Checkers**
  - [ ] Parser: `checker ... endchecker`
  - [ ] Test: Checker modules

- [ ] **Configuration libraries**
  - [ ] Parser: `config ... endconfig`
  - [ ] Test: Configuration blocks

### 7.13 SystemVerilog Spec Compliance Testing
- [ ] **IEEE 1800 Compliance Suite**
  - [ ] Run official SystemVerilog compliance tests (if available)
  - [ ] Document any deviations from spec
  - [ ] Test: 100% spec coverage

- [ ] **Cross-tool validation**
  - [ ] Compare against commercial simulators (if available)
  - [ ] Compare against open-source: Verilator, Slang
  - [ ] Document compatibility matrix

---

## Notes

- Focus on **synthesizable subset** first (Phases 1-4)
- SystemVerilog **synthesizable features** (Phase 7.1-7.4) before verification features
- SystemVerilog **verification features** (Phase 7.5-7.12) for testbench support
- Each checkbox represents a discrete, testable work item
- Tests should be written **before or alongside** implementation (TDD)
- Use existing parsers as reference: Slang (most complete SV parser), Verilator, Yosys
- **SystemVerilog spec document** is available in this repository - reference it for all implementations

---

## Current Priority

**Phase 1** (Verilog-2005 core features) → **Phase 3** (testing) → **Phase 7** (SystemVerilog)

**Start with Phase 1.1-1.4** to complete core Verilog-2005 feature coverage, then move to Phase 3 for comprehensive testing, then begin SystemVerilog features in Phase 7.
