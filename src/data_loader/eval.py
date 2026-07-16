import os
import glob
import sys
import pandas as pd

#Structure of the output CSV file for evaluation results:
#file_name, compile_success, test_1_result, ..., test_n_result, test_1_score, ..., test_n_score, total_score
#	compile_success = boolean value (true = successfully compiled)
#	test_i_result = P --> passed
#	       	      = R --> failed, runtime error
#	              = O --> failed, output mismatch
#	       	      = - --> failed by default due to compilation fail


#Change the below variables to have this program run for all the different weeks of data
path_main = "./lab_ec"
path_test_file_regex = path_main + "/week2/in*.txt"
path_res_file_regex = path_main + "/week2/out*.txt"
driver_name_no_extension = "main"
path_driver_no_extension = path_main + "/week2/" + driver_name_no_extension
path_student_files = path_main + "/week2/A/"
path_output_data = "./" #make sure this folder already exists

#Fetching the student files and test case files
# Here we have assumed that every test file has a corresponding result file and there are no mismatches in the pairs
# i.e. test file i has a corresponding res file i
names = sorted(glob.glob(path_student_files + '/*.c'))
test_files = sorted(glob.glob(path_test_file_regex))
res_files = sorted(glob.glob(path_res_file_regex))

#misc variables
len_path_student_files = len(path_student_files)
num_tests = len(test_files)

#Initializing dictionary of lists for evaluation results - will be converted to a dataframe and written into a csv file later
data_dict = {}
colheaders = ["file_name", "compile_success"]
for i in range(num_tests):
	data_dict[f"test_{i+1}_result"] = []
	colheaders.append(f"test_{i+1}_result")
for i in range(num_tests):
	data_dict[f"test_{i+1}_score"] = []
	colheaders.append(f"test_{i+1}_score")
colheaders.append("total_score")
data_dict["file_name"] = []
data_dict["compile_success"] = []
data_dict["total_score"] = []


#Compiling the driver .c file
status = os.system(f"gcc -c {path_driver_no_extension}.c")
if status != 0 :
	print("cannot create object file")
	sys.exit(0)


#Going through student files one by one and running the test cases
# Scoring is inflexible currently (if test case successful, 10 points, otherwise 0). This could be changed
for name in names:
	score = []
	file_name = name[len_path_student_files::]
	data_dict["file_name"].append(file_name)
	#status = os.system(f"gcc {name} {driver_name_no_extension}.o 2>/dev/null")
	status = os.system(f"gcc {name} {driver_name_no_extension}.o")
	if status != 0 :
		print("cannot compile and link", file_name)
		for i in range(num_tests):
			data_dict[f"test_{i+1}_result"].append('-')
			data_dict[f"test_{i+1}_score"].append(0)
		data_dict["compile_success"].append(0)
		data_dict["total_score"].append(0)
		continue
	else:
		data_dict["compile_success"].append(1)

	test_counter = 0
	for (test, res) in zip(test_files, res_files):
		test_counter += 1
		status = os.system(f"./a.out < {test} > out.txt")
		if status != 0 :
			print("cannot run : ", file_name)
			data_dict[f"test_{test_counter}_result"].append('R')
			data_dict[f"test_{test_counter}_score"].append(0)
			score.append(0)
			continue
		else:
			status = os.system(f"cmp -s out.txt {res}")
			if status == 0 :
				data_dict[f"test_{test_counter}_result"].append('P')
				data_dict[f"test_{test_counter}_score"].append(10)
				score.append(10)
			else:
				data_dict[f"test_{test_counter}_result"].append('O')
				data_dict[f"test_{test_counter}_score"].append(0)
				score.append(0)
	data_dict["total_score"].append(sum(score))
	print(name, score, sum(score))
'''
#Remove out.txt, a.out, and driver object file
os.system(f"rm out.txt a.out {driver_name_no_extension}.o")
'''

#Write data as a pandas dataframe into a csv file
eval_df = pd.DataFrame(data_dict, columns = colheaders)
eval_df.to_csv(f"{path_output_data}submission_data.csv")
print(f"Data has been saved as a csv file (path: {path_output_data}submission_data.csv)")