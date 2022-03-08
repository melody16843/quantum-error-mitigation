# reference
https://www.nature.com/articles/s41534-022-00517-3
the file basis_ops.py, burer_monteiro.py, channels.py, decomposition.py, diamond_norm.py, jason_tools.py, stinespring.py, variational_approximation.py is based on the github account the essay attached.

# about gate_apply file
1. use gen_data to get decomposition set of a certain gate.
2. use our_simulation to get result based on the decomposition set the user give.
  our_simulation(shots,qc,file_name,noise_model,print_data,gamma)
  shots: integer
  qc:quantum circuit
  file_name: {'gate name':'dir name of the decomposition set'}
  noise_model: noise_model
  print_data: if true, the process would be printed
  gamma:{'gate name':'gamma of the gate'}

## notice
please use cx gate instead of cnot, or the program would lead to a bug.
