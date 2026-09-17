# global-moisture-tracking
This project is a computational pipeline that automates WAM2Layers simulations to create a global dataset of precipitation. It then normalizes this precipitation by evaporation and the area of the evaporation source region. 

This pipeline works by creating a configuration template file and choosing how large you want each evaporation source region to be (we used 4x4 boxes). It then runs a simulation for each box of the desired size. 
