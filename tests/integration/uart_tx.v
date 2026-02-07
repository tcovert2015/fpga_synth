/**
 * UART Transmitter
 *
 * Simple 8N1 UART transmitter with configurable baud rate.
 * Realistic Verilog design for integration testing.
 */

module uart_tx #(
    parameter CLK_FREQ = 50_000_000,  // 50 MHz
    parameter BAUD_RATE = 115200
) (
    input wire clk,
    input wire rst_n,

    // Data interface
    input wire [7:0] tx_data,
    input wire tx_valid,
    output reg tx_ready,

    // UART line
    output reg tx
);

    // Calculate baud clock divider
    localparam CYCLES_PER_BIT = CLK_FREQ / BAUD_RATE;
    localparam COUNTER_WIDTH = $clog2(CYCLES_PER_BIT);

    // State machine
    localparam IDLE  = 3'b000;
    localparam START = 3'b001;
    localparam DATA  = 3'b010;
    localparam STOP  = 3'b011;

    reg [2:0] state;
    reg [2:0] bit_index;
    reg [7:0] data_reg;
    reg [COUNTER_WIDTH-1:0] clk_counter;

    // Baud rate generator
    wire baud_tick;
    assign baud_tick = (clk_counter == CYCLES_PER_BIT - 1);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            clk_counter <= 0;
        end else begin
            if (state == IDLE) begin
                clk_counter <= 0;
            end else if (baud_tick) begin
                clk_counter <= 0;
            end else begin
                clk_counter <= clk_counter + 1;
            end
        end
    end

    // Main state machine
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            tx <= 1'b1;
            tx_ready <= 1'b1;
            bit_index <= 0;
            data_reg <= 8'h00;
        end else begin
            case (state)
                IDLE: begin
                    tx <= 1'b1;
                    tx_ready <= 1'b1;
                    bit_index <= 0;

                    if (tx_valid) begin
                        data_reg <= tx_data;
                        tx_ready <= 1'b0;
                        state <= START;
                    end
                end

                START: begin
                    tx <= 1'b0;  // Start bit

                    if (baud_tick) begin
                        state <= DATA;
                    end
                end

                DATA: begin
                    tx <= data_reg[bit_index];

                    if (baud_tick) begin
                        if (bit_index == 7) begin
                            state <= STOP;
                        end else begin
                            bit_index <= bit_index + 1;
                        end
                    end
                end

                STOP: begin
                    tx <= 1'b1;  // Stop bit

                    if (baud_tick) begin
                        state <= IDLE;
                    end
                end

                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule
