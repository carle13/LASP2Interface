from mpi4py import MPI
import lammps
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import signal
import time

# Python script to perform a simulation with nnp potentials and check agreement

# Function to measure the agreement between the different potentials
def check():
    disag = 0.0
    # Disagreement measurement loop
    seeds = [None]*5
    forces = [None]*5
    for b in range(5):
        # Create 5 lammps objects with no output
        seeds[b] = lammps.lammps(cmdargs=["-log", "none", "-screen", os.devnull,  "-nocite"])
        seeds[b].command('units metal')
        seeds[b].command('boundary p p p')
        # Read the last structure of the main simulation
        seeds[b].command('read_data check.data')

        # Setup potentials with different random seeds for each lammps object
        seeds[b].command('pair_style hdnnp 6.0 dir '+potDir+'/Seed'+str(b+1)+' showew no showewsum 100 resetew no maxew 10000000 cflength 1.0 cfenergy 1.0')
        seeds[b].command('pair_coeff * * Au')
        # Perform an empty step to calculate forces
        seeds[b].command('run 0')
        # Extract forces and destroy temporary lammps object
        forces[b] = seeds[b].numpy.extract_atom('f').copy()
        seeds[b].close()
    # Calculate the standard deviation of the forces calculated with the different random seeds
    deviationAtom = np.std(np.ma.masked_invalid(forces), axis=0)
    # Get the maximum standard deviation
    try:
        deviationMax = np.ma.masked_invalid(deviationAtom).max()
    except ValueError: #In case the forces array of this MPI process is empty
        deviationMax = 0.0
    # MPI process communication
    if rank == 0: #If this is the main thread, wait for other threads to send their maximum standard deviation
        forceNodes = []
        forceNodes.append(deviationMax)
        for s in range(1, nprocs):
            message = comm.recv(source=s, tag=s)
            forceNodes.append(message)
        disag = max(forceNodes) #Get the maximum of the standard deviations obtained by each MPI process
    else: #If this is not the main thread send a message to the main thread with the max standard deviation
        comm.send(deviationMax, dest=0, tag=rank)
        # Wait for message to know that it is ok to continue
        message = comm.recv(source = 0, tag = rank)
        if message == 1:
            return True
    if rank == 0:
        disagreement.append(disag)
        # Flag activation
        message = 0
        if disag > threshold:
            sections.append(disagreement.copy())
            disagreement.clear()
            message = 1
            # Disagreement is too high
            # DFT calculations will be performed and potentials will be trained
            ############# TEST DATA ########################################
            file2 = open('train.outcar', 'w')
            file2.write('energy without something etc ' + str(pe))
            file2.close()
            ################################################################
        for i in range(1, nprocs):
            comm.send(message, dest=i, tag=i)
        if disag > threshold:
            return True
    return False

# MPI variables and set COMM_WORLD as communicator
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
nprocs = comm.Get_size()

potentialSeed = 1 #Potential used for main simulation
dataDir = 'Au100Messy.data' #Location of the structure being simulated
potDir = 'PotentialsComplete' ############################### TEST ####################################
#potDir = 'Training/Potentials'

# Main LAMMPS object to carry on the simulation
lmp = lammps.lammps()
lmp.command('units metal')
lmp.command('boundary p p p')
lmp.command('read_data '+dataDir)

# Setup n2p2 potential
lmp.command('pair_style hdnnp 6.0 dir '+potDir+'/Seed'+str(potentialSeed)+' showew no showewsum 100 resetew no maxew 10000000 cflength 1.0 cfenergy 1.0')
lmp.command('pair_coeff * * Au')

# Read commands for the simulation to be performed
lmp.file('input.lmp')
lmp.command('run 0')
pe = lmp.get_thermo("pe")

# Training variables
disagreement = []
sections = []
threshold = 0.02001143776 * 4 #Disagreement value that will activate the training flag
totalSteps = 1000 #Total number of steps to be simulated
checkEvery = 100 #Number of steps after which the agreement will be measured
checkSteps = int(totalSteps / checkEvery) #Number of times the agreement will be measured
startPoint = 0

def simulate():
    global startPoint
    global pe
    # Simulation loop
    for a in range(startPoint, checkSteps):
        # Save the structure
        lmp.command('write_data check.data')
        #################### TEST DATA
        lmp.command('write_dump all custom train.lammpstrj id type x y z fx fy fz modify sort id')
        #############################

        # Measure agreement
        flag = check()
        if flag:
            startPoint = a
            return False

        # Advance the simulation
        lmp.command('run '+str(checkEvery))
        pe = lmp.get_thermo("pe")

    # Measure agreement of last structure in the simulation
    lmp.command('write_data check.data')
    flag = check()
    if flag:
        return False
    sections.append(disagreement.copy())

    # Plotting disagreement over time (Only on rank 0)
    if rank == 0:
        plt.rcParams["axes.prop_cycle"] = plt.cycler("color", plt.cm.Dark2.colors)
        fig, ax1 = plt.subplots()

        ax1.set_title('Evolution (100) Au (T = 1000)')
        ax1.set_ylabel('Disagreement')
        ax1.set_xlabel('Timestep')

        x = []
        for i in range(len(sections)):
            x.append((np.arange(len(sections[i])))*checkEvery)
            if i > 0:
                x[i] += x[i-1][-1]
            ax1.plot(x[i], sections[i], marker='o', ls=':')
        ax1.axhline(threshold, ls='--', color='black')

        fig.savefig('timeAgreement.png')
        print('Finished')
    return True