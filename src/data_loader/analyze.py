import os
import glob
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#Refer to eval.py for the structure of the output CSV file for evaluation results

#Change the below variables to have this program run for all the different weeks of data
path_data_file = "./submission_data.csv"
path_output_data = "./"
output_plot_file = "week1.png"
max_score = 40

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
print("Average score: ", df["total_score"].mean())
print(f"Number of people who passed all test cases: {(df["total_score"] == max_score).sum()} (~{round((df["total_score"] == max_score).sum() / tot_submissions * 100, 2)}%)") #we have assumed for now that passing a test case means you get full marks
print("Compilation errors: ", (df["compile_success"] == 0).sum())

#Test failure data
print("Test failure counts: ")
fail_counts = []
runtime_errors = []; output_mismatches = []; compilation_errors = []; bar_graph_labels = [] #these lists are being created for bar graph plotting purposes
for i in range(1, num_tests+1, 1):
	bar_graph_labels.append(f"Test {i}")
	fail_counts.append((df[f"test_{i}_result"] != "P").sum())
	runtime_errors.append((df[f"test_{i}_result"] == "R").sum())
	output_mismatches.append((df[f"test_{i}_result"] == "O").sum())
	compilation_errors.append((df[f"test_{i}_result"] == "-").sum())
	print(f"\tTest {i}: {fail_counts[i-1]} (~{round(fail_counts[i-1] / tot_submissions * 100, 2)}%)")
	print("\t\tRuntime errors: ", runtime_errors[i-1])
	print("\t\tOutput mismatches: ", output_mismatches[i-1])
print(f"\tTotal test case failures: {sum(fail_counts)} (~{round(sum(fail_counts) / (num_tests*tot_submissions) * 100, 2)}%)")

#Plotting the data
bar_graph_data = {"runtime_errors": np.array(runtime_errors), "output_mismatches": np.array(output_mismatches), "compilation_errors": np.array(compilation_errors)}
fig, ax = plt.subplots()
fig.suptitle("Week 1 test case failures")
bottom = np.zeros(num_tests)
for (key, value) in bar_graph_data.items():
	ax.bar(bar_graph_labels, value, label = key, bottom = bottom)
	bottom += value
ax.legend()

'''
#Saving plot to an image file
fig.savefig(f"{path_output_data}{output_plot_file}")
print(f"This information has been plotted and saved as an image (path: {path_output_data}{output_plot_file})")
print("Program finished")
'''