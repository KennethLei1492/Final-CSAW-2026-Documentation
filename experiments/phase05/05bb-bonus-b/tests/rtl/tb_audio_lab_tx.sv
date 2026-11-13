`timescale 1ns/1ps
module tb_audio_lab_tx;
    reg clk=0, tick=0;
    reg [15:0] input_sample=0;
    wire active;
    wire signed [15:0] audio_sample;
    always #5 clk=~clk;
    audio_lab_tx dut(.*);
    reg [15:0] magic[0:7];
    localparam [167:0] PACKET=168'hD391C5A70E4353415732362D424F4E55532D4296C7;
    integer bad,j,n,pass;
    reg expected_bit;
    reg signed [15:0] expected_sample;
    task send(input [15:0] value);
        begin
            @(negedge clk); input_sample=value; tick=1;
            @(negedge clk); tick=0;
        end
    endtask
    task check_packet;
        begin
            for(n=0;n<5376;n=n+1) begin
                if(!active) $fatal(1,"active ended early at sample %0d",n);
                expected_bit=PACKET[167-(n/32)];
                expected_sample=((n/(expected_bit?2:4))%2) ? -4096 : 4096;
                if(audio_sample !== expected_sample)
                    $fatal(1,"sample %0d: actual %0d expected %0d",n,audio_sample,expected_sample);
                // An additional trigger inside the payload must not restart it.
                if(n<5375) send(magic[n%8]);
            end
        end
    endtask
    initial begin
        magic[0]=16'h1357; magic[1]=16'hECA8;
        magic[2]=16'h2468; magic[3]=16'hDB97;
        magic[4]=16'h369C; magic[5]=16'hC963;
        magic[6]=16'h55AA; magic[7]=16'hAA55;
        #20;
        if(active!==0) $fatal(1,"active at powerup");
        for(bad=0;bad<8;bad=bad+1) begin
            send(0);
            for(j=0;j<8;j=j+1) begin
                send(magic[j] ^ ((j==bad)?16'd1:16'd0));
                if(active) $fatal(1,"near miss activated position %0d",bad);
            end
        end
        // Unticked data never advances the matcher.
        for(j=0;j<8;j=j+1) begin
            @(negedge clk); input_sample=magic[j];
            if(active) $fatal(1,"unticked data activated");
        end
        send(0);
        // Restart from a matching prefix rather than dropping the new start.
        for(j=0;j<4;j=j+1) send(magic[j]);
        for(j=0;j<8;j=j+1) send(magic[j]);
        check_packet;
        // First post-payload sample is eligible as the next trigger start.
        send(magic[0]);
        if(active) $fatal(1,"active exceeded packet length");
        for(j=1;j<8;j=j+1) send(magic[j]);
        check_packet;
        send(0);
        if(active) $fatal(1,"active exceeded second packet length");
        $display("PASS: 8 near misses, unticked inputs, prefix restart, 10752 exact PCM samples, in-payload trigger ignored, immediate rearm");
        $finish;
    end
endmodule
