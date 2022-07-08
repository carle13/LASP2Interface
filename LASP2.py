import os
import sys
import configparser
# from mpi4py import MPI
import signal
import subprocess
import time
from interfaceN2P2 import training
import interfaceLAMMPS
import interfaceVASP

def readLASP2():
    global lasp2
    vars = config['LASP2']
    for key in vars:
        if key == 'numprocesses':
            try:
                lasp2[key] = int(vars[key])
            except:
                print('Invalid value for variable: ' +key)
                exit(1)
        elif key == 'numseeds':
            try:
                lasp2[key] = int(vars[key])
            except:
                print('Invalid value for variable: ' +key)
                exit(1)
        else:
            print('Invalid variable: '+key)
            exit(1)

def readLAMMPS():
    global lammps
    vars = config['LAMMPS']
    for key in vars:
        if key == 'totalsteps':
            try:
                lammps[key] = int(vars[key])
            except:
                print('Invalid value for variable: ' +key)
                exit(1)
        elif key == 'checksteps':
            try:
                lammps[key] = int(vars[key])
            except:
                print('Invalid value for variable: ' +key)
                exit(1)
        else:
            print('Invalid variable: '+key)
            exit(1)

def readN2P2():
    global n2p2
    vars = config['N2P2']
    for key in vars:
        if key == 'dirpotentials':
            try:
                n2p2[key] = str(vars[key])
                if not os.path.isdir(n2p2[key]):
                    print('Directory of potentials was not found')
                    raise Exception('Directory not found')
                numSeeds = lasp2['numseeds']
                for i in range(1, numSeeds+1):
                    if not os.path.isdir(os.path.join(n2p2[key], 'Seed'+str(i))):
                        print('Seed'+str(i)+' not found')
                        raise Exception('Seed not found')
            except:
                print('Invalid value for variable: ' +key)

def readVASP():
    global vasp
    vars = config['VASP']
    for key in vars:
        if key == 'numProcesses':
            try:
                vasp[key] = int(vars[key])
            except:
                print('Invalid value for variable: ' +key)

# # MPI variables and set COMM_WORLD as communicator
# comm = MPI.COMM_WORLD
# rank = comm.Get_rank()
# nprocs = comm.Get_size()

# Read input from lasp2.ini or another file indicated by the user
inputFile = 'lasp2.ini'
for i in range(len(sys.argv)):
    if sys.argv[i] == '-i':
        try:
            inputFile = sys.argv[i+1]
            if not os.path.isfile(inputFile):
                print('Input file could not be found: '+inputFile)
                raise Exception('File error')
        except:
            print('No valid inpupt parameter after option -i')
            exit(1)

# Dictionaries where configuration variables will be stored
lasp2 = dict()
lammps = dict()
n2p2 = dict()
vasp = dict()

config = configparser.ConfigParser()
config.read(inputFile)
for section in config:
    if section == 'LASP2':
        readLASP2()
    elif section == 'LAMMPS':
        readLAMMPS()
    elif section == 'N2P2':
        readN2P2()
    elif section == 'VASP':
        print('Found variables for VASP')
    elif section == 'DEFAULT':
        if len(config[section]) > 0:
            print('Undefined section found: DEFAULT')
            exit(1)
    else:
        print('Undefined section found: ' + section)
        exit(1)

potDirs = 'Training/'
outDirs = 'Output/'
os.makedirs(potDirs, exist_ok=True)
os.makedirs(outDirs, exist_ok=True)
potInitial = 'PotentialsComplete/'
os.system('cp -r '+potInitial+' '+potDirs+'Potentials')

trainings = 1

while True:
    if not interfaceLAMMPS.simulate():
        training(potDirs, trainings)
        trainings += 1
    else:
        break

# End of the program
# MPI.Finalize()