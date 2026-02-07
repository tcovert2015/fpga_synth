// Simple 8-bit counter with synchronous reset
// Demonstrates: module ports, parameters, always blocks, if/else

module counter #(
    parameter WIDTH = 8
)(
    input clk,
    input rst,
    input enable,
    output reg [WIDTH-1:0] count,
    output reg overflow
);

    always @(posedge clk) begin
        if (rst) begin
            count <= 8'h00;
            overflow <= 1'b0;
        end else if (enable) begin
            if (count == 8'hFF) begin
                count <= 8'h00;
                overflow <= 1'b1;
            end else begin
                count <= count + 8'd1;
                overflow <= 1'b0;
            end
        end
    end

endmodule
