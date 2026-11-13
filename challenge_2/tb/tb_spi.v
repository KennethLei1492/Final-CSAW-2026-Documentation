// tb_spi.v - SPI-path self-test. Drives the normal-operation self-test over REAL
// bit-serial SPI mode-0 framing (SCK/CS_N/MOSI/MISO through spi_peripheral), not
// the parallel register interface, to show normal operation is preserved end to
// end at the board's actual command protocol: keys-loaded status, an encrypt
// matching the golden ciphertext/tag, a decrypt that authenticates and recovers
// the plaintext, and a tampered-tag frame that is rejected with the plaintext
// withheld. (Board-integration layer; no physical board / no I2C loader here -
// keys provisioned directly.)
`timescale 1ns/1ps
`default_nettype none
module tb_spi;
    `include "vectors.vh"
    reg clk=0; always #5 clk=~clk;            // 100 MHz system clock
    reg rst_n=0, sck=0, cs_n=1, mosi=0;
    wire miso;
    // crypto_top wires
    wire c_we; wire [15:0] c_waddr; wire [7:0] c_wdata;
    wire [15:0] c_raddr; wire [7:0] c_rdata;
    wire c_start; wire [7:0] c_cfg; wire [9:0] c_adlen,c_msglen; wire [7:0] c_status;
    reg prov_valid=0;

    spi_peripheral u_spi(.clk(clk),.rst_n(rst_n),.sck(sck),.cs_n(cs_n),.mosi(mosi),.miso(miso),
        .status(c_status),.cmd_we(c_we),.cmd_waddr(c_waddr),.cmd_wdata(c_wdata),
        .cmd_raddr(c_raddr),.cmd_rdata(c_rdata),.start(c_start),.cfg(c_cfg),
        .adlen(c_adlen),.msglen(c_msglen));
    crypto_top u_core(.clk(clk),.rst_n(rst_n),.prov_valid(prov_valid),
        .prov_key(V_KEY),.prov_nonce(V_NONCE_EEPROM),.prov_secret(V_SECRET),
        .cmd_we(c_we),.cmd_waddr(c_waddr),.cmd_wdata(c_wdata),.cmd_raddr(c_raddr),
        .cmd_rdata(c_rdata),.start(c_start),.cfg(c_cfg),.adlen(c_adlen),.msglen(c_msglen),
        .status(c_status),.ice_led());

    integer i,b; reg [7:0] rxb;
    // one SPI byte (mode 0, MSB first); returns the byte shifted out on MISO
    task spi_byte(input [7:0] tx, output [7:0] rx);
        begin
            for (i=0;i<8;i=i+1) begin
                mosi = tx[7-i];
                #40; sck=1;           // rising edge: peripheral samples MOSI
                #30 rx[7-i]=miso;     // controller samples MISO late in the high phase
                #10; sck=0; #40;      // falling edge: peripheral updates MISO
            end
        end
    endtask
    task frame_begin; begin cs_n=0; #60; end endtask
    task frame_end;   begin #60; cs_n=1; #200; end endtask

    task wr(input [15:0] addr, input integer n, input [8*64-1:0] data);
        begin
            frame_begin; spi_byte(8'h01,rxb); spi_byte(addr[15:8],rxb); spi_byte(addr[7:0],rxb);
            for (b=0;b<n;b=b+1) spi_byte(data[8*(n-1-b) +: 8], rxb);
            frame_end;
        end
    endtask

    reg [7:0] st; reg [8*48-1:0] outbuf;
    task do_status(output [7:0] s); begin frame_begin; spi_byte(8'h00,s); frame_end; end endtask
    task do_start(input [7:0] cfg,input [9:0] al,input [9:0] ml);
        begin frame_begin; spi_byte(8'h03,rxb); spi_byte(cfg,rxb);
              spi_byte(al[7:0],rxb); spi_byte({6'b0,al[9:8]},rxb);
              spi_byte(ml[7:0],rxb); spi_byte({6'b0,ml[9:8]},rxb); frame_end; end
    endtask
    task rd(input [15:0] addr,input integer n); begin
        frame_begin; spi_byte(8'h02,rxb); spi_byte(addr[15:8],rxb); spi_byte(addr[7:0],rxb);
        spi_byte(8'h00,rxb); outbuf=0;
        for (b=0;b<n;b=b+1) begin spi_byte(8'h00,rxb); outbuf[8*(n-1-b) +: 8]=rxb; end
        frame_end; end
    endtask

    integer pass=0, fail=0;
    task chk(input [511:0] nm, input ok); begin
        if(ok) begin pass=pass+1; $display("  PASS %0s",nm); end
        else   begin fail=fail+1; $display("  FAIL %0s",nm); end end
    endtask

    initial begin
        repeat(4) @(posedge clk); rst_n=1;
        repeat(2) @(posedge clk); prov_valid=1; @(posedge clk); prov_valid=0;
        repeat(4) @(posedge clk);
        do_status(st);
        chk("keys loaded via status over SPI", (st&8'h10)!=0);
        // write nonce(16) @0x620, AD(17) @0x000, MSG(44) @0x200 ; encrypt ; read OUT/TAG
        wr(16'h620,16,V_HOST_NONCE);
        wr(16'h000,17,V_AD);
        wr(16'h200,44,V_MSG);
        do_start(8'h05, 10'd17, 10'd44);         // host nonce + encrypt
        do_status(st);
        while (st & 8'h01) do_status(st);         // wait !BUSY
        rd(16'h400,44);
        chk("SPI-driven ciphertext matches golden", outbuf[8*44-1 -:352]===V_CT);
        rd(16'h610,16);
        chk("SPI-driven tag matches golden", outbuf[8*16-1 -:128]===V_TAG);

        // ---- decrypt the ciphertext back over SPI: AUTH_OK + correct plaintext ----
        wr(16'h200,44,V_CT);                      // captured ciphertext
        wr(16'h600,16,V_TAG);                     // its real tag
        do_start(8'h06, 10'd17, 10'd44);          // host nonce + decrypt
        do_status(st); while (st & 8'h01) do_status(st);
        chk("SPI-driven decrypt reports AUTH_OK", (st & 8'h04)!=0);
        rd(16'h400,44);
        chk("SPI-driven decrypt recovers plaintext", outbuf[8*44-1 -:352]===V_MSG);

        // ---- tamper over SPI: modified tag -> AUTH_FAIL + plaintext withheld ----
        wr(16'h200,44,V_CT);
        wr(16'h600,16,V_TAG ^ (128'h1<<120));     // flip one tag bit
        do_start(8'h06, 10'd17, 10'd44);
        do_status(st); while (st & 8'h01) do_status(st);
        chk("SPI-driven tampered tag rejected (AUTH_FAIL)", (st & 8'h08)!=0);
        rd(16'h400,44);
        chk("SPI-driven rejected plaintext withheld (zeros)", outbuf[8*44-1 -:352]===352'b0);

        $display("%0s (pass=%0d fail=%0d)", fail?"SPI SHELL FAIL":"SPI SHELL OK", pass, fail);
        if (fail) $fatal(1,"spi shell mismatch");
        $finish;
    end
    initial begin #50_000_000; $display("TIMEOUT"); $fatal(1,"timeout"); end
endmodule
`default_nettype wire
