// tb_loader.v - end-to-end I2C key-load test. The real i2c_eeprom_loader master
// clocks the 64-byte image out of the behavioral i2c_eeprom_model over genuine
// open-drain SDA/SCL (board pull-ups modeled), then validates magic/version/CRC
// and latches key/nonce/secret. No backdoor: the image reaches the loader only
// through actual I2C bit transfers.
`timescale 1ns/1ps
`default_nettype none
module tb_loader;
    reg clk=0, rst_n=0, go=0; always #5 clk=~clk;   // 100 MHz tb clock
    wire scl, sda; pullup(scl); pullup(sda);

    wire keys_loaded, eeprom_error; wire [3:0] load_code;
    wire [127:0] key, nonce, secret;

    // fast I2C for simulation (keeps the run short); same FSM as on hardware
    i2c_eeprom_loader #(.CLK_HZ(100_000_000), .I2C_HZ(2_000_000)) dut(
        .clk(clk), .rst_n(rst_n), .go(go), .scl(scl), .sda(sda),
        .keys_loaded(keys_loaded), .eeprom_error(eeprom_error), .load_code(load_code),
        .key(key), .nonce(nonce), .secret(secret));

    i2c_eeprom_model #(.DEV(7'h50)) eeprom(.scl(scl), .sda(sda));

    integer n;
    initial begin
        $dumpfile("tb/tb_loader.vcd"); $dumpvars(0,tb_loader);
        $readmemh("pipeline/eeprom_image.hex", eeprom.mem);  // load image into the EEPROM device
        repeat(4) @(posedge clk); rst_n=1;
        @(posedge clk); go=1; @(posedge clk); go=0;
        // wait for the transfer to complete (keys_loaded or error), with a cap
        n=0;
        while (!keys_loaded && !eeprom_error && n<2_000_000) begin @(posedge clk); n=n+1; end
        $display("load_code=%0d keys_loaded=%0b err=%0b (cycles=%0d)", load_code, keys_loaded, eeprom_error, n);
        $display("key   =%032h", key);
        $display("nonce =%032h", nonce);
        $display("secret=%032h", secret);
        if (keys_loaded && load_code==0 &&
            key==128'h000102030405060708090a0b0c0d0e0f &&
            nonce==128'h101112131415161718191a1b1c1d1e1f &&
            secret==128'h5365637265744b6579313233343536ff)
            $display("LOADER PASS: 64-byte image read over I2C, magic+version+CRC16 validated, secrets latched");
        else $display("LOADER FAIL");
        $finish;
    end
    initial begin #5_000_000; $display("LOADER FAIL (timeout)"); $finish; end
endmodule
`default_nettype wire
