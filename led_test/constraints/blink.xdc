#Zybo Z7-10 constraint file
#Blink LED test - derived from DA2JE7_10.xdc

#Clock signal
set_property PACKAGE_PIN K17 [get_ports clk]
set_property IOSTANDARD LVCMOS33 [get_ports clk]
create_clock -add -name sys_clk_pin -period 8.00 -waveform {0 4} [get_ports clk]

#LED0
set_property PACKAGE_PIN M14 [get_ports led]
set_property IOSTANDARD LVCMOS33 [get_ports led]