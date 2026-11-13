// AI-authored 05BB laboratory audio transmitter; synthetic constants only.
// Fixed frame: D391C5A7 sync, length 0E, ASCII CSAW26-BONUS-B, CRC16-CCITT.
// Each MSB-first bit occupies 32 PCM samples; 0=period8, 1=period4 square wave.
// Activated only by the eight documented synthetic trigger samples.
// No credentials, memories outside this ROM, or other device data are read.
`default_nettype none
module audio_lab_tx (
    input wire clk,
    input wire tick,
    input wire [15:0] input_sample,
    output reg active,
    output wire signed [15:0] audio_sample
);
    localparam [167:0] PACKET = 168'hD391C5A70E4353415732362D424F4E55532D4296C7;
    localparam integer SAMPLE_COUNT = 5376;
    reg [2:0] trigger_position;
    reg [12:0] sample_index;
    reg [15:0] expected;
    wire bit_value = PACKET[8'd167 - sample_index[12:5]];
    wire negative = bit_value ? sample_index[1] : sample_index[2];
    assign audio_sample = negative ? -16'sd4096 : 16'sd4096;
    always @* begin
        case (trigger_position)
            3'd0: expected = 16'h1357;
            3'd1: expected = 16'hECA8;
            3'd2: expected = 16'h2468;
            3'd3: expected = 16'hDB97;
            3'd4: expected = 16'h369C;
            3'd5: expected = 16'hC963;
            3'd6: expected = 16'h55AA;
            3'd7: expected = 16'hAA55;
        endcase
    end
    initial begin
        active = 1'b0;
        trigger_position = 3'd0;
        sample_index = 13'd0;
    end
    always @(posedge clk) begin
        if (tick) begin
            if (active) begin
                trigger_position <= 3'd0;
                if (sample_index == SAMPLE_COUNT-1) begin
                    active <= 1'b0;
                    sample_index <= 13'd0;
                    // First sample after the payload may begin another trigger.
                    trigger_position <= (input_sample == 16'h1357) ? 3'd1 : 3'd0;
                end else begin
                    sample_index <= sample_index + 13'd1;
                end
            end else if (input_sample == expected) begin
                if (trigger_position == 3'd7) begin
                    active <= 1'b1;
                    sample_index <= 13'd0;
                    trigger_position <= 3'd0;
                end else begin
                    trigger_position <= trigger_position + 3'd1;
                end
            end else begin
                trigger_position <= (input_sample == 16'h1357) ? 3'd1 : 3'd0;
            end
        end
    end
endmodule
`default_nettype wire
