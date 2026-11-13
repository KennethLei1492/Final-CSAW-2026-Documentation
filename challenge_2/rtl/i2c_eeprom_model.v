// i2c_eeprom_model.v - behavioral I2C EEPROM (24LC-style) for SIMULATION ONLY.
// Responds at 7-bit device address DEV (0x50). Supports the random-read used by
// i2c_eeprom_loader.v: control(write)+word-address, repeated START,
// control(read), sequential reads with master ACK/NACK, STOP. Open-drain: only
// ever pulls SDA low (ACK / read data); the board pull-ups supply the highs.
// Image bytes are loaded by the testbench via $readmemh into `mem`.
`default_nettype none
module i2c_eeprom_model #(parameter [6:0] DEV = 7'h50) (
    inout wire scl,
    inout wire sda
);
    reg [7:0] mem [0:255];
    reg sda_drv = 1'b0;              // 1 => pull SDA low
    assign sda = sda_drv ? 1'b0 : 1'bz;
    wire scl_i = (scl === 1'b0) ? 1'b0 : 1'b1;
    wire sda_i = (sda === 1'b0) ? 1'b0 : 1'b1;

    localparam ST_IDLE=0, ST_CTRL=1, ST_CTRL_ACK=2, ST_WADDR=3, ST_WADDR_ACK=4,
               ST_SEND=5, ST_SEND_ACK=6;
    reg [2:0] st = ST_IDLE;
    reg [3:0] bitc = 0;
    reg [7:0] shin, shout;
    reg [7:0] addr_ptr = 0;
    reg       rw = 0;                // 1 = read
    reg       matched = 0;

    // ---- START / STOP detection (SDA transitions while SCL high) ----
    always @(negedge sda) if (scl_i) begin        // START
        st<=ST_CTRL; bitc<=0; sda_drv<=0; matched<=0;
    end
    always @(posedge sda) if (scl_i) begin        // STOP
        st<=ST_IDLE; sda_drv<=0;
    end

    // ---- sample / shift on SCL rising edge ----
    always @(posedge scl) begin
        case (st)
        ST_CTRL:     if (bitc<8) begin shin<={shin[6:0],sda_i}; bitc<=bitc+1; end
        ST_WADDR:    if (bitc<8) begin shin<={shin[6:0],sda_i}; bitc<=bitc+1; end
        ST_SEND_ACK: begin /* master ACK/NACK sampled here */ end
        default: ;
        endcase
    end

    // ---- act / drive on SCL falling edge ----
    reg mack;
    always @(negedge scl) begin
        case (st)
        ST_CTRL: begin
            if (bitc==8) begin
                rw <= shin[0];
                if (shin[7:1]==DEV) begin matched<=1; sda_drv<=1; st<=ST_CTRL_ACK; end
                else begin matched<=0; sda_drv<=0; st<=ST_IDLE; end
            end
        end
        ST_CTRL_ACK: begin
            sda_drv<=0; bitc<=0;
            if (rw) begin shout<=mem[addr_ptr]; st<=ST_SEND; sda_drv<=~mem[addr_ptr][7]; shout<={mem[addr_ptr][6:0],1'b0}; end
            else    st<=ST_WADDR;
        end
        ST_WADDR: begin
            if (bitc==8) begin addr_ptr<=shin; sda_drv<=1; st<=ST_WADDR_ACK; end
        end
        ST_WADDR_ACK: begin sda_drv<=0; bitc<=0; st<=ST_IDLE; end // await repeated START
        ST_SEND: begin
            // drive next data bit while SCL low (MSB first)
            if (bitc<7) begin
                sda_drv<=~shout[7]; shout<={shout[6:0],1'b0}; bitc<=bitc+1;
            end else begin
                // 8 bits sent; release SDA for the master ACK/NACK bit
                sda_drv<=0; bitc<=0; st<=ST_SEND_ACK;
            end
        end
        ST_SEND_ACK: begin
            // master drove ACK(0)/NACK(1) during the high we just left
            mack = sda_i;
            if (!mack) begin
                addr_ptr<=addr_ptr+1;
                shout<={mem[addr_ptr+1][6:0],1'b0}; sda_drv<=~mem[addr_ptr+1][7];
                bitc<=0; st<=ST_SEND;
            end else begin
                sda_drv<=0; st<=ST_IDLE;   // NACK -> stop sending
            end
        end
        default: ;
        endcase
    end
endmodule
`default_nettype wire
