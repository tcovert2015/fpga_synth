"""
Tests for additional data types (real, realtime, time, event).

Completing Phase 1.1 of the TODO list.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


def test_real_declaration():
    """Test: real variable declaration"""
    verilog = """
    module test;
        real voltage;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    real_decls = [item for item in mod.body if isinstance(item, RealDecl)]
    assert len(real_decls) == 1
    assert real_decls[0].name == "voltage"
    assert real_decls[0].kind == "real"
    print("✓ test_real_declaration")


def test_real_with_initialization():
    """Test: real variable with initialization"""
    verilog = """
    module test;
        real pi = 3.14159;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    real_decls = [item for item in mod.body if isinstance(item, RealDecl)]
    assert len(real_decls) == 1
    assert real_decls[0].name == "pi"
    assert real_decls[0].init_value is not None
    print("✓ test_real_with_initialization")


def test_realtime_declaration():
    """Test: realtime variable declaration"""
    verilog = """
    module test;
        realtime current_time;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    real_decls = [item for item in mod.body if isinstance(item, RealDecl)]
    assert len(real_decls) == 1
    assert real_decls[0].name == "current_time"
    assert real_decls[0].kind == "realtime"
    print("✓ test_realtime_declaration")


def test_time_declaration():
    """Test: time variable declaration"""
    verilog = """
    module test;
        time timestamp;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    time_decls = [item for item in mod.body if isinstance(item, TimeDecl)]
    assert len(time_decls) == 1
    assert time_decls[0].name == "timestamp"
    print("✓ test_time_declaration")


def test_time_with_initialization():
    """Test: time variable with initialization"""
    verilog = """
    module test;
        time start_time = 0;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    time_decls = [item for item in mod.body if isinstance(item, TimeDecl)]
    assert len(time_decls) == 1
    assert time_decls[0].name == "start_time"
    assert time_decls[0].init_value is not None
    print("✓ test_time_with_initialization")


def test_event_declaration():
    """Test: event declaration"""
    verilog = """
    module test;
        event data_ready;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    event_decls = [item for item in mod.body if isinstance(item, EventDecl)]
    assert len(event_decls) == 1
    assert event_decls[0].name == "data_ready"
    print("✓ test_event_declaration")


def test_event_trigger():
    """Test: event trigger statement"""
    verilog = """
    module test;
        event done;
        initial begin
            -> done;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    # Find initial block
    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    assert len(initial_blocks) == 1

    # Find event trigger in initial block
    trigger_found = False
    for stmt in initial_blocks[0].body:
        if isinstance(stmt, EventTrigger):
            assert stmt.event == "done"
            trigger_found = True
            break

    assert trigger_found
    print("✓ test_event_trigger")


def test_real_number_literals():
    """Test: parsing real number literals"""
    verilog = """
    module test;
        real a = 1.5;
        real b = 3.14159;
        real c = 2.5e10;
        real d = 1.0e-3;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    real_decls = [item for item in mod.body if isinstance(item, RealDecl)]
    assert len(real_decls) == 4

    # All should have initialization values
    for decl in real_decls:
        assert decl.init_value is not None

    print("✓ test_real_number_literals")


def test_mixed_data_types():
    """Test: module with mixed data types"""
    verilog = """
    module test;
        wire w;
        reg r;
        integer i;
        real voltage;
        time t;
        event e;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    wires = [item for item in mod.body if isinstance(item, NetDecl) and item.net_type == "wire"]
    regs = [item for item in mod.body if isinstance(item, NetDecl) and item.net_type == "reg"]
    integers = [item for item in mod.body if isinstance(item, IntegerDecl)]
    reals = [item for item in mod.body if isinstance(item, RealDecl)]
    times = [item for item in mod.body if isinstance(item, TimeDecl)]
    events = [item for item in mod.body if isinstance(item, EventDecl)]

    assert len(wires) == 1
    assert len(regs) == 1
    assert len(integers) == 1
    assert len(reals) == 1
    assert len(times) == 1
    assert len(events) == 1

    print("✓ test_mixed_data_types")


def run_all():
    """Run all data type tests"""
    tests = [
        test_real_declaration,
        test_real_with_initialization,
        test_realtime_declaration,
        test_time_declaration,
        test_time_with_initialization,
        test_event_declaration,
        test_event_trigger,
        test_real_number_literals,
        test_mixed_data_types,
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
    print(f"Data Type Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running data type tests...\n")
    run_all()
