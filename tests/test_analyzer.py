"""
Tests for netlist analysis tools.
"""

import sys
import os
import tempfile
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.elaborator import elaborate
from fpga_synth.ir.analyzer import NetlistAnalyzer, analyze_netlist
from fpga_synth.ir.types import CellOp


def test_resource_usage_combinational():
    """Test: Resource usage for combinational logic"""
    verilog = """
    module test(
        input wire [7:0] a,
        input wire [7:0] b,
        output wire [7:0] sum,
        output wire [7:0] logic_out
    );
        assign sum = a + b;
        assign logic_out = a & b;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    analyzer = NetlistAnalyzer(netlist)
    usage = analyzer.resource_usage()

    # Should have some LUTs for logic, adder for addition
    assert usage["adders"] >= 1
    assert usage["luts"] >= 1
    assert usage["ffs"] == 0  # No sequential logic
    assert usage["memories"] == 0

    print(f"✓ test_resource_usage_combinational: {usage}")


def test_resource_usage_sequential():
    """Test: Resource usage for sequential logic"""
    verilog = """
    module test(
        input wire clk,
        input wire [7:0] d,
        output reg [7:0] q
    );
        always @(posedge clk) begin
            q <= d;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    analyzer = NetlistAnalyzer(netlist)
    usage = analyzer.resource_usage()

    # Should have flip-flops
    assert usage["ffs"] >= 1
    assert usage["luts"] == 0  # No combinational logic
    assert usage["adders"] == 0

    print(f"✓ test_resource_usage_sequential: {usage}")


def test_resource_usage_memory():
    """Test: Resource usage for memory"""
    verilog = """
    module test(
        input wire clk,
        input wire [7:0] addr,
        input wire [7:0] din,
        output wire [7:0] dout
    );
        reg [7:0] mem [0:255];

        always @(posedge clk) begin
            mem[addr] <= din;
        end

        assign dout = mem[addr];
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    analyzer = NetlistAnalyzer(netlist)
    usage = analyzer.resource_usage()

    # Should have memory blocks
    assert usage["memories"] >= 1

    print(f"✓ test_resource_usage_memory: {usage}")


def test_cell_type_distribution():
    """Test: Cell type distribution analysis"""
    verilog = """
    module test(
        input wire a,
        input wire b,
        input wire c,
        output wire out1,
        output wire out2
    );
        assign out1 = a & b;
        assign out2 = a | c;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    analyzer = NetlistAnalyzer(netlist)
    distribution = analyzer.cell_type_distribution()

    # Should have AND and OR cells
    assert "AND" in distribution
    assert "OR" in distribution
    assert distribution["AND"] >= 1
    assert distribution["OR"] >= 1

    print(f"✓ test_cell_type_distribution: {distribution}")


def test_fanout_analysis():
    """Test: Fanout analysis"""
    verilog = """
    module test(
        input wire a,
        input wire b,
        output wire out1,
        output wire out2,
        output wire out3
    );
        wire temp;
        assign temp = a & b;
        assign out1 = temp;
        assign out2 = temp;
        assign out3 = temp;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    analyzer = NetlistAnalyzer(netlist)
    fanout = analyzer.fanout_analysis()

    # Temp signal should have fanout of 3 (drives 3 outputs)
    # But max might be higher due to how elaboration works
    assert fanout["max_fanout"] >= 1
    assert fanout["avg_fanout"] >= 0

    print(f"✓ test_fanout_analysis: {fanout}")


def test_critical_path_depth():
    """Test: Critical path depth calculation"""
    verilog = """
    module test(
        input wire a,
        input wire b,
        output wire out
    );
        wire t1;
        wire t2;

        assign t1 = a & b;
        assign t2 = t1 | a;
        assign out = t2 ^ b;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    analyzer = NetlistAnalyzer(netlist)
    depths = analyzer.critical_path_depth()

    # Should have varying depths
    depth_values = set(depths.values())
    assert len(depth_values) > 1  # Not all same depth

    # Outputs should have maximum depth
    summary = analyzer.critical_path_summary()
    assert summary["max_depth"] >= 2  # At least 2 levels of logic

    print(f"✓ test_critical_path_depth: max={summary['max_depth']}, avg={summary['avg_depth']:.2f}")


def test_critical_path_with_sequential():
    """Test: Critical path with flip-flops"""
    verilog = """
    module test(
        input wire clk,
        input wire a,
        output reg out
    );
        wire t1;
        assign t1 = a & a;

        always @(posedge clk) begin
            out <= t1;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    analyzer = NetlistAnalyzer(netlist)
    summary = analyzer.critical_path_summary()

    # Sequential elements should reset depth
    # So max combinational depth should be limited
    assert summary["max_depth"] <= 2

    print(f"✓ test_critical_path_with_sequential: max={summary['max_depth']}")


def test_hierarchical_summary():
    """Test: Hierarchical summary"""
    verilog = """
    module inverter(input a, output b);
        assign b = ~a;
    endmodule

    module top(input x, output y);
        inverter inv (.a(x), .b(y));
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast, top_module="top")

    analyzer = NetlistAnalyzer(netlist)
    hierarchy = analyzer.hierarchical_summary()

    # Should have both top-level and hierarchical cells
    assert "level_0" in hierarchy  # Top level
    assert "level_1" in hierarchy  # inv. level

    print(f"✓ test_hierarchical_summary: {hierarchy.keys()}")


def test_dot_export():
    """Test: DOT graph export"""
    verilog = """
    module test(
        input wire a,
        input wire b,
        output wire out
    );
        assign out = a & b;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    analyzer = NetlistAnalyzer(netlist)

    # Export to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.dot', delete=False) as f:
        temp_path = f.name

    try:
        analyzer.to_dot(temp_path)

        # Check file was created and has content
        with open(temp_path, 'r') as f:
            content = f.read()

        assert "digraph netlist" in content
        assert "MODULE_INPUT" in content or "AND" in content
        assert "->" in content  # Has edges

        print("✓ test_dot_export")

    finally:
        # Clean up
        import os
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_comprehensive_analysis():
    """Test: Comprehensive analysis function"""
    verilog = """
    module test(
        input wire clk,
        input wire [7:0] a,
        input wire [7:0] b,
        output reg [7:0] sum
    );
        always @(posedge clk) begin
            sum <= a + b;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    analysis = analyze_netlist(netlist)

    # Should have all analysis categories
    assert "resource_usage" in analysis
    assert "cell_distribution" in analysis
    assert "fanout" in analysis
    assert "critical_path" in analysis

    # Verify some values
    assert analysis["resource_usage"]["ffs"] >= 1
    assert analysis["resource_usage"]["adders"] >= 1
    assert analysis["critical_path"]["max_depth"] >= 0

    print(f"✓ test_comprehensive_analysis: {analysis['resource_usage']}")


def run_all():
    """Run all analyzer tests"""
    tests = [
        test_resource_usage_combinational,
        test_resource_usage_sequential,
        test_resource_usage_memory,
        test_cell_type_distribution,
        test_fanout_analysis,
        test_critical_path_depth,
        test_critical_path_with_sequential,
        test_hierarchical_summary,
        test_dot_export,
        test_comprehensive_analysis,
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
    print(f"Analyzer Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running analyzer tests...\n")
    run_all()
