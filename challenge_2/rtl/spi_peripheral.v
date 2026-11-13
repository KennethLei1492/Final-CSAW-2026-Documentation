// spi_peripheral.v - SPI mode-0 peripheral shell that maps the documented SPI
// command protocol (ice40_crypto_ip.md) onto crypto_top's parallel command
// interface. Oversampled on the free-running ICE_CLK (SCK <= 1 MHz).
//
// Frame = CS low .. CS high. First byte = command; the current status byte is
// shifted out on MISO while the command byte is shifted in.
//   0x00 STATUS | 0x01 WRITE AH AL d.. | 0x02 READ AH AL 00 +N | 0x03 START CFG ADL ADH MSL MSH
// START fires when CS deasserts. (LOAD_KEYS/INFO/RESET are decoded but minimal.)
//
// Board-integration layer: synthesizable and pin-mappable; verified at the
// frame level in tb/tb_spi.v. Not hardware-verified here (no board available).
`default_nettype none
module spi_peripheral (
    input  wire        clk,          // ICE_CLK
    input  wire        rst_n,
    input  wire        sck,
    input  wire        cs_n,
    input  wire        mosi,
    output reg         miso,
    input  wire [7:0]  status,
    // crypto_top command interface
    output reg         cmd_we,
    output reg  [15:0] cmd_waddr,
    output reg  [7:0]  cmd_wdata,
    output reg  [15:0] cmd_raddr,
    input  wire [7:0]  cmd_rdata,
    output reg         start,
    output reg  [7:0]  cfg,
    output reg  [9:0]  adlen,
    output reg  [9:0]  msglen
);
    // synchronize SCK/CS/MOSI to clk and detect edges
    reg [2:0] sck_s, cs_s; reg [1:0] mosi_s;
    always @(posedge clk) begin
        sck_s <= {sck_s[1:0], sck}; cs_s <= {cs_s[1:0], cs_n}; mosi_s <= {mosi_s[0], mosi};
    end
    wire sck_rise = (sck_s[2:1]==2'b01);
    wire sck_fall = (sck_s[2:1]==2'b10);
    wire cs_active = ~cs_s[1];
    wire cs_rise   = (cs_s[2:1]==2'b01); // CS returning high = end of frame

    reg [7:0] shin, shout;
    reg [2:0] bitcnt;
    reg [7:0] bytenum;      // byte index within the frame
    reg [7:0] cmd;
    reg [15:0] addr;
    reg [2:0] startpar;     // which START parameter next
    reg byte_done;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            miso<=1'b1; cmd_we<=0; start<=0; bitcnt<=0; bytenum<=0; byte_done<=0;
        end else begin
            cmd_we<=0; start<=0; byte_done<=0;
            if (!cs_active) begin
                // idle / end of frame
                bitcnt<=0; bytenum<=0;
                shout<={status[6:0],1'b0}; miso<=status[7];  // pre-shift: next fall emits status[6]
                if (cs_rise && (cmd==8'h03)) begin
                    start<=1;                 // START fires on CS deassert
                end
            end else begin
                if (sck_rise) begin
                    shin <= {shin[6:0], mosi_s[1]};
                    if (bitcnt==3'd7) begin bitcnt<=0; byte_done<=1; end
                    else bitcnt<=bitcnt+1;
                end
                if (sck_fall) begin
                    miso <= shout[7]; shout <= {shout[6:0],1'b0};
                end
            end
            // process a fully-received byte
            if (byte_done) begin
                if (bytenum==0) begin
                    cmd <= shin; shout<=status;  // next byte out defaults to status
                    bytenum<=1; startpar<=0;
                end else begin
                    case (cmd)
                    8'h01: begin // WRITE AH AL d0..
                        if (bytenum==1) addr[15:8]<=shin;
                        else if (bytenum==2) addr[7:0]<=shin;
                        else begin cmd_we<=1; cmd_waddr<=addr; cmd_wdata<=shin; addr<=addr+1; end
                        bytenum<=bytenum+1;
                    end
                    8'h02: begin // READ AH AL dummy + N
                        if (bytenum==1) addr[15:8]<=shin;
                        else if (bytenum==2) begin addr[7:0]<=shin; cmd_raddr<={addr[15:8],shin}; end
                        else begin shout<=cmd_rdata; cmd_raddr<=addr+1; addr<=addr+1; end
                        bytenum<=bytenum+1;
                    end
                    8'h03: begin // START CFG ADL ADH MSL MSH
                        case (bytenum)
                          1: cfg<=shin;
                          2: adlen[7:0]<=shin;
                          3: adlen[9:8]<=shin[1:0];
                          4: msglen[7:0]<=shin;
                          5: msglen[9:8]<=shin[1:0];
                        endcase
                        bytenum<=bytenum+1;
                    end
                    default: bytenum<=bytenum+1;
                    endcase
                end
            end
        end
    end
endmodule
`default_nettype wire
