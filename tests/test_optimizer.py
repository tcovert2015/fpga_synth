"""
Tests for netlist optimization passes.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.elaborator import elaborate
from fpga_synth.ir.optimizer import optimize_netlist
from fpga_synth.ir.types import CellOp


def test_constant_propagation():
    """Test: Constant propagation"""
    verilog = """
    module test(
        output wire [7:0] result
    );
        assign result = 8'd5 + 8'd3;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Before optimization: should have CONST cells and ADD cell
    add_cells_before = [c for c in netlist.cells.values() if c.op == CellOp.ADD]
    assert len(add_cells_before) >= 1

    # Optimize
    stats = optimize_netlist(netlist, passes=["constant_prop"])

    # After optimization: ADD should be replaced with CONST
    add_cells_after = [c for c in netlist.cells.values() if c.op == CellOp.ADD]
    assert len(add_cells_after) == 0

    # Should have propagated at least one constant
    assert stats["constants_propagated"] >= 1

    print("✓ test_constant_propagation")


def test_constant_propagation_logic():
    """Test: Constant propagation with logic"""
    verilog = """
    module test(
        output wire result
    );
        assign result = 1'b1 & 1'b0;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Before: should have AND cell
    and_cells_before = [c for c in netlist.cells.values() if c.op == CellOp.AND]
    assert len(and_cells_before) >= 1

    # Optimize
    optimize_netlist(netlist, passes=["constant_prop"])

    # After: AND should be replaced with CONST (result is 0)
    and_cells_after = [c for c in netlist.cells.values() if c.op == CellOp.AND]
    assert len(and_cells_after) == 0

    # Should have CONST cell with value 0
    const_cells = [c for c in netlist.cells.values() if c.op == CellOp.CONST]
    assert any(c.attributes.get("value") == 0 for c in const_cells)

    print("✓ test_constant_propagation_logic")


def test_dead_code_elimination():
    """Test: Dead code elimination"""
    verilog = """
    module test(
        input wire a,
        output wire b
    );
        wire unused;
        assign unused = a & a;
        assign b = a;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Count cells before optimization
    cells_before = len([c for c in netlist.cells.values()
                       if c.op not in (CellOp.MODULE_INPUT, CellOp.MODULE_OUTPUT)])

    # Optimize
    stats = optimize_netlist(netlist, passes=["dead_code"])

    # After: unused AND cell should be removed
    cells_after = len([c for c in netlist.cells.values()
                      if c.op not in (CellOp.MODULE_INPUT, CellOp.MODULE_OUTPUT)])

    assert cells_after < cells_before
    assert stats["dead_cells_removed"] >= 1

    print("✓ test_dead_code_elimination")


def test_common_subexpression_elimination():
    """Test: Common subexpression elimination"""
    verilog = """
    module test(
        input wire a,
        input wire b,
        output wire c,
        output wire d
    );
        assign c = a & b;
        assign d = a & b;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Before: should have 2 AND cells
    and_cells_before = [c for c in netlist.cells.values() if c.op == CellOp.AND]
    assert len(and_cells_before) >= 2

    # Optimize
    stats = optimize_netlist(netlist, passes=["cse"])

    # After: should have only 1 AND cell (common subexpression)
    and_cells_after = [c for c in netlist.cells.values() if c.op == CellOp.AND]
    assert len(and_cells_after) >= 1
    assert len(and_cells_after) < len(and_cells_before)
    assert stats["common_subexprs_eliminated"] >= 1

    print("✓ test_common_subexpression_elimination")


def test_combined_optimization():
    """Test: Combined optimization passes"""
    verilog = """
    module test(
        input wire a,
        output wire result
    );
        wire unused;
        wire temp1;
        wire temp2;

        assign unused = a | a;
        assign temp1 = a & 1'b1;
        assign temp2 = a & 1'b1;
        assign result = temp1 | temp2;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    cells_before = len(netlist.cells)

    # Run all optimizations
    stats = optimize_netlist(netlist)

    cells_after = len(netlist.cells)

    # Should have removed some cells
    assert cells_after < cells_before

    print(f"✓ test_combined_optimization (cells: {cells_before} → {cells_after})")


def test_optimization_preserves_outputs():
    """Test: Optimization preserves module outputs"""
    verilog = """
    module test(
        input wire a,
        input wire b,
        output wire sum,
        output wire carry
    );
        assign sum = a ^ b;
        assign carry = a & b;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Optimize
    optimize_netlist(netlist)

    # Outputs should still exist
    assert "sum" in netlist.outputs
    assert "carry" in netlist.outputs

    # Output cells should have drivers
    sum_cell = netlist.outputs["sum"]
    carry_cell = netlist.outputs["carry"]

    sum_input_net = list(sum_cell.inputs.values())[0].net
    carry_input_net = list(carry_cell.inputs.values())[0].net

    assert sum_input_net is not None
    assert carry_input_net is not None
    assert sum_input_net.driver is not None
    assert carry_input_net.driver is not None

    print("✓ test_optimization_preserves_outputs")


def test_no_optimization_on_sequential():
    """Test: Sequential elements not optimized away"""
    verilog = """
    module test(
        input wire clk,
        input wire d,
        output reg q
    );
        always @(posedge clk) begin
            q <= d;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Count DFFs before
    dff_before = [c for c in netlist.cells.values()
                  if c.op in (CellOp.DFF, CellOp.DFFR)]

    # Optimize
    optimize_netlist(netlist)

    # DFFs should still exist
    dff_after = [c for c in netlist.cells.values()
                 if c.op in (CellOp.DFF, CellOp.DFFR)]

    assert len(dff_after) == len(dff_before)

    print("✓ test_no_optimization_on_sequential")


def run_all():
    """Run all optimizer tests"""
    tests = [
        test_constant_propagation,
        test_constant_propagation_logic,
        test_dead_code_elimination,
        test_common_subexpression_elimination,
        test_combined_optimization,
        test_optimization_preserves_outputs,
        test_no_optimization_on_sequential,
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
    print(f"Optimizer Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running optimizer tests...\n")
    run_all()
