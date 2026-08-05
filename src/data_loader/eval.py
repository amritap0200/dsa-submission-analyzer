import glob
import sys
import subprocess
import pandas as pd

#Structure of the output CSV file for evaluation results:
#file_name, compile_success, test_1_result, ..., test_n_result, test_1_score, ..., test_n_score, total_score, "program_is_correct"
#	compile_success = boolean value (true = successfully compiled)
#	program_is_correct = boolean value (true = passed all test cases (this is after dealing with the excess print statements)
#	test_i_result = P --> passed
#	       	      = R --> failed, runtime error
#				  = RS --> failed, runtime error, specifically a segmentation fault
#	              = O --> failed, output mismatch
#				  = T --> timeout expired
#				  = U --> unknown
#	       	      = - --> failed by default due to compilation fail


#Change the below variables to have this program run for all the different weeks of data
path_main = "/home/sam/Programming/DAA_IDE/lab_ec/week2/"
path_test_file_regex = path_main + "/in*.txt"
path_res_file_regex = path_main + "/out*.txt"
driver_name_no_extension = "main"
path_driver_no_extension = path_main + driver_name_no_extension
path_student_files = path_main + "/A/"
path_output_data = "./artifacts/" #make sure this folder already exists
output_file_name = "submission_data_week2.csv"
DEFAULT_TIMEOUT = 5 #if a submission runs longer than this, kill it and log it as a timeout exceeded.

#Fetching the student files and test case files
# Here we have assumed that every test file has a corresponding result file and there are no mismatches in the pairs
# i.e. test file i has a corresponding res file i
names = sorted(glob.glob(path_student_files + '/*.c'))
test_file_paths = sorted(glob.glob(path_test_file_regex))
res_file_paths = sorted(glob.glob(path_res_file_regex))

#misc variables
len_path_student_files = len(path_student_files)
num_tests = len(test_file_paths)

#Creating file pointers for test_file_paths and reading the contents of the res_file_paths
test_file_pointers = []
results = []
for i in range(num_tests):
	file = open(test_file_paths[i], "r", encoding = "utf-8")
	test_file_pointers.append(file)
	with open(res_file_paths[i], "r", encoding = "utf-8") as file:
		results.append(file.read().strip())
	

#Initializing dictionary of lists for evaluation results - will be converted to a dataframe and written into a csv file later
data_dict = {}
data_dict["file_name"] = []
data_dict["compile_success"] = []
data_dict["total_score"] = []
data_dict["program_is_correct"] = []
colheaders = ["file_name", "compile_success"]
for i in range(num_tests):
	data_dict[f"test_{i+1}_result"] = []
	colheaders.append(f"test_{i+1}_result")
for i in range(num_tests):
	data_dict[f"test_{i+1}_score"] = []
	colheaders.append(f"test_{i+1}_score")
colheaders.append("total_score")
colheaders.append("program_is_correct")


#Compiling the driver .c file
compile_result = subprocess.run(["gcc", "-c", f"{path_driver_no_extension}.c"], capture_output=True, text=True)
if compile_result.returncode != 0 :
	print("cannot create object file")
	#print(compile_result.stderr)
	sys.exit(0)

#Going through student files one by one and running the test cases
# Scoring is inflexible currently (if test case successful, 10 points, otherwise 0). This could be changed
for name in names:
	score = []
	data_dict["file_name"].append(name)
	file_name = name[len_path_student_files::]
	compile_result = None
	try:
		compile_result = subprocess.run(["gcc", name, f"{driver_name_no_extension}.o"], capture_output=True, text=True)
		if compile_result.returncode != 0 :
			print("cannot compile and link", file_name)
			for i in range(num_tests):
				data_dict[f"test_{i+1}_result"].append('-')
				data_dict[f"test_{i+1}_score"].append(0)
			data_dict["compile_success"].append(0)
			data_dict["total_score"].append(0)
			data_dict["program_is_correct"].append(0)
			continue
		else:
			data_dict["compile_success"].append(1)
	except Exception as e:
		print("Error during compilation but not compile time error.")
		print("\t", type(e))
		print("\t", e)
		for i in range(num_tests):
			data_dict[f"test_{i+1}_result"].append('-')
			data_dict[f"test_{i+1}_score"].append(0)
		data_dict["compile_success"].append(0)
		data_dict["total_score"].append(0)
		data_dict["program_is_correct"].append(0)
		continue

	test_counter = 0
	passed_all_test_cases = True
	for (test, res) in zip(test_file_pointers, results):
		test_counter += 1
		test.seek(0)
		try:
			test_result = subprocess.run(["./a.out"], stdin=test, capture_output=True, text=True, timeout=DEFAULT_TIMEOUT)
			if test_result.returncode != 0 :
				if test_result.returncode == -11:
					print(f"Segmentation fault in test case {test_counter}: ", file_name)
					data_dict[f"test_{test_counter}_result"].append('RS')
					data_dict[f"test_{test_counter}_score"].append(0)
					score.append(0)				
				else:
					print("cannot run : ", file_name)
					data_dict[f"test_{test_counter}_result"].append('R')
					data_dict[f"test_{test_counter}_score"].append(0)
					score.append(0)
				passed_all_test_cases = False
				continue
			else:
				if test_result.stdout.strip() == res:
					data_dict[f"test_{test_counter}_result"].append('P')
					data_dict[f"test_{test_counter}_score"].append(10)
					score.append(10)
				else:
					data_dict[f"test_{test_counter}_result"].append('O')
					data_dict[f"test_{test_counter}_score"].append(0)
					score.append(0)
					passed_all_test_cases = False
		except subprocess.TimeoutExpired:
			print(f"Timeout expired while running test case {test_counter}: ", file_name)
			data_dict[f"test_{test_counter}_result"].append('T')
			data_dict[f"test_{test_counter}_score"].append(0)
			score.append(0)
			passed_all_test_cases = False
		total_score = sum(score)
	data_dict["total_score"].append(total_score)
	if passed_all_test_cases:
		data_dict["program_is_correct"].append(1)
	else:
		data_dict["program_is_correct"].append(0)
	print(name, score, total_score)

#Remove a.out and driver object file
subprocess.run(["rm", "a.out", f"{driver_name_no_extension}.o"])

#Write data as a pandas dataframe into a csv file
eval_df = pd.DataFrame(data_dict, columns = colheaders)
eval_df.to_csv(f"{path_output_data}{output_file_name}")
print(f"Data has been saved as a csv file (path: {path_output_data}{output_file_name})")

#Close file pointers in test_file_pointers:
for i in test_file_pointers:
	i.close()
