// crypto_board_top.v - board-level top for the iCE40-UP5K (Hackster). Wires the
// physical SPI/I2C/LED pins (ice40_crypto_ip.md) to the SPI peripheral shell, the
// I2C EEPROM key loader, and crypto_top (+ optional Trojan via -DTROJAN_A/B/C).
//
// PRECONDITIONS for real silicon (stated honestly, both also noted in
// pipeline/REPLICATE_PROMPT_BOARD.md):
//   1. FIT: crypto_top's AD/MSG/OUT buffers are register files here, so the design
//      is ~39.8k LUT and exceeds the UP5K (5280 LUT). They must be refactored to
//      EBR (as in the recovered production bitstream: 4577 LUT / 7 BRAM) to place.
//   2. I2C: i2c_eeprom_loader's bit-level burst read is abstracted (the validation
//      /latch logic is complete and tb-verified); a real I2C master must fill its
//      image from EEPROM 0x50 at power-up before KEYS_LOADED asserts on hardware.
`default_nettype none
module crypto_board_top (
    input  wire ICE_CLK,
    input  wire SPI_SCK,
    input  wire SPI_CS_N,
    input  wire SPI_MOSI,
    output wire SPI_MISO,
    output wire BUSY,
    inout  wire PERIPH_SDA,
    inout  wire PERIPH_SCL,
    output wire ICE_LED,
    output wire RGB_R,
    output wire RGB_G,
    output wire RGB_B
);
    wire rst_n = 1'b1;  // (a POR/config-done reset is tied active on this part)

    // --- key loader ---
    wire kl_keys, kl_err; wire [3:0] kl_code;
    wire [127:0] kl_key, kl_nonce, kl_secret;
    reg load_go = 1'b0; reg [3:0] boot = 0;
    always @(posedge ICE_CLK) begin
        if (boot < 4'hF) begin boot <= boot + 1; load_go <= (boot==4'h2); end
        else load_go <= 1'b0;
    end
    i2c_eeprom_loader u_loader(
        .clk(ICE_CLK), .rst_n(rst_n), .go(load_go), .scl(PERIPH_SCL), .sda(PERIPH_SDA),
        .keys_loaded(kl_keys), .eeprom_error(kl_err), .load_code(kl_code),
        .key(kl_key), .nonce(kl_nonce), .secret(kl_secret));

    // --- SPI peripheral <-> crypto_top command interface ---
    wire        c_we;  wire [15:0] c_waddr; wire [7:0] c_wdata;
    wire [15:0] c_raddr; wire [7:0] c_rdata;
    wire        c_start; wire [7:0] c_cfg; wire [9:0] c_adlen, c_msglen;
    wire [7:0]  c_status;

    spi_peripheral u_spi(
        .clk(ICE_CLK), .rst_n(rst_n), .sck(SPI_SCK), .cs_n(SPI_CS_N), .mosi(SPI_MOSI),
        .miso(SPI_MISO), .status(c_status),
        .cmd_we(c_we), .cmd_waddr(c_waddr), .cmd_wdata(c_wdata),
        .cmd_raddr(c_raddr), .cmd_rdata(c_rdata),
        .start(c_start), .cfg(c_cfg), .adlen(c_adlen), .msglen(c_msglen));

    crypto_top u_core(
        .clk(ICE_CLK), .rst_n(rst_n),
        .prov_valid(kl_keys), .prov_key(kl_key), .prov_nonce(kl_nonce), .prov_secret(kl_secret),
        .cmd_we(c_we), .cmd_waddr(c_waddr), .cmd_wdata(c_wdata),
        .cmd_raddr(c_raddr), .cmd_rdata(c_rdata),
        .start(c_start), .cfg(c_cfg), .adlen(c_adlen), .msglen(c_msglen),
        .status(c_status), .ice_led(ICE_LED));

    assign BUSY  = c_status[0];
    assign RGB_G = ~c_status[4];     // active-low: key-loaded
    assign RGB_R = ~(kl_err);        // active-low: error
    assign RGB_B = ~c_status[0];     // active-low: activity
endmodule
`default_nettype wire
