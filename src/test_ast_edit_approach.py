import sys
import os
from error_identifier.AST_Edit_Script_Processing import get_suggested_edits

#Check that command line arguments are given as expected
if len(sys.argv) != 3:
	print("Usage: python3 src/test_ast_edit_approach.py <path to incorrect .c code> <path to correct .c code> \n\tNote: do not enter slashes at beginning of file path")
	sys.exit(1)

cwd = os.getcwd()

print("----------------------------------------------------------------")	
print(f"Processing incorrect file")
#Querying joern (assume the server is already up)
print("\tCorrect: ", cwd + '/' + sys.argv[2])
print("\tIncorrect: ", cwd + '/' + sys.argv[1])
get_suggested_edits(path_wrong=cwd + '/' + sys.argv[1], path_correct=cwd + '/' + sys.argv[2])
print("----------------------------------------------------------------")
