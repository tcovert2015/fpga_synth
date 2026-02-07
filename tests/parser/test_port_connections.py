"""
Tests for different port connection styles.

Part of Phase 1.9 of the TODO list.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


def test_positional_port_connections():
    """Test: module instance with positional port connections"""
    verilog = """
    module test;
        wire a;
        wire b;
        wire c;
        my_module inst (a, b, c);
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    instances = [item for item in mod.body if isinstance(item, ModuleInstance)]
    assert len(instances) == 1

    inst = instances[0]
    assert inst.instance_name == "inst"
    assert len(inst.ports) == 3

    # Positional connections have no port_name
    assert inst.ports[0].port_name == ""
    assert inst.ports[1].port_name == ""
    assert inst.ports[2].port_name == ""

    # But they have expressions
    assert inst.ports[0].expr is not None
    assert inst.ports[1].expr is not None
    assert inst.ports[2].expr is not None

    print("✓ test_positional_port_connections")


def test_named_port_connections():
    """Test: module instance with named port connections"""
    verilog = """
    module test;
        wire a;
        wire b;
        wire c;
        my_module inst (
            .port_a(a),
            .port_b(b),
            .port_c(c)
        );
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    instances = [item for item in mod.body if isinstance(item, ModuleInstance)]
    inst = instances[0]

    assert len(inst.ports) == 3
    assert inst.ports[0].port_name == "port_a"
    assert inst.ports[1].port_name == "port_b"
    assert inst.ports[2].port_name == "port_c"

    print("✓ test_named_port_connections")


def test_mixed_port_connections():
    """Test: module instance with mixed positional and named ports"""
    verilog = """
    module test;
        wire a;
        wire b;
        wire c;
        wire d;
        my_module inst (a, b, .port_c(c), .port_d(d));
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    instances = [item for item in mod.body if isinstance(item, ModuleInstance)]
    inst = instances[0]

    assert len(inst.ports) == 4

    # First two are positional
    assert inst.ports[0].port_name == ""
    assert inst.ports[1].port_name == ""

    # Last two are named
    assert inst.ports[2].port_name == "port_c"
    assert inst.ports[3].port_name == "port_d"

    print("✓ test_mixed_port_connections")


def test_unconnected_port():
    """Test: unconnected port with .port()"""
    verilog = """
    module test;
        wire a;
        wire b;
        my_module inst (
            .port_a(a),
            .port_b(),
            .port_c(b)
        );
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    instances = [item for item in mod.body if isinstance(item, ModuleInstance)]
    inst = instances[0]

    assert len(inst.ports) == 3
    assert inst.ports[0].port_name == "port_a"
    assert inst.ports[0].expr is not None

    # Unconnected port
    assert inst.ports[1].port_name == "port_b"
    assert inst.ports[1].expr is None

    assert inst.ports[2].port_name == "port_c"
    assert inst.ports[2].expr is not None

    print("✓ test_unconnected_port")


def test_port_with_expression():
    """Test: port connected to expression"""
    verilog = """
    module test;
        wire [7:0] a;
        wire [7:0] b;
        my_module inst (
            .port_a(a + b),
            .port_b(a[3:0])
        );
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    instances = [item for item in mod.body if isinstance(item, ModuleInstance)]
    inst = instances[0]

    assert len(inst.ports) == 2

    # First port has an addition expression
    assert inst.ports[0].port_name == "port_a"
    assert isinstance(inst.ports[0].expr, BinaryOp)

    # Second port has a bit-select expression
    assert inst.ports[1].port_name == "port_b"
    assert isinstance(inst.ports[1].expr, BitSelect)

    print("✓ test_port_with_expression")


def run_all():
    """Run all port connection tests"""
    tests = [
        test_positional_port_connections,
        test_named_port_connections,
        test_mixed_port_connections,
        test_unconnected_port,
        test_port_with_expression,
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
    print(f"Port Connection Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running port connection tests...\n")
    run_all()
