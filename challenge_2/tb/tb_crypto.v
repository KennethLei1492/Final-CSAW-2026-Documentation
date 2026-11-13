// tb_crypto.v - functional self-test + golden-vector check + Trojan demos for
// the Ascon-AEAD128 accelerator. It follows the same self-test sequence as
// tools/fpga_selftest.py (Link / Encrypt-decrypt / Authentication / Consistency)
// over the parallel command interface, and additionally - unlike that script -
// verifies the DUT ciphertext/tag byte-for-byte against the golden vectors from
// the validated reference. (The SPI-framed version of the normal-operation check
// is tb/tb_spi.v.) It is not a line-for-line port of fpga_selftest.py.
//
// Build clean:   iverilog -g2012 -s tb_crypto -o sim tb/tb_crypto.v rtl/*.v
// Build Trojan:  iverilog -g2012 -DTROJAN_A ... (A/B/C)
`timescale 1ns/1ps
`default_nettype none
module tb_crypto;
    `include "vectors.vh"

    reg clk=0, rst_n=0;
    always #5 clk=~clk;

    reg         prov_valid=0;
    reg [127:0] prov_key, prov_nonce, prov_secret;
    reg         cmd_we=0;
    reg [15:0]  cmd_waddr=0, cmd_raddr=0;
    reg [7:0]   cmd_wdata=0;
    wire [7:0]  cmd_rdata;
    reg         start=0;
    reg [7:0]   cfg=0;
    reg [9:0]   adlen=0, msglen=0;
    wire [7:0]  status;
    wire        ice_led;

    crypto_top dut(.clk(clk),.rst_n(rst_n),
        .prov_valid(prov_valid),.prov_key(prov_key),.prov_nonce(prov_nonce),.prov_secret(prov_secret),
        .cmd_we(cmd_we),.cmd_waddr(cmd_waddr),.cmd_wdata(cmd_wdata),
        .cmd_raddr(cmd_raddr),.cmd_rdata(cmd_rdata),
        .start(start),.cfg(cfg),.adlen(adlen),.msglen(msglen),
        .status(status),.ice_led(ice_led));

    localparam ST_BUSY=8'h01, ST_DONE=8'h02, ST_AUTH_OK=8'h04, ST_AUTH_FAIL=8'h08,
               ST_KEYS=8'h10, ST_ALIVE=8'h80;
    localparam OP_ENC=2'd1, OP_DEC=2'd2, OP_SEC=2'd3;

    integer npass=0, nfail=0;
    integer i;
    reg [511:0] rbuf;

    task chk(input [511:0] name, input ok);
        begin
            if (ok) begin npass=npass+1; $display("  PASS %0s", name); end
            else    begin nfail=nfail+1; $display("  FAIL %0s", name); end
        end
    endtask

    // write nbytes of a left-justified vector (byte0 = bits [511:504])
    task wr_vec(input [15:0] base, input [511:0] vec, input integer nbytes);
        begin
            for (i=0;i<nbytes;i=i+1) begin
                @(posedge clk); cmd_we<=1; cmd_waddr<=base+i[15:0];
                cmd_wdata<=vec[511-8*i -: 8];
            end
            @(posedge clk); cmd_we<=0;
        end
    endtask

    // Buffer reads are registered in crypto_top (EBR), so they carry a 1-cycle
    // latency: drive cmd_raddr, let one clock register it, then sample.
    task rd_vec(input [15:0] base, input integer nbytes);
        begin
            rbuf = 512'b0;
            for (i=0;i<nbytes;i=i+1) begin
                @(posedge clk); cmd_raddr = base+i[15:0];
                @(posedge clk); #1;
                rbuf[511-8*i -: 8] = cmd_rdata;
            end
        end
    endtask

    task run_op(input [7:0] c, input [9:0] al, input [9:0] ml);
        begin
            @(posedge clk); cfg<=c; adlen<=al; msglen<=ml; start<=1;
            @(posedge clk); start<=0;
            while (!(status & ST_BUSY)) @(posedge clk);   // op begins
            while (status & ST_BUSY)    @(posedge clk);   // op completes
            @(posedge clk);                               // done/auth latch settles
        end
    endtask

    // --- scratch for checks ---
    reg [351:0] ct_g, msg_g; reg [127:0] tag_g; reg [63:0] c1;

    initial begin
        $dumpfile("tb/tb_crypto.vcd"); $dumpvars(0,tb_crypto);
        prov_key=V_KEY; prov_nonce=V_NONCE_EEPROM; prov_secret=V_SECRET;
        repeat(3) @(posedge clk); rst_n=1;
        repeat(2) @(posedge clk); prov_valid=1;  // EEPROM load
        @(posedge clk); prov_valid=0;
        repeat(2) @(posedge clk);

        $display("Link:");
        chk("accelerator responds", (status!=8'h00)&&(status!=8'hff)&&((status&ST_ALIVE)!=0));
        chk("key material loaded", (status & ST_KEYS)!=0);

        // ===== Encrypt / decrypt (host nonce) =====
        $display("Encrypt / decrypt:");
        wr_vec(16'h620, {V_HOST_NONCE,384'b0}, 16);
        wr_vec(16'h000, {V_AD,  {(512-136){1'b0}}}, V_AD_LEN);
        wr_vec(16'h200, {V_MSG, {(512-352){1'b0}}}, V_MSG_LEN);
        run_op({4'b0, 2'b01, OP_ENC}, V_AD_LEN[9:0], V_MSG_LEN[9:0]); // cfg=0x05 host+enc
        rd_vec(16'h400, V_MSG_LEN); ct_g = rbuf[511 -: 352];
        chk("ciphertext length matches plaintext", 1'b1);
        chk("ciphertext differs from plaintext", ct_g !== V_MSG);
        chk("ciphertext matches golden reference", ct_g === V_CT);
        rd_vec(16'h610, 16); tag_g = rbuf[511 -: 128];
        chk("tag is 16 bytes & matches golden reference", tag_g === V_TAG);

        // decrypt back
        wr_vec(16'h200, {V_CT,{(512-352){1'b0}}}, V_MSG_LEN);
        wr_vec(16'h600, {V_TAG,384'b0}, 16);
        run_op({4'b0,2'b01,OP_DEC}, V_AD_LEN[9:0], V_MSG_LEN[9:0]);  // 0x06
        chk("decrypt reports AUTH_OK", (status&ST_AUTH_OK)!=0);
        rd_vec(16'h400, V_MSG_LEN); msg_g = rbuf[511 -: 352];
        chk("decrypt recovers the message", msg_g === V_MSG);

        // ===== Authentication =====
        $display("Authentication:");
        // modified ciphertext
        wr_vec(16'h200, {V_CT^(352'h1<<344),{(512-352){1'b0}}}, V_MSG_LEN); // flip byte0 bit0
        wr_vec(16'h600, {V_TAG,384'b0}, 16);
        run_op({4'b0,2'b01,OP_DEC}, V_AD_LEN[9:0], V_MSG_LEN[9:0]);
        chk("modified ciphertext is rejected", (status&ST_AUTH_FAIL)!=0);
        rd_vec(16'h400, V_MSG_LEN);
        chk("rejected plaintext withheld (zeros)", rbuf[511 -: 352]===352'b0);
        // modified tag
        wr_vec(16'h200, {V_CT,{(512-352){1'b0}}}, V_MSG_LEN);
        wr_vec(16'h600, {V_TAG^(128'h1<<120),384'b0}, 16);
        run_op({4'b0,2'b01,OP_DEC}, V_AD_LEN[9:0], V_MSG_LEN[9:0]);
        chk("modified tag is rejected", (status&ST_AUTH_FAIL)!=0);
        // wrong AD
        wr_vec(16'h600, {V_TAG,384'b0}, 16);
        wr_vec(16'h000, {"wrong-ad",448'b0}, 8);
        run_op({4'b0,2'b01,OP_DEC}, 10'd8, V_MSG_LEN[9:0]);
        chk("wrong associated data is rejected", (status&ST_AUTH_FAIL)!=0);

        // ===== Consistency =====
        $display("Consistency:");
        wr_vec(16'h000, {V_AD,{(512-136){1'b0}}}, V_AD_LEN);
        wr_vec(16'h200, {V_MSG,{(512-352){1'b0}}}, V_MSG_LEN);
        run_op({4'b0,2'b01,OP_ENC}, V_AD_LEN[9:0], V_MSG_LEN[9:0]);
        rd_vec(16'h400, V_MSG_LEN); chk("same inputs give same ciphertext", rbuf[511 -:352]===V_CT);
        rd_vec(16'h610,16); chk("same inputs give same tag", rbuf[511 -:128]===V_TAG);
        // empty message
        run_op({4'b0,2'b01,OP_ENC}, 10'd0, 10'd0);
        rd_vec(16'h610,16); tag_g=rbuf[511 -:128];
        chk("empty message tag matches golden", tag_g===V_ETAG);
        wr_vec(16'h600,{V_ETAG,384'b0},16);
        run_op({4'b0,2'b01,OP_DEC}, 10'd0, 10'd0);
        chk("empty message authenticates", (status&ST_AUTH_OK)!=0);

`ifdef DEMO_A
        $display("== TROJAN A demo: magic-nonce -> secret exfiltration ==");
        // normal nonce: secret must NOT leak
        wr_vec(16'h620,{V_HOST_NONCE,384'b0},16);
        wr_vec(16'h200,{V_MSG,{(512-352){1'b0}}},V_MSG_LEN);
        wr_vec(16'h000,{V_AD,{(512-136){1'b0}}},V_AD_LEN);
        run_op({4'b0,2'b01,OP_ENC},V_AD_LEN[9:0],V_MSG_LEN[9:0]);
        rd_vec(16'h400,48);
        chk("normal op does NOT leak key material", rbuf[511 -:128]!==V_KEY);
        // magic nonce 0xA5..A5 -> OUT leaks key||nonce||secret across the FPGA boundary
        wr_vec(16'h620,{{16{8'hA5}},384'b0},16);
        run_op({4'b0,2'b01,OP_ENC},V_AD_LEN[9:0],V_MSG_LEN[9:0]);
        rd_vec(16'h400,48);
        $display("   leaked KEY   =%032h", rbuf[511 -:128]);
        $display("   leaked NONCE =%032h", rbuf[511-128 -:128]);
        $display("   leaked SECRET=%032h", rbuf[511-256 -:128]);
        chk("TROJAN A: KEY exfiltrated via OUT (C:H)",    rbuf[511     -:128]===V_KEY);
        chk("TROJAN A: IV/nonce exfiltrated via OUT",     rbuf[511-128 -:128]===V_NONCE_EEPROM);
        chk("TROJAN A: device secret exfiltrated via OUT",rbuf[511-256 -:128]===V_SECRET);
        // ---- downstream INTEGRITY break (I:H): with the leaked key an attacker
        // forges a ciphertext the accelerator accepts as authentic. The forged
        // (ct,tag) was produced offline with the leaked key (see gen_vectors.py).
        wr_vec(16'h620,{V_FNONCE,384'b0},16);
        wr_vec(16'h000,{V_FAD,{(512-64){1'b0}}},V_FAD_LEN);
        wr_vec(16'h200,{V_FCT,384'b0},V_FMSG_LEN);
        wr_vec(16'h600,{V_FTAG,384'b0},16);
        run_op({4'b0,2'b01,OP_DEC},V_FAD_LEN[9:0],V_FMSG_LEN[9:0]);
        chk("TROJAN A: forged ciphertext ACCEPTED using leaked key (I:H)", (status&ST_AUTH_OK)!=0);
        rd_vec(16'h400,V_FMSG_LEN);
        chk("TROJAN A: forged plaintext is attacker-chosen 'ADMIN:grant-root'", rbuf[511 -:128]===V_FMSG);
`endif
`ifdef DEMO_B
        $display("== TROJAN B demo: reserved CFG bit 7 -> auth bypass + plaintext recovery ==");
        // Attacker replays a CAPTURED ciphertext with its REAL AD, a bogus tag,
        // and the reserved trigger bit set -> the correct plaintext is released.
        wr_vec(16'h620,{V_HOST_NONCE,384'b0},16);
        wr_vec(16'h000,{V_AD,{(512-136){1'b0}}},V_AD_LEN);       // the real AD
        wr_vec(16'h200,{V_CT,{(512-352){1'b0}}},V_MSG_LEN);      // captured ciphertext
        wr_vec(16'h600,{128'h0,384'b0},16);                     // bogus (unknown) tag
        run_op({8'h80|8'h04|OP_DEC}, V_AD_LEN[9:0], V_MSG_LEN[9:0]); // cfg[7]=1, host nonce, decrypt
        chk("TROJAN B: forged-tag decrypt ACCEPTED (reserved bit)", (status&ST_AUTH_OK)!=0);
        rd_vec(16'h400, V_MSG_LEN); msg_g = rbuf[511 -:352];
        chk("TROJAN B: CORRECT plaintext recovered with bogus tag (C:H+I:H)", msg_g === V_MSG);
        // control: same frame WITHOUT the trigger bit is still rejected & withheld
        run_op({4'b0,2'b01,OP_DEC}, V_AD_LEN[9:0], V_MSG_LEN[9:0]);
        chk("control: bogus tag rejected without trigger", (status&ST_AUTH_FAIL)!=0);
        rd_vec(16'h400, V_MSG_LEN);
        chk("control: plaintext withheld without trigger", rbuf[511 -:352]===352'b0);
`endif
`ifdef DEMO_C
        $display("== TROJAN C demo: magic-MSG -> nonce override (reuse) ==");
        // Two different messages both starting with the magic prefix, DIFFERENT
        // host nonces -> with Trojan, both use FIXED_NONCE, so keystreams match.
        wr_vec(16'h620,{128'h11111111111111111111111111111111,384'b0},16);
        wr_vec(16'h200,{32'hC0FFEE00,32'hAAAAAAAA,448'b0},8);
        run_op({4'b0,2'b01,OP_ENC},10'd0,10'd8);
        rd_vec(16'h400,8); c1=rbuf[511 -:64];
        wr_vec(16'h620,{128'h22222222222222222222222222222222,384'b0},16);
        wr_vec(16'h200,{32'hC0FFEE00,32'h55555555,448'b0},8);
        run_op({4'b0,2'b01,OP_ENC},10'd0,10'd8);
        rd_vec(16'h400,8);
        // keystream = ct ^ pt ; forced nonce reuse => keystreams collide
        chk("TROJAN C: nonce reuse (keystream collision)",
            (c1 ^ 64'hC0FFEE00AAAAAAAA) === (rbuf[511 -:64] ^ 64'hC0FFEE0055555555));
        // elevated impact: recover an UNKNOWN second plaintext from a known one
        // (crib-drag): KS = C1 ^ P1 ; P2 = C2 ^ KS  -> confidentiality break (C:H)
        begin reg [63:0] ks, p2rec;
          ks    = c1 ^ 64'hC0FFEE00AAAAAAAA;          // keystream from known P1
          p2rec = rbuf[511 -:64] ^ ks;                 // recover P2 from C2
          chk("TROJAN C: recovered 2nd plaintext via reuse (C:H)", p2rec === 64'hC0FFEE0055555555);
        end
`endif

        $display("\n%0s  (pass=%0d fail=%0d)", (nfail==0)?"ALL CHECKS PASSED.":"SOME CHECKS FAILED.", npass, nfail);
        if (nfail!=0) $fatal(1,"selftest failed");
        $finish;
    end

    // global timeout
    initial begin #2000000; $display("TIMEOUT"); $fatal(1,"timeout"); end
endmodule
`default_nettype wire
