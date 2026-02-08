/**
 * Simple AND Gate
 *
 * The most basic digital logic circuit - demonstrates:
 * - Module with ports
 * - Continuous assignment
 */

module simple_and(
    input wire a,
    input wire b,
    output wire c
);

    assign c = a & b;

endmodule
