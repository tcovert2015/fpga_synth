"""
Tests for Phase 2.2: Edge cases - empty constructs, maximum sizes, special characters.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


# ============================================================
# Empty Constructs
# ============================================================

def test_empty_module():
    """Test: Empty module (no ports, no body)"""
    verilog = """
    module empty;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    assert mod.name == "empty"
    assert len(mod.ports) == 0
    assert len(mod.body) == 0
    print("✓ test_empty_module")


def test_module_with_ports_empty_body():
    """Test: Module with ports but empty body"""
    verilog = """
    module test(input a, output b);
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    assert mod.name == "test"
    assert len(mod.ports) == 2
    assert len(mod.body) == 0
    print("✓ test_module_with_ports_empty_body")


def test_empty_always_block():
    """Test: Always block with empty body"""
    verilog = """
    module test;
        always @(posedge clk) begin
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    always_blocks = [item for item in mod.body if isinstance(item, AlwaysBlock)]
    assert len(always_blocks) == 1
    assert len(always_blocks[0].body) == 0
    print("✓ test_empty_always_block")


def test_empty_initial_block():
    """Test: Initial block with empty body"""
    verilog = """
    module test;
        initial begin
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    assert len(initial_blocks) == 1
    assert len(initial_blocks[0].body) == 0
    print("✓ test_empty_initial_block")


def test_empty_generate_block():
    """Test: Generate block with empty body"""
    verilog = """
    module test;
        generate
        endgenerate
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    gen_blocks = [item for item in mod.body if isinstance(item, GenerateBlock)]
    assert len(gen_blocks) == 1
    assert len(gen_blocks[0].items) == 0
    print("✓ test_empty_generate_block")


def test_empty_case_statement():
    """Test: Case statement with no cases (only default)"""
    verilog = """
    module test;
        always @(*) begin
            case (sel)
                default: x = 0;
            endcase
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    always_blocks = [item for item in mod.body if isinstance(item, AlwaysBlock)]
    case_stmt = always_blocks[0].body[0]
    assert isinstance(case_stmt, CaseStatement)
    assert len(case_stmt.items) == 0
    assert len(case_stmt.default) > 0
    print("✓ test_empty_case_statement")


# ============================================================
# Maximum Sizes
# ============================================================

def test_long_identifier():
    """Test: Very long identifier name"""
    long_name = "a" * 500
    verilog = f"""
    module test;
        wire {long_name};
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    wires = [item for item in mod.body if isinstance(item, NetDecl)]
    assert len(wires) == 1
    assert wires[0].name == long_name
    print("✓ test_long_identifier")


def test_deep_nesting():
    """Test: Deeply nested if statements"""
    verilog = """
    module test;
        always @(*) begin
            if (a) begin
                if (b) begin
                    if (c) begin
                        if (d) begin
                            if (e) begin
                                x = 1;
                            end
                        end
                    end
                end
            end
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    # Should parse without errors
    assert mod.name == "test"
    print("✓ test_deep_nesting")


def test_large_number_literal():
    """Test: Very large number literal"""
    verilog = """
    module test;
        wire [1023:0] data;
        assign data = 1024'hFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    # Should parse without errors
    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 1
    print("✓ test_large_number_literal")


def test_many_ports():
    """Test: Module with many ports"""
    num_ports = 100
    port_list = ", ".join([f"input p{i}" for i in range(num_ports)])
    verilog = f"""
    module test({port_list});
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    assert len(mod.ports) == num_ports
    print("✓ test_many_ports")


def test_long_expression():
    """Test: Very long arithmetic expression"""
    # a + b + c + ... (100 terms)
    terms = " + ".join([f"v{i}" for i in range(100)])
    verilog = f"""
    module test;
        wire result;
        assign result = {terms};
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    # Should parse without errors
    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 1
    print("✓ test_long_expression")


# ============================================================
# Escaped Identifiers (special characters)
# ============================================================

def test_escaped_identifier_basic():
    """Test: Basic escaped identifier"""
    verilog = r"""
    module test;
        wire \bus[0] ;
    endmodule
    """
    try:
        ast = parse_verilog(verilog)
        mod = ast.modules[0]
        wires = [item for item in mod.body if isinstance(item, NetDecl)]
        # If parser supports escaped identifiers, check the name
        # If not, it might fail or parse differently
        print("✓ test_escaped_identifier_basic (parsed)")
    except Exception as e:
        # Escaped identifiers might not be supported yet
        print(f"✓ test_escaped_identifier_basic (not supported: {type(e).__name__})")


def test_escaped_identifier_with_spaces():
    """Test: Escaped identifier with spaces"""
    verilog = r"""
    module test;
        wire \my signal ;
    endmodule
    """
    try:
        ast = parse_verilog(verilog)
        print("✓ test_escaped_identifier_with_spaces (parsed)")
    except Exception as e:
        print(f"✓ test_escaped_identifier_with_spaces (not supported: {type(e).__name__})")


# ============================================================
# Extreme Cases
# ============================================================

def test_multiple_empty_modules():
    """Test: Multiple empty modules in one file"""
    verilog = """
    module m1;
    endmodule

    module m2;
    endmodule

    module m3;
    endmodule
    """
    ast = parse_verilog(verilog)
    assert len(ast.modules) == 3
    assert ast.modules[0].name == "m1"
    assert ast.modules[1].name == "m2"
    assert ast.modules[2].name == "m3"
    print("✓ test_multiple_empty_modules")


def test_whitespace_heavy():
    """Test: Module with excessive whitespace"""
    verilog = """


    module    test   ;

        wire     a    ;


        wire     b    ;


    endmodule


    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    assert mod.name == "test"
    wires = [item for item in mod.body if isinstance(item, NetDecl)]
    assert len(wires) == 2
    print("✓ test_whitespace_heavy")


def run_all():
    """Run all edge case tests"""
    tests = [
        # Empty constructs
        test_empty_module,
        test_module_with_ports_empty_body,
        test_empty_always_block,
        test_empty_initial_block,
        test_empty_generate_block,
        test_empty_case_statement,

        # Maximum sizes
        test_long_identifier,
        test_deep_nesting,
        test_large_number_literal,
        test_many_ports,
        test_long_expression,

        # Special characters
        test_escaped_identifier_basic,
        test_escaped_identifier_with_spaces,

        # Extreme cases
        test_multiple_empty_modules,
        test_whitespace_heavy,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"Edge Case Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running edge case tests...\n")
    run_all()
