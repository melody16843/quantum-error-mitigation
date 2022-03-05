import numpy as np
import scipy
import glob
from qiskit import *
from qiskit.quantum_info import *
from qiskit.providers.aer.noise import *
from qiskit.providers.aer.utils import insert_noise
from qiskit.visualization import plot_histogram
from qiskit import QuantumCircuit
from qiskit.compiler import transpile
from qiskit.circuit.library.standard_gates.equivalence_library import StandardEquivalenceLibrary
from qiskit.circuit.library import standard_gates
import random

#from json_tools import *
#from basis_ops import *
#from decomposition import *
#from channels import *
#from stinespring import stinespring_algorithm
#from variational_approximation import get_approx_circuit, get_varform_circuit
    

def data_load(file_name):
    # load quasiprobability coefficients 
    coeffs={}
    noise_choi={}
    circuits={}
    for kind in file_name.keys():
        coeffs[kind] = np.load(file_name[kind]+"/final_"+kind+".npz")["arr_2"]
        noise_choi[kind] = np.load(file_name[kind]+"/final_"+kind+".npz")["arr_1"]

        # load circuits generated by Strinespring algorithm
        def read_file(path):
            with open(path, 'r') as f:
                return f.read()
        num_files = len(glob.glob(file_name[kind]+"/*.qasm"))
        qasm_circuits = [read_file(file_name[kind]+"/final_"+kind+"_sim_circ"+str(f)+".qasm") for f in range(num_files)]
        circuits[kind] = [QuantumCircuit.from_qasm_str(s) for s in qasm_circuits]
    return circuits,coeffs,noise_choi
    
def my_sample(gate_num,shots,circuits,coeffs):
    idxlist={}
    subqcidxList={}
    subqccoeffs={}
    kind=gate_num.keys()
    for kind in kind:
        idxlist[kind] = range(len(circuits[kind]))
    for i in range(shots):
        result=[]
        strr=''
        for kind in kind:
            result=random.choices(idxlist,weights=abs(coeffs[kind]),k=gate_num[kind])
            strr+='diff'
            strr+=kind+' '
            for j in range(gate_num[kind]):
                strr=strr+str(result[j])+' '
            
        if strr in subqcidxList.keys():
            subqcidxList[strr]+=1
        else:
            subqcidxList[strr]=1
            result2=1
            seq=strr.split('diff')
            for seq in seq:
                seq_temp=seq.split(' ')
                coe=coeffs[seq_temp[0]]
                for j in range(gate_num[kind]):
                    result2 = result2*coe[seq_temp[j+1]]
            #print(result1[0],result2)
            if result2>0:
                subqccoeffs[strr]=1
            else:
                subqccoeffs[strr]=-1
    #print(subqcidxList)
    #print(subqccoeffs)
    return subqcidxList, subqccoeffs

def my_append(qc,subqc,place,noise_model):
    if subqc.num_qubits==1:
        qctot=QuantumCircuit(1)
        qctot+=subqc
        qc_noisy=insert_noise(qctot,noise_model)
    elif subqc.num_qubits == 2:
        qctot = QuantumCircuit(2)
        qctot += subqc
        qc_noisy = insert_noise(qctot, noise_model)
        # qctot.to_gate()
        qc.append(qc_noisy, place[:2])
    elif subqc.num_qubits == 3:
        qctot = QuantumCircuit(3)
        qctot.reset(2)       
        qctot += subqc
        qc_noisy = insert_noise(qctot, noise_model)
        # qctot.to_gate()
        qc.append(qc_noisy, place)
    else: raise
    

def our_simulation(shots,qc,file_name,noise_model):
    #load qc information
    num_qubit=qc.num_qubits
    #load file of decomposition set
    circuits,coeffs,noise_choi=data_load(file_name)
    
    #count number of gate
    gate_num={}
    for instruction in qc.data:
        if instruction[0].name in gate_num.keys():
            gate_num[instruction[0].name]+=1
        else:
            gate_num[instruction[0].name]=0
            
    #sample
    subqcidxList, subqccoeffs=my_sample(gate_num,shots,circuits,coeffs)
    
    totalcount={}
    
    #circuit construct
    for subcir in subqcidxList.keys():
        qc_new=QuantumCircuit(num_qubit+2,num_qubit)
        strr=subcir.split('diff')
        cir_temp={}
        #gate load
        for cir in strr:
            cir_kind=cir.split(' ')
            cir_temp[str(cir_kind[0])]=cir_kind
            cir_kind.pop(0)
        #gate apply
        for instruction in qc.data:
            kind=instruction[0].name
            if kind in cir_temp.keys():
                if instruction[0][2][0] != []: 
                    place=[instruction[0][1][0].index,instruction[0][2][0].index,num_qubit+1]
                else:
                    place=[instruction[0][1][0].index,num_qubit+1,num_qubit+2]
                my_append(qc_new,circuits[kind][cir_temp[kind][0]],place,noise_model)
        #simulation
        qc_noisy = insert_noise(qc_new, noise_model)
        backend = Aer.get_backend('qasm_simulator')
        job=execute(qc_noisy,backend,subqcidxList[subcir])
        counts = job.result().get_counts(qc_noisy)
        #coefficient apply
        for data in counts:
            if data in totalcount.keys():
                if subqccoeffs[subcir] == 1:
                    totalcount[data] += counts[data]
                elif subqccoeffs[subcir] == -1:
                    totalcount[data] -= counts[data]
            else:
                if subqccoeffs[subcir] == 1:
                    totalcount[data] = counts[data]
                elif subqccoeffs[subcir] == -1:
                    totalcount[data] = -counts[data]
                    
        return totalcount
    
    
##for generate decompostion set
    
def noise_oracle(U, num_anc,n_qubits,noise_model,saved_circuits,depth,full_connectivity):
    if num_anc == 0:
        qc = QuantumCircuit(n_qubits)
        qc.unitary(U, list(range(n_qubits)))
        qc = qiskit.compiler.transpile(qc, basis_gates=noise_model.basis_gates,
                                           coupling_map=[[0,1]])
        saved_circuits.append(qc)
        qc_noisy = insert_noise(qc, noise_model)
        return Choi(qc_noisy).data
    elif num_anc == 1:
        exp = channel_expand(n_qubits, num_anc)
        tr = channel_trace(n_qubits, num_anc)
        _,params = get_approx_circuit(U, n_qubits+num_anc, depth, full_connectivity)
        qc = get_varform_circuit(params, n_qubits+num_anc, depth, full_connectivity)
        coupling_map = [[0,1],[1,2],[0,2]] if full_connectivity else [[0,1],[1,2]]
        qc = qiskit.compiler.transpile(qc, basis_gates=noise_model.basis_gates,
                                           coupling_map=coupling_map)
        saved_circuits.append(qc)
        qc_noisy = insert_noise(qc, noise_model)
        qc_noisy = SuperOp(qc_noisy)
        return Choi( exp.compose(qc_noisy.compose(tr)) ).data
    else: raise
    
def gen_data(noise_model,target_unitary,n_qubits,depth,full_connectivity,gate_name):

    cfac_budget = None

    saved_circuits = list()
    fixed_unitaries, fixed_choi, coeffs = stinespring_algorithm(target_unitary, n_qubits, noise_oracle, disp=True, cfac_tol=1.2, bm_ops=8, cfac_budget=cfac_budget,saved_circuits,depth,full_connectivity)
    print("STINESPRING:", np.sum(np.abs(coeffs)))
    np.savez(gate_name+"/final_"+gate_name+".npz", fixed_unitaries, fixed_choi, coeffs)
    for i in range(len(saved_circuits)):
        saved_circuits[i].qasm(filename=gate_name+"/final_"+gate_name+"_sim_circ{}.qasm".format(i))