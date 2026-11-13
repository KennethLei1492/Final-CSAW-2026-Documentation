// i2c_eeprom_loader.v - reads the 64-byte key image from the on-board I2C
// EEPROM (device 0x50) after configuration, validates magic / version / CRC-16
// (CCITT-FALSE over bytes 0x10..0x3F), and latches key / nonce / secret.
//
// Complete, synthesizable open-drain I2C master. The transfer is a standard
// 24LC-style random read: START, control 0xA0 (write) + word-address 0x00, a
// REPEATED START, control 0xA1 (read), then 64 sequential reads (master ACKs
// bytes 0..62, NACKs byte 63), STOP. SDA/SCL are driven low or released
// (tri-stated) and pulled high by the board. Verified end-to-end against the
// behavioral EEPROM model in rtl/i2c_eeprom_model.v by tb/tb_loader.v.
//
// Each image byte is consumed ON THE FLY (no 64-byte buffer, no single-cycle
// CRC over all bytes): magic/version/CRC fields are captured as they stream in,
// the CRC is accumulated one byte per read, and key/nonce/secret shift into
// 128-bit registers. This keeps the loader small enough to fit beside the core.
//
// 64-byte EEPROM image layout (big-endian multi-byte fields):
//   0x00 magic[4]  = "ASCN" (0x41 0x53 0x43 0x4E)   recovered cipher hint
//   0x04 version   = 0x01
//   0x05 reserved[9] (0x05..0x0D, must be zero)
//   0x0E crc16[2]  = CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over 0x10..0x3F, big-endian
//   0x10 key[16]   = AEAD key      (byte 0 = MSB)
//   0x20 nonce[16] = AEAD nonce/IV (byte 0 = MSB)
//   0x30 secret[16]= device secret (byte 0 = MSB)
`default_nettype none
module i2c_eeprom_loader #(
    parameter integer CLK_HZ = 10_000_000,
    parameter integer I2C_HZ = 100_000,
    parameter [6:0]   DEV    = 7'h50,
    parameter [31:0]  MAGIC  = 32'h4153434E   // "ASCN"
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        go,
    inout  wire        scl,
    inout  wire        sda,
    output reg         keys_loaded,
    output reg         eeprom_error,
    output reg  [3:0]  load_code,     // 0 ok,1 noack,2 bad magic,3 bad ver,4 crc
    output reg  [127:0] key,
    output reg  [127:0] nonce,
    output reg  [127:0] secret
);
    // ---- open-drain drivers (1 => pull line low, 0 => release/Hi-Z) ----
    reg scl_drv, sda_drv;
    assign scl = scl_drv ? 1'b0 : 1'bz;
    assign sda = sda_drv ? 1'b0 : 1'bz;
    wire sda_in = (sda === 1'b0) ? 1'b0 : 1'b1;

    // ---- quarter-bit tick ----
    localparam integer DIV = (CLK_HZ/(I2C_HZ*4)) < 1 ? 1 : (CLK_HZ/(I2C_HZ*4));
    reg [15:0] divcnt; reg tick;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin divcnt<=0; tick<=0; end
        else if(divcnt>=DIV-1) begin divcnt<=0; tick<=1; end
        else begin divcnt<=divcnt+1; tick<=0; end
    end

    function [15:0] crc16_upd(input [15:0] c, input [7:0] d);
        integer i; reg [15:0] x;
        begin
            x = c ^ {d,8'b0};
            for(i=0;i<8;i=i+1) x = x[15] ? (x<<1)^16'h1021 : (x<<1);
            crc16_upd = x;
        end
    endfunction

    localparam OP_START=0, OP_TX=1, OP_RX=2, OP_RSTART=3, OP_STOP=4;
    localparam S_IDLE=0, S_START=1, S_CTRLW=2, S_ADDR=3, S_RSTART=4, S_CTRLR=5,
               S_READ=6, S_STOP=7, S_VALIDATE=8, S_DONE=9, S_ERR=10;
    reg [3:0] st;
    reg [2:0] op;
    reg [3:0] bitc;
    reg [1:0] q;
    reg [7:0] txb, rxb;
    reg       ackbit, rd_ack, busy;
    reg [6:0] bytei;

    // on-the-fly capture
    reg [31:0] magic_r;
    reg [7:0]  ver_r, crc_hi, crc_lo;
    reg [15:0] crc_acc;
    reg [127:0] key_r, nonce_r, secret_r;

    task start_phase(input [2:0] o); begin op<=o; bitc<=0; q<=0; busy<=1; end endtask

    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            st<=S_IDLE; scl_drv<=0; sda_drv<=0; busy<=0; bytei<=0; q<=0; bitc<=0;
            keys_loaded<=0; eeprom_error<=0; load_code<=4'hF; op<=OP_START; rd_ack<=0;
        end else begin
            // ---------- bit/byte engine (advances on tick) ----------
            if (busy && tick) begin
                case (op)
                OP_START, OP_RSTART: begin
                    case (q)
                    0: begin sda_drv<=0; scl_drv<=(op==OP_RSTART); end
                    1: begin scl_drv<=0; sda_drv<=0; end
                    2: begin scl_drv<=0; sda_drv<=0; end
                    3: begin sda_drv<=1; end
                    endcase
                    if (q==3) begin scl_drv<=1; busy<=0; end
                    q<=q+1;
                end
                OP_TX: begin
                    if (bitc < 8) begin
                        case (q)
                        0: begin scl_drv<=1; sda_drv<=~txb[7]; end
                        1: begin scl_drv<=0;                 end
                        2: ;
                        3: begin scl_drv<=1;                 end
                        endcase
                        if (q==3) begin txb<={txb[6:0],1'b0}; bitc<=bitc+1; end
                        q<=q+1;
                    end else begin
                        case (q)
                        0: begin scl_drv<=1; sda_drv<=0; end
                        1: begin scl_drv<=0;            end
                        2: begin ackbit<=sda_in;        end
                        3: begin scl_drv<=1;            end
                        endcase
                        if (q==3) busy<=0;
                        q<=q+1;
                    end
                end
                OP_RX: begin
                    if (bitc < 8) begin
                        case (q)
                        0: begin scl_drv<=1; sda_drv<=0; end
                        1: begin scl_drv<=0;            end
                        2: begin rxb<={rxb[6:0],sda_in}; end
                        3: begin scl_drv<=1;            end
                        endcase
                        if (q==3) bitc<=bitc+1;
                        q<=q+1;
                    end else begin
                        case (q)
                        0: begin scl_drv<=1; sda_drv<=rd_ack; end
                        1: begin scl_drv<=0;              end
                        2: ;
                        3: begin scl_drv<=1; end
                        endcase
                        if (q==3) begin sda_drv<=0; busy<=0; end
                        q<=q+1;
                    end
                end
                OP_STOP: begin
                    case (q)
                    0: begin scl_drv<=1; sda_drv<=1; end
                    1: begin scl_drv<=0;            end
                    2: begin sda_drv<=0;            end
                    3: ;
                    endcase
                    if (q==3) busy<=0;
                    q<=q+1;
                end
                endcase
            end

            // ---------- high-level sequencer ----------
            case (st)
            S_IDLE: if (go) begin
                keys_loaded<=0; eeprom_error<=0; load_code<=4'hE; bytei<=0;
                start_phase(OP_START); st<=S_START;
            end
            S_START:  if (!busy) begin txb<={DEV,1'b0}; start_phase(OP_TX); st<=S_CTRLW; end
            S_CTRLW:  if (!busy) begin
                        if (ackbit) begin load_code<=4'd1; st<=S_ERR; end
                        else begin txb<=8'h00; start_phase(OP_TX); st<=S_ADDR; end
                      end
            S_ADDR:   if (!busy) begin
                        if (ackbit) begin load_code<=4'd1; st<=S_ERR; end
                        else begin start_phase(OP_RSTART); st<=S_RSTART; end
                      end
            S_RSTART: if (!busy) begin txb<={DEV,1'b1}; start_phase(OP_TX); st<=S_CTRLR; end
            S_CTRLR:  if (!busy) begin
                        if (ackbit) begin load_code<=4'd1; st<=S_ERR; end
                        else begin bytei<=0; rd_ack<=1'b1; crc_acc<=16'hFFFF;
                                   start_phase(OP_RX); st<=S_READ; end
                      end
            S_READ:   if (!busy) begin
                        // consume image byte `bytei` on the fly
                        if (bytei < 7'd4) magic_r <= {magic_r[23:0], rxb};
                        if (bytei == 7'd4)  ver_r  <= rxb;
                        if (bytei == 7'd14) crc_hi <= rxb;
                        if (bytei == 7'd15) crc_lo <= rxb;
                        if (bytei >= 7'd16) begin
                            crc_acc <= crc16_upd(crc_acc, rxb);
                            if      (bytei < 7'd32) key_r    <= {key_r[119:0], rxb};
                            else if (bytei < 7'd48) nonce_r  <= {nonce_r[119:0], rxb};
                            else                    secret_r <= {secret_r[119:0], rxb};
                        end
                        if (bytei==7'd63) begin start_phase(OP_STOP); st<=S_STOP; end
                        else begin
                            bytei<=bytei+1;
                            rd_ack <= (bytei==7'd62) ? 1'b0 : 1'b1; // NACK final byte
                            start_phase(OP_RX); st<=S_READ;
                        end
                      end
            S_STOP:   if (!busy) st<=S_VALIDATE;
            S_VALIDATE: begin
                if      (magic_r != MAGIC)            begin load_code<=4'd2; st<=S_ERR; end
                else if (ver_r != 8'h01)             begin load_code<=4'd3; st<=S_ERR; end
                else if ({crc_hi,crc_lo} != crc_acc) begin load_code<=4'd4; st<=S_ERR; end
                else begin
                    key<=key_r; nonce<=nonce_r; secret<=secret_r;
                    load_code<=4'd0; keys_loaded<=1; st<=S_DONE;
                end
            end
            S_ERR:  begin eeprom_error<=1; st<=S_DONE; end
            S_DONE: st<=S_DONE;
            default: st<=S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
