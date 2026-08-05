import pandas as pd
import numpy as np

#Refer to eval.py for the structure of the output CSV file for evaluation results

#Change the below variables to have this program run for all the different weeks of data
path_data_file = "./artifacts/submission_data_week3.csv"
path_output_data = "./artifacts/"
MAX_SCORE = 30

df = pd.read_csv(path_data_file)

#Finding number of test cases
num_tests = 0
colheaders = list(df.columns)
for i in colheaders:
	if '_result' in i:
		num_tests += 1
print(f"Number of test cases: {num_tests}")
#General data
tot_submissions = df.shape[0]
print("Total submissions: ", tot_submissions)
print(f"Maximum score possible: {MAX_SCORE}")
print("Average score: ", df["total_score"].mean())
num_correct_programs =  (df["program_is_correct"] == 1).sum()
print(f"Number of people who passed all test cases: {num_correct_programs} (~{round(num_correct_programs / tot_submissions * 100, 2)}%)")
print("Compilation errors: ", (df["compile_success"] == 0).sum())

#Test failure data
print("Test failure counts: ")
fail_counts = []
non_segfault_runtime_errors = []; output_mismatches = []; timeouts_exceeded = []; segmentation_faults = []; unknown_errors = []; 
for i in range(1, num_tests+1, 1):
	fail_counts.append((df[f"test_{i}_result"] != "P").sum())
	non_segfault_runtime_errors.append((df[f"test_{i}_result"] == "R").sum())
	segmentation_faults.append((df[f"test_{i}_result"] == "RS").sum())
	output_mismatches.append((df[f"test_{i}_result"] == "O").sum())
	timeouts_exceeded.append((df[f"test_{i}_result"] == "T").sum())
	unknown_errors.append((df[f"test_{i}_result"] == "U").sum())
	print(f"\tTest {i}: {fail_counts[i-1]} (~{round(fail_counts[i-1] / tot_submissions * 100, 2)}%)")
	print("\t\tTotal runtime errors: ", non_segfault_runtime_errors[i-1] + segmentation_faults[i-1] + timeouts_exceeded[i-1])
	print("\t\t\tSegmentation faults: ", segmentation_faults[i-1])
	print("\t\t\tTimeouts exceeded: ", timeouts_exceeded[i-1])
	print("\t\tOutput mismatches: ", output_mismatches[i-1])
	print("\t\tUnknown errors: ", unknown_errors[i-1])
print(f"\tTotal test case failures: {sum(fail_counts)} (~{round(sum(fail_counts) / (num_tests*tot_submissions) * 100, 2)}%)")