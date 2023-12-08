#!/usr/bin/env python
# coding: utf-8

# In[1]:
from gurobipy import *
import os
import csv

# In[4]:

name1 = "ZJX_Central.csv"
name2 = "ZJX_East.csv"
name3 = "ZJX_North.csv"
name4 = "ZJX_South.csv"
name5 = "ZJX_West.csv"

with open(name1, 'r') as file:
    csv_reader = csv.reader(file)
    data = []

    for row in csv_reader:
        data.extend(row)

data_file_name = file.name
#print(data)

# In[5]:

s = [32, 40]
r = [int(value) for value in data]

## limit input size for trial runs
#r = r[0:240]

# In[7]:
# Model Initiation
m = Model("Shift_Scheduling_Problem")


# In[8]:


######################################
########## Input parameters ##########
######################################
## Subscript 1 is for 8 hours shifts and 2 is for 10 hour shifts

# HOURLY cost of 1 shift
hcost = 1

# hours in 1 shift
h1 = 8
h2 = 10

# number of shifts in schedule
j1 = 10
j2 = 8

# cost of entire schedule
c1 = hcost*h1*j1
c2 = hcost*h2*j2

# overtime hourly cost
ot_hcost = 1.5 * hcost

# total number of schedules
n1 = 30
n2 = 30


# In[9]:


i_indices = range(n1) #Total count of standard schedules
k_indices = range(n2) #Total count of compressed schedules

j1_indices = range(j1) #shift indices in standard schedule
j2_indices = range(j2) #shift indices in compressed schedule

t_indices = range(len(r)) #time period indices

# In[10]:


########################################
########## Decision Variables ##########
########################################

###
### Schedule selection ###
S = m.addVars(i_indices, vtype=GRB.BINARY, name="S")
C = m.addVars(k_indices, vtype=GRB.BINARY, name="C")


###
### Normal Working Hours ### (only captures starting marks)
# Normal working hours initiation for each shift "j1" in standard schedule "i"
X = m.addVars(i_indices, j1_indices, t_indices, vtype=GRB.BINARY, name="X")

# Normal working hours initiation for each shift "j2" in compressed schedule "k"
Y = m.addVars(k_indices, j2_indices, t_indices, vtype=GRB.BINARY, name="Y")


###
### Overtime working hours ### (captures all the time periods that are active)
# Active period for Overtime in "i"th standard schedule's "j1"th shift
OS = m.addVars(i_indices, j1_indices, t_indices, vtype=GRB.BINARY, name="OS")

# Active period for Overtime in "k"th compressed schedule's "j2"th shift
OC = m.addVars(k_indices, j2_indices, t_indices, vtype=GRB.BINARY, name="OC")


# In[11]:


########################################
########## Objective function ##########
########################################

expression01 = quicksum(c1 * S[i] for i in i_indices)
expression02 = quicksum(c2 * C[k] for k in k_indices)
expression03 = quicksum(ot_hcost * OS[i, j1, t] for i in i_indices for j1 in j1_indices for t in t_indices)
expression04 = quicksum(ot_hcost * OC[k, j2, t] for k in k_indices for j2 in j2_indices for t in t_indices)

# Set objective function
m.setObjective(expression01 + expression02 + expression03 + expression04, GRB.MINIMIZE)

# In[12]:


#################################
########## Constraints ##########
#################################

###
### demand constraint

## POSSIBLE ERROR

for t in t_indices:
    time_range_normal = range(max(0, t-31), t+1)
    time_range_compressed = range(max(0, t-39), t+1)
    
    exp1 = quicksum(S[i]*X[i, j1, tau] for i in i_indices for j1 in j1_indices for tau in time_range_normal)
    exp2 = quicksum(C[k]*Y[k, j2, tau] for k in k_indices for j2 in j2_indices for tau in time_range_compressed)
    
    exp3 = quicksum(OS[i, j1, t] for i in i_indices for j1 in j1_indices)
    exp4 = quicksum(OC[k, j2, t] for k in k_indices for j2 in j2_indices)
    
    m.addConstr(exp1 + exp2 + exp3 + exp4 >= r[t], name=f"demand_constraint_{t}")


# In[13]:


###
### OT continuation constraints
### Only gets affected by same values of "j"
for i in i_indices:
    for j1 in j1_indices:
        for t in t_indices:
            if t >= s[0]:
                m.addConstr(OS[i, j1, t] <= X[i, j1, t-s[0]] + OS[i, j1, t-1], name=f"OS_Cont_{i},{j1},{t}")

for k in k_indices:
    for j2 in j2_indices:
        for t in t_indices:
            if t >= s[1]:
                m.addConstr(OC[k, j2, t] <= Y[k, j2, t-s[1]] + OC[k, j2, t-1], name=f"OC_Cont_{k},{j2},{t}")


# In[14]:


###
### 8-hours gap
### affected by other "j" of same "i"
# X & OS
for i in i_indices:
    for j1 in j1_indices:
        for t in t_indices:
            time_check_range1 = range(max(0,t-63), t)           
            exp001 = quicksum(X[i, jetta1, tau1] for jetta1 in j1_indices for tau1 in time_check_range1)
            
            time_check_range2 = range(max(0,t-32), t)           
            exp002 = quicksum(OS[i, jetta1, tau2] for jetta1 in j1_indices for tau2 in time_check_range2)
            
            m.addConstr(100000*(1 - X[i, j1, t]) >= exp001 + exp002, name=f"8hourGap_OS_{i}{j1}{t}")
            
# Y & OC
for k in k_indices:
    for j2 in j2_indices:
        for t in t_indices:
            time_check_range1 = range(max(0,t-71), t)           
            exp101 = quicksum(Y[k, jetta2, tau1] for jetta2 in j2_indices for tau1 in time_check_range1)
            
            time_check_range2 = range(max(0,t-32), t)           
            exp102 = quicksum(OC[k, jetta2, tau2] for jetta2 in j2_indices for tau2 in time_check_range2)
            
            m.addConstr(100000*(1 - Y[k, j2, t]) >= exp101 + exp102, name=f"8hourGap_OC_{k}{j2}{t}")
            


# In[15]:


###
### Shift validation constraint
for i in i_indices:
    a = quicksum(X[i, j1, t] for j1 in j1_indices for t in t_indices)
    b = 10*S[i]
    m.addConstr(a == b, name=f"shift_validation_S{i}")

for k in k_indices:
    a = quicksum(Y[k, j2, t] for j2 in j2_indices for t in t_indices)
    b = 8*C[k]
    m.addConstr(a == b, name=f"shift_validation_C{k}")


# In[16]:


###
### Last few shifts should not be initialized
for t in range(len(t_indices)-31, len(t_indices)):
    a = quicksum(X[i, j1, t] for i in i_indices for j1 in j1_indices)
    m.addConstr(a == 0, name=f"last_zeroes_8hours_{t}")

for t in range(len(t_indices)-39, len(t_indices)):
    a = quicksum(Y[k, j2, t] for k in k_indices for j2 in j2_indices)
    m.addConstr(a == 0, name=f"last_zeroes_10hours_{t}")


# In[17]:


###
### OT can't start in initial time
for t in range(0, 32):
    a = quicksum(OS[i, j1, t] for i in i_indices for j1 in j1_indices)
    m.addConstr(a == 0, name=f"Initial_OS_zero_{t}")
    
for t in range(0, 40):
    a = quicksum(OC[k, j2, t] for k in k_indices for j2 in j2_indices)
    m.addConstr(a == 0, name=f"Initial_OC_zero_{t}")


# In[18]:


###
###
for i in i_indices:
    for t in t_indices:
        a = quicksum(X[i, j1, t] for j1 in j1_indices)
        m.addConstr(a <= 1, name=f"one_shift_at_a_time_S_{i}{t}")
#
for k in k_indices:
    for t in t_indices:
        a = quicksum(Y[k, j2, t] for j2 in j2_indices)
        m.addConstr(a <= 1, name=f"one_shift_at_a_time_C_{k}{t}")   

# In[19]:


m.Params.timeLimit = 8*3600

m.optimize()


# In[28]:


# Check if the optimization was successful
if m.status == GRB.OPTIMAL:
    # Access and print the objective value
    print(f"Optimal Objective Value: {m.objVal}")
    # Access and print the values of decision variables X
    for i in i_indices:
        a = 0
        print(f"{i + 1}th standard schdedule's shifts should start at time period :" )
        for t in t_indices:
            for j1 in j1_indices:
                if X[i, j1, t].x == 1:
                    print(f"Shift {a +1} : Time Period {t+1}" )
                    a = a + 1
                if t < 1343:
                        if OS[i, j1, t].x == 0:
                            if OS[i, j1, t + 1].x == 1:
                                print(f"Shift {a } : OT starts at Time Period {t + 2}" )
                if t < 1343:
                        if OS[i, j1, t].x == 1:
                            if OS[i, j1, t + 1].x == 0:
                                print(f"Shift {a } : OT ends at Time Period {t + 2}" )

    for k in k_indices:
        a = 0
        print(f"{k + 1}th compressed schdedule's shifts should start at time period :" )
        for t in t_indices:
            for j2 in j2_indices:
                if Y[k, j2, t].x == 1:
                    print(f"Shift {a +1} : Time Period {t+1}" )
                    a = a + 1
                if t < 1343:
                        if OC[k, j2, t].x == 0:
                            if OC[k, j2, t + 1].x == 1:
                                print(f"Shift {a } : OT starts at Time Period {t + 2}" )
                if t < 1343:
                        if OC[k, j2, t].x == 1:
                            if OC[k, j2, t + 1].x == 0:
                                print(f"Shift {a } : OT ends at Time Period {t + 2}" )

    # Access and print the objective value
    print(f"Optimal Objective Value: {m.objVal}")
else:
    print("Optimization was not successful.")


# In[32]:


# Check if the optimization was successful
if m.status == GRB.OPTIMAL:
    
    distribution_text = ""
    # Access and print the objective value
    print(f"Optimal Objective Value: {m.objVal}")
    # Access and print the values of decision variables X
    for i in i_indices:
        a = 0
        distribution_text += f"{i + 1}th standard schdedule's shifts should start at time period :\n"
        for t in t_indices:
            for j1 in j1_indices:
                if X[i, j1, t].x == 1:
                    distribution_text += f"Shift {a +1} : Time Period {t+1} \n"
                    a = a + 1
                if t < 1343:
                        if OS[i, j1, t].x == 0:
                            if OS[i, j1, t + 1].x == 1:
                                distribution_text += f"Shift {a } : OT starts at Time Period {t + 2} & "
                if t < 1343:
                        if OS[i, j1, t].x == 1:
                            if OS[i, j1, t + 1].x == 0:
                                distribution_text += f"ends at Time Period {t + 2}\n"

    for k in k_indices:
        a = 0
        distribution_text += f"{k + 1}th compressed schdedule's shifts should start at time period :\n"
        for t in t_indices:
            for j2 in j2_indices:
                if Y[k, j2, t].x == 1:
                    distribution_text += f"Shift {a +1} : Time Period {t+1}\n"
                    a = a + 1
                if t < 1343:
                        if OC[k, j2, t].x == 0:
                            if OC[k, j2, t + 1].x == 1:
                                distribution_text += f"Shift {a } : OT starts at Time Period {t + 2} & "
                if t < 1343:
                        if OC[k, j2, t].x == 1:
                            if OC[k, j2, t + 1].x == 0:
                                distribution_text += f"ends at Time Period {t + 2}\n"

    # Access and print the objective value and wrire in file
    print(f"Optimal Objective Value: {m.objVal}")
    file_path = "PatelPatelBhandari2.txt"
    with open(file_path, "a") as file:
        file.write(distribution_text)
else:
    print("Optimization was not successful.")