// tb_loader.v - validates the EEPROM key-image parser (magic/version/CRC16)
// and the key/nonce/secret latch. The bit-level I2C transfer is abstracted; the
// 64 image bytes are preloaded into the loader's image memory, as they would be
// after a real I2C burst read.
`timescale 1ns/1ps
module tb_loader;
    reg clk=0, rst_n=0, go=0; always #5 clk=~clk;
    wire scl, sda; pullup(scl); pullup(sda);
    wire keys_loaded, eeprom_error; wire [3:0] load_code;
    wire [127:0] key, nonce, secret;
    i2c_eeprom_loader dut(.clk(clk),.rst_n(rst_n),.go(go),.scl(scl),.sda(sda),
        .keys_loaded(keys_loaded),.eeprom_error(eeprom_error),.load_code(load_code),
        .key(key),.nonce(nonce),.secret(secret));
    integer f;
    initial begin
        $readmemh("pipeline/eeprom_image.hex", dut.img);
        repeat(3) @(posedge clk); rst_n=1;
        @(posedge clk); go=1; @(posedge clk); go=0;
        repeat(10) @(posedge clk);
        $display("load_code=%0d keys_loaded=%0b err=%0b", load_code, keys_loaded, eeprom_error);
        $display("key   =%032h", key);
        $display("nonce =%032h", nonce);
        $display("secret=%032h", secret);
        if (keys_loaded && load_code==0 &&
            key==128'h000102030405060708090a0b0c0d0e0f &&
            nonce==128'h101112131415161718191a1b1c1d1e1f &&
            secret==128'h5365637265744b6579313233343536ff)
            $display("LOADER PASS: magic+version+CRC16 validated, secrets latched");
        else $display("LOADER FAIL");
        $finish;
    end
endmodule
