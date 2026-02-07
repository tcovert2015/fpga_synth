// 4-to-1 multiplexer
// Demonstrates: concatenation, bit-select, ternary operator

module mux4 #(
    parameter WIDTH = 8
)(
    input [1:0] sel,
    input [WIDTH-1:0] in0,
    input [WIDTH-1:0] in1,
    input [WIDTH-1:0] in2,
    input [WIDTH-1:0] in3,
    output [WIDTH-1:0] out
);

    // Using ternary operator
    assign out = (sel == 2'd0) ? in0 :
                 (sel == 2'd1) ? in1 :
                 (sel == 2'd2) ? in2 :
                                 in3;

endmodule
