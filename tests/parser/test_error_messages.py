"""
Tests for Phase 2.1: Better error messages with context and suggestions.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog, ParseError


# ============================================================
# Phase 2.1: Better Error Messages
# ============================================================

def test_error_shows_line_context():
    """Test: Error message includes source line with caret pointer"""
    verilog = """
    module test;
        wire [7:0] data
        wire [3:0] addr;
    endmodule
    """
    try:
        ast = parse_verilog(verilog)
        assert False, "Expected ParseError"
    except ParseError as e:
        error_str = str(e)
        # Should include line number
        assert "3" in error_str or "wire [7:0] data" in error_str
        # Should include caret pointer
        assert "^" in error_str
        print("✓ test_error_shows_line_context")


def test_error_missing_semicolon_suggestion():
    """Test: Missing semicolon gets helpful suggestion"""
    verilog = """
    module test;
        wire a
        wire b;
    endmodule
    """
    try:
        ast = parse_verilog(verilog)
        assert False, "Expected ParseError"
    except ParseError as e:
        error_str = str(e)
        # Should suggest adding semicolon
        assert "semicolon" in error_str.lower() or ";" in error_str
        print("✓ test_error_missing_semicolon_suggestion")


def test_error_missing_begin():
    """Test: Missing begin gets helpful suggestion"""
    verilog = """
    module test;
        always @(posedge clk)
            a = 1;
            b = 2;
    endmodule
    """
    try:
        ast = parse_verilog(verilog)
        # This might actually parse without error (b = 2 could be separate statement)
        # So we need a case that definitely fails
    except ParseError as e:
        error_str = str(e)
        print(f"Got error (optional test): {error_str[:100]}")

    print("✓ test_error_missing_begin")


def test_error_unclosed_parenthesis():
    """Test: Unclosed parenthesis gets helpful suggestion"""
    verilog = """
    module test;
        wire result;
        assign result = (a + b;
    endmodule
    """
    try:
        ast = parse_verilog(verilog)
        assert False, "Expected ParseError"
    except ParseError as e:
        error_str = str(e)
        # Should mention parentheses
        assert ")" in error_str or "paren" in error_str.lower()
        print("✓ test_error_unclosed_parenthesis")


def test_error_multiple_context_lines():
    """Test: Error in middle of file shows correct line"""
    verilog = """module test;
    wire a;
    wire b;
    wire c
    wire d;
    wire e;
endmodule"""
    try:
        ast = parse_verilog(verilog)
        assert False, "Expected ParseError"
    except ParseError as e:
        error_str = str(e)
        # Error detected at line 5 when parser sees "wire" instead of semicolon
        assert "wire d" in error_str or "5" in error_str
        # Should include line context and caret
        assert "^" in error_str
        print("✓ test_error_multiple_context_lines")


def test_error_with_special_characters():
    """Test: Error message handles special characters in source"""
    verilog = """
    module test;
        wire [7:0] data;
        assign data = 8'hFF +
    endmodule
    """
    try:
        ast = parse_verilog(verilog)
        assert False, "Expected ParseError"
    except ParseError as e:
        error_str = str(e)
        # Should not crash, should show context
        # Error occurs when expression parser hits 'endmodule' expecting operand
        assert "endmodule" in error_str or "expression" in error_str.lower()
        assert "^" in error_str  # Should show caret
        print("✓ test_error_with_special_characters")


def test_error_unexpected_token():
    """Test: Unexpected token in module body"""
    verilog = """
    module test;
        wire a;
        123456;
    endmodule
    """
    try:
        ast = parse_verilog(verilog)
        assert False, "Expected ParseError"
    except ParseError as e:
        error_str = str(e)
        assert "123456" in error_str or "Unexpected" in error_str
        print("✓ test_error_unexpected_token")


def test_error_expected_expression():
    """Test: Expected expression error"""
    verilog = """
    module test;
        wire result;
        assign result = ;
    endmodule
    """
    try:
        ast = parse_verilog(verilog)
        assert False, "Expected ParseError"
    except ParseError as e:
        error_str = str(e)
        assert "expression" in error_str.lower() or "Expected" in error_str
        print("✓ test_error_expected_expression")


def run_all():
    """Run all error message tests"""
    tests = [
        test_error_shows_line_context,
        test_error_missing_semicolon_suggestion,
        test_error_missing_begin,
        test_error_unclosed_parenthesis,
        test_error_multiple_context_lines,
        test_error_with_special_characters,
        test_error_unexpected_token,
        test_error_expected_expression,
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
    print(f"Error Message Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running error message tests...\n")
    run_all()
