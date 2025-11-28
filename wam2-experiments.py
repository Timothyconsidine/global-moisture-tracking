#!/usr/bin/env python
# coding: utf-8

# In[1]:


#Importing and setting directory
import yaml
import os
import shutil
import subprocess

directory = '/glade/u/home/considine/'
os.chdir(directory)


# In[2]:


#Delete folder function
def delete_folder(folder): #Method deletes configuration folder and files

        os.chdir(directory)
        folder_path = directory + folder

        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            os.remove(file_path)

        os.rmdir(folder_path)


# In[3]:


#Class that creates wam2 experiments
class wam2experiment:

    #Constructor method, all inputs except coordinates are strings
    def __init__(self, cls, direction, output_frequency, coordinates, output_folder):

        os.chdir(directory)

        if direction == 'forward':
            with open('config-template-forward.yaml', 'r') as f:
                cls.template = yaml.load(f, Loader=yaml.FullLoader)
        else:
            with open('config-template-backward.yaml', 'r') as f:
                cls.template = yaml.load(f, Loader=yaml.FullLoader)

        #Creating instances of variables unique to this experiment
        self.direction = direction 
        self.coordinates = coordinates 
        self.output_frequency = output_frequency 
        self.output_folder = '/glade/derecho/scratch/considine/'+output_folder
        self.config_folder = output_folder + '-config'

        if os.path.exists(directory + self.config_folder):
            return

        try: #Creating configuration folder
            os.mkdir(self.config_folder)
        except Exception as e:
            print(f"An error occurred: {e}")

        try: #Creating output folder
            os.mkdir(self.output_folder)
        except Exception as e:
            print(f"An error occurred: {e}")

        #Modifying the template for this experiment
        cls.template['tracking_direction'] = direction
        cls.template['output_frequency'] = output_frequency
        cls.template['output_folder'] = self.output_folder

        #Used for naming files
        fb = list(direction.lower())

        #Creating a configuration file for each set of coordinates
        for c in coordinates: 

            cls.template['tagging_region'] = c
            file_name = 'config['+str(c[0])+'_'+str(c[1])+']_'+fb[0]+'_'+output_frequency.lower()+'.yaml'

            with open(file_name, "a") as f:
                file_contents = yaml.dump(cls.template)
                f.write(file_contents)

            shutil.move(file_name, self.config_folder) #Moving file into configuration folder

    #Method to run experiment
    def run_experiment(self):
        os.chdir(directory + self.config_folder)

        derecho_job = ['#!/bin/bash', #0
                 '#PBS -A WYOM0161', #1
                 '#PBS -l walltime=04:00:00', #2
                 '#PBS -q main', #3
                 '#PBS -l select=1:ncpus=1:mem=20GB', #4
                 '#PBS -N ', #5
                 '#PBS -e ', #6
                 '#PBS -o ', #7
                 'module load conda', #8
                 'conda activate wamenv', #9
                 'wam2layers track '] #10

        count = 0

        for file in os.listdir(directory + self.config_folder):

            if file.startswith('config') == False:
                continue

            count = count + 1

            if self.direction == 'forward':
                file_name = 'job'+str(count)+'f'
            else:
                file_name = 'job'+str(count)+'b'

            derecho_job[5] = '#PBS -N ' + file_name
            derecho_job[6] = '#PBS -e ' + file_name + '_e.txt'
            derecho_job[7] = '#PBS -o ' + file_name + '_o.txt'
            derecho_job[10] = 'wam2layers track ' + directory + self.config_folder+ '/' + file

            with open(file_name+'.sh',"w") as f:
                f.write('\n'.join(derecho_job))

            subprocess.call('qsub '+file_name+'.sh',shell=True)

        return None


# In[4]:


#Creating Experiments

#Where you run wam2layers: /glade/work/considine/conda-envs/wamenv

#Creating vector of coordinate values
coordinates = []
x = 2
longitude = list(range(-180,179,x))
latitude = list(range(-80,79,x))

for w in longitude:

    for s in latitude: 
        e = w+2
        n = s+2
        coordinates.append([w,s,e,n])

#Test experiment
test = wam2experiment(wam2experiment, 'forward', '1D', [coordinates[0]], 'test6')
test.run_experiment()

#Creating global forward tracking experiment
#global_forward = wam2experiment(wam2experiment, 'forward', '1D', coordinates,'global-forward')

#Creating global backward tracking experiment
#global_backward = wam2experiment(wam2experiment, 'backward', '1D', coordinates,'global-backward')

#Running global forward tracking experiment
#global_forward.run_experiment()

#Running global backward tracking experiment
#global_backward.run_experiment()


# Notes
# 
# We will run wam2layers in this directory: /glade/work/considine/conda-envs/wamenv
# 
# module load conda
# conda activate wamenv
# wam2layers track <<path to config file>>
# 
# #!\bin\bash
# 
# #Need to submit on derecho computer

# In[ ]:




