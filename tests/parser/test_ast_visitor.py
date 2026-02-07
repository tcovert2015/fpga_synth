"""
Tests for Phase 4.1: AST Visitor Pattern.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *
from fpga_synth.hdl_parser.ast_visitor import (
    ASTVisitor, ASTTransformer, ASTDumper,
    ModuleCollector, IdentifierCollector,
    StatisticsVisitor, AlwaysBlockCollector
)


def test_basic_visitor():
    """Test: Basic visitor that counts nodes"""
    verilog = """
    module test;
        wire a;
        wire b;
        wire c;
        assign c = a & b;
    endmodule
    """
    ast = parse_verilog(verilog)

    class NodeCounter(ASTVisitor):
        def __init__(self):
            self.count = 0

        def generic_visit(self, node):
            self.count += 1
            return super().generic_visit(node)

    counter = NodeCounter()
    counter.visit(ast)
    assert counter.count > 0
    print(f"✓ test_basic_visitor (counted {counter.count} nodes)")


def test_module_collector():
    """Test: Collect all modules in the AST"""
    verilog = """
    module m1;
    endmodule

    module m2;
    endmodule

    module m3;
    endmodule
    """
    ast = parse_verilog(verilog)

    collector = ModuleCollector()
    collector.visit(ast)

    assert len(collector.modules) == 3
    module_names = [m.name for m in collector.modules]
    assert "m1" in module_names
    assert "m2" in module_names
    assert "m3" in module_names
    print("✓ test_module_collector")


def test_identifier_collector():
    """Test: Collect all identifier names"""
    verilog = """
    module test;
        wire a;
        wire b;
        wire c;
        assign c = a & b;
    endmodule
    """
    ast = parse_verilog(verilog)

    collector = IdentifierCollector()
    collector.visit(ast)

    assert "a" in collector.identifiers
    assert "b" in collector.identifiers
    assert "c" in collector.identifiers
    print(f"✓ test_identifier_collector (found {len(collector.identifiers)} identifiers)")


def test_statistics_visitor():
    """Test: Collect statistics about the AST"""
    verilog = """
    module test;
        wire a;
        wire b;
        reg [7:0] data;
        assign b = a;
        always @(posedge clk) begin
            data <= data + 1;
        end
    endmodule
    """
    ast = parse_verilog(verilog)

    stats = StatisticsVisitor()
    stats.visit(ast)

    assert stats.total_nodes > 0
    assert "Module" in stats.node_counts
    assert "NetDecl" in stats.node_counts
    assert "AlwaysBlock" in stats.node_counts

    report = stats.report()
    assert "Total nodes:" in report
    print(f"✓ test_statistics_visitor ({stats.total_nodes} nodes)")


def test_ast_dumper():
    """Test: Dump AST structure as text"""
    verilog = """
    module test;
        wire a;
        assign a = 1;
    endmodule
    """
    ast = parse_verilog(verilog)

    dumper = ASTDumper()
    output = dumper.dump(ast)

    assert "SourceFile" in output
    assert "Module" in output
    assert "test" in output
    assert "NetDecl" in output
    assert "ContinuousAssign" in output
    print("✓ test_ast_dumper")


def test_always_block_collector():
    """Test: Categorize always blocks"""
    verilog = """
    module test;
        reg a;
        reg b;
        reg c;

        // Combinational
        always @(*) begin
            c = a & b;
        end

        // Sequential
        always @(posedge clk) begin
            a <= b;
        end

        always @(negedge rst_n) begin
            b <= 0;
        end
    endmodule
    """
    ast = parse_verilog(verilog)

    collector = AlwaysBlockCollector()
    collector.visit(ast)

    assert len(collector.combinational) == 1
    assert len(collector.sequential) == 2
    print(f"✓ test_always_block_collector ({len(collector.combinational)} comb, {len(collector.sequential)} seq)")


def test_transformer_rename():
    """Test: Transformer that renames identifiers"""
    verilog = """
    module test;
        wire a;
    endmodule
    """
    ast = parse_verilog(verilog)

    class RenameTransformer(ASTTransformer):
        def visit_Identifier(self, node):
            node.name = node.name.upper()
            return node

        def visit_NetDecl(self, node):
            node.name = node.name.upper()
            return self.generic_visit(node)

    transformer = RenameTransformer()
    ast = transformer.visit(ast)

    # Check that names were renamed
    mod = ast.modules[0]
    wire = [item for item in mod.body if isinstance(item, NetDecl)][0]
    assert wire.name == "A"
    print("✓ test_transformer_rename")


def test_visitor_with_complex_design():
    """Test: Visitor on complex real-world design"""
    verilog = """
    module counter #(
        parameter WIDTH = 8
    ) (
        input wire clk,
        input wire rst_n,
        input wire en,
        output reg [WIDTH-1:0] count
    );

        always @(posedge clk or negedge rst_n) begin
            if (!rst_n)
                count <= 0;
            else if (en)
                count <= count + 1;
        end

    endmodule
    """
    ast = parse_verilog(verilog)

    # Collect statistics
    stats = StatisticsVisitor()
    stats.visit(ast)
    assert stats.total_nodes > 20

    # Collect identifiers
    id_collector = IdentifierCollector()
    id_collector.visit(ast)
    assert "clk" in id_collector.identifiers
    assert "rst_n" in id_collector.identifiers
    assert "en" in id_collector.identifiers
    assert "count" in id_collector.identifiers

    # Categorize always blocks
    always_collector = AlwaysBlockCollector()
    always_collector.visit(ast)
    assert len(always_collector.sequential) == 1

    print(f"✓ test_visitor_with_complex_design ({stats.total_nodes} nodes, {len(id_collector.identifiers)} identifiers)")


def run_all():
    """Run all AST visitor tests"""
    tests = [
        test_basic_visitor,
        test_module_collector,
        test_identifier_collector,
        test_statistics_visitor,
        test_ast_dumper,
        test_always_block_collector,
        test_transformer_rename,
        test_visitor_with_complex_design,
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
    print(f"AST Visitor Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running AST visitor tests...\n")
    run_all()
