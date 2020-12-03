from __future__ import unicode_literals

#import pandas as pd
import subprocess as thread


# paths
LTSPICE_PATH = "/home/mxfxm/.wine/drive_c/Program Files/LTC/LTspiceXVII/XVIIx64.exe" # if wine is used, provide extra command
FILE_PATH = "/home/mxfxm/.wine/drive_c/users/mxfxm/simulations/"
INPUT_FILE = "Draft1.asc"
SIMULATION_FILE = "SIM.asc"
SIMULATION_RAW = "SIM.raw"
SIMULATION_PATH = "C:/users/mxfxm/simulations/SIM.asc"
OUTPUT_FILE = "/home/mxfxm/Desktop/output.csv"

# settings
TIME_STEP = 10 # in nano seconds
STEPS_PER_CYCLE = 1
SIMULATION_TIME = 1e-6
SIMULATION_RUNTIME = 3
USE_WINE = True
KEEP_ADDED_SAMPLES = True

# initialize
time = 0

with open(f"{FILE_PATH}{SIMULATION_FILE}", 'wb') as simulation_file: # write a new file to not kill the original
    with open(f"{FILE_PATH}{INPUT_FILE}", 'rb') as schematic_file: # open the original file
        for n, line in enumerate(schematic_file): # step through each line
            # set the time step in the transient command
            if b'tran' in line: # set transient analysis and time steps
                linestart = line.split(b'!')[0]
                sim_len = f"{TIME_STEP * STEPS_PER_CYCLE}"
                sim_step = f"{TIME_STEP}"
                linestart = linestart + b'!.tran 0 ' + sim_len.encode("UTF-8") + b'n 0 ' + sim_step.encode("UTF-8") + b'n\n'
                print(linestart)
                line = linestart
            
            simulation_file.write(line)

out = open(OUTPUT_FILE, "w")
newfile = True

name_dict = {}

# loop until simulation is done
# or break criteria was met
while time < SIMULATION_TIME:

    # run ltspice for the next cycle
    args = []
    if USEWINE == True:
        args = ["wine", LTSPICE_PATH, SIMULATION_PATH, "-ascii",  "-run",  "-wine"]
    else:
        args = [LTSPICE_PATH, SIMULATION_PATH, "-ascii",  "-run"]

    process = thread.Popen(args, stdout=thread.PIPE)
    try:
        (out, err) = process.communicate(timeout=SIMULATION_RUNTIME)
    except thread.TimeoutExpired:
        process.kill()

    # read the raw file
    names = []
    variables = []
    names_start = False
    values_start = False
    with open(f"{FILE_PATH}{SIMULATION_RAW}", "rb") as raw:
        for n, line in enumerate(raw):
            if values_start == True:
                decoded = line.decode("UTF-8")
                step = decoded.split('\t')[0]
                value = decoded.split('\t')[1]
                if step != "":
                    variables.append([])
                    steptime = decoded.split('\t')[2]
                    variables[-1].append(float(steptime[:-2])+time)
                else:
                    variables[-1].append(value[:-2])

            if names_start == True:
                if b'Values:' in line:
                    names_start = False
                    values_start = True
                else:
                    decoded = line.decode("UTF-8")
                    name = decoded.split('\t')[2]
                    names.append(name)
            
            if b'Variables:\r\n' in line:
                names_start = True
    
    # save the new output
    if newfile: # if the file is new, output a header line
        for n, name in enumerate(names):
            out.write(f"{name}\t")
            name_dict[name] = n
        out.write("\n")
        newfile = False
        for step in variables[:0]: # use initial point
            for value in step:
                out.write(f"{value}\t")
            out.write("\n")
    if KEEP_ADDED_SAMPLES: # keep all samples
        for step in variables[1:]: # skip initial point
            for value in step:
                out.write(f"{value}\t")
            out.write("\n")
    else: # only keep the last point (sample distance as set above)
        for value in variables[-1]:
            out.write(f"{value}\t")
        out.write("\n")
    
    # test abort criteria
    pass

    # python simulation time counter
    time = time + TIME_STEP * STEPS_PER_CYCLE * 1e-9
    
    # set for the next cycle
    # for example initial voltages and currents on capacitors and inductors
    # also set the voltage sources if necessary
    # set the timeoffset for sources using the passed time
    with open(f"{FILE_PATH}{SIMULATION_FILE}", 'wb') as simulation_file: # write a new file to not kill the original
        with open(f"{FILE_PATH}{INPUT_FILE}", 'rb') as schematic_file: # open the original file
            prevline = None
            for n, line in enumerate(schematic_file): # step through each line
                if prevline == None: # catch an error
                    prevline = line

                if b'tran' in line: # set transient analysis and time steps
                    linestart = line.split(b'!')[0]
                    sim_len = f"{TIME_STEP * STEPS_PER_CYCLE}"
                    sim_step = f"{TIME_STEP}"
                    linestart = linestart + b'!.tran 0 ' + sim_len.encode("UTF-8") + b'n 0 ' + sim_step.encode("UTF-8") + b'n\n'
                    line = linestart
                
                if b'param starttime' in line: # set the starttime to compensate for previous runs
                    linestart = line.split(b'!')[0]
                    sim_time = f"{time}"
                    linestart = linestart + b'!.param starttime -' + sim_time.encode("UTF-8") + b'\n'
                    line = linestart

                # this is an example for a controlled value, in this case the voltage output of the source "OUTPIN"
                if b'OUTPIN' in prevline:
                    adcvoltage = float(variables[-1][name_dict["V(adcpin)"]])
                    outvoltage = 0
                    if adcvoltage > 0.5:
                        outvoltage = 5 * adcvoltage
                    value = f"{outvoltage}"
                    linestart = b'SYMATTR Value ' + value.encode("UTF-8") + b'\n'
                    line = linestart

                # this is an example for a voltage dependent capacitor
                # its capacitance changes over voltage
                # and the voltage is kept between runs as the initial condition
                if b'MYCAP' in prevline:
                    capvoltage = float(variables[-1][name_dict["V(somevoltage)"]])
                    capacitance = (10 - 10 * capvoltage) * 1
                    if capacitance < 1:
                        capacitance = 1
                    value = f"{capacitance}u"
                    startvalue = f"IC={capvoltage}"
                    linestart = linestart + b'SYMATTR Value ' + value.encode("UTF-8") + b' ' + startvalue.encode("UTF-8") + b'\n'
                    line = linestart

                simulation_file.write(line)
                prevline = line


    #break

out.close()