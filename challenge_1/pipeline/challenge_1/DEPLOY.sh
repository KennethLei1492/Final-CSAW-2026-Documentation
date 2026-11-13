#!/bin/bash
# ============================================
# CSAW26 — Deploy Trojan to Hackster Board
# Clone, simulate, synthesize, flash
# ============================================

set -e

# Step 0: Clone the repo
git clone https://github.com/koillea/CSAW26.git
cd CSAW26

# Step 1: Simulate (verify logic works)
echo "=== STEP 1: Simulating ==="
iverilog -o sim_trojan tb/tb_trojan.v rtl/spi_crypto_top.v rtl/crypto_core.v
vvp sim_trojan

iverilog -o sim_validate tb/tb_validate.v rtl/spi_crypto_top.v rtl/crypto_core.v
vvp sim_validate

# Step 2: Synthesize (Verilog → gates)
echo "=== STEP 2: Synthesizing ==="
yosys -p "read_verilog rtl/spi_crypto_top.v rtl/crypto_core.v; synth_ice40 -top spi_crypto_top -json design.json"

# Step 3: Place and route (gates → physical layout)
echo "=== STEP 3: Place and Route ==="
nextpnr-ice40 --up5k --json design.json --pcf hackster.pcf --asc design.asc

# Step 4: Pack bitstream (layout → binary)
echo "=== STEP 4: Packing Bitstream ==="
icepack design.asc design.bin

# Step 5: Flash to board (binary → FPGA)
echo "=== STEP 5: Flashing to Board ==="
iceprog design.bin

echo "=== DONE: Trojan deployed. Run MicroPython exploit on RP2040. ==="
