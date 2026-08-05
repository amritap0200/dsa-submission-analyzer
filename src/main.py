import sys
import pandas as pd
import json
import tree_sitter_c as tsc
from tree_sitter import Language, Parser
from similarity_scorer.TSTree_to_AST import convert_to_ast
from similarity_scorer.AST_Similarity_Score import get_naive_similarity_score, get_dice_similarity_score
from error_identifier.AST_Edit_Script_Processing import get_suggested_edits

def find_best_match(correct_submissions, wrong_code_path, min_naive_similarity=0.9):
    #Read the incorrect C file and parse it into a tree sitter tree, then to ASTnode representation.
    wrong_code = None
    try:
        with open(wrong_code_path, 'r') as fp:
            wrong_code = fp.read().strip()
    except UnicodeDecodeError as e:
        print("\tUnicodeDecodeError has been found")
        print(f"\t{e}")
        return None
    wrong_ts_tree = parser.parse(bytes(wrong_code, "ascii"))
    wrong_ASTNode = convert_to_ast(wrong_ts_tree.root_node.walk(), "c")

    possible_matches = []
    for i in correct_submissions:
        correct_code = None
        with open(i, 'r', encoding = "ascii") as fp:
            correct_code = fp.read().strip()
        correct_ts_tree = parser.parse(bytes(correct_code, "ascii"))
        correct_ASTNode = convert_to_ast(correct_ts_tree.root_node.walk(), "c")
        score = get_naive_similarity_score(correct_ASTNode, wrong_ASTNode)
        if score >= min_naive_similarity:
            possible_matches.append((i, correct_ASTNode, score))
    
    possible_matches.sort(key = lambda item: get_dice_similarity_score(item[1], wrong_ASTNode), reverse=True)
    if possible_matches:
        print("Best match found: ", possible_matches[0][0], "with naive similarity", possible_matches[0][2], "and dice similarity", get_dice_similarity_score(possible_matches[0][1], wrong_ASTNode))
        return possible_matches[0][0]
    else:
        return None

#Change the below variables to have this program run for all the different weeks of data
path_data_file = "./artifacts/submission_data_week1.csv"
path_output_data = "./artifacts/"

#Check that command line arguments are given as expected
'''
if len(sys.argv) != 2:
	print("Usage: python3 src/newmain.py <absolute path to incorrect .c code>")
	sys.exit(1)
'''

#Set language
C_LANGUAGE = Language(tsc.language())

#Create parser using language
parser = Parser(C_LANGUAGE)

#Getting names of correct and incorrect programs from the data csv file:
df = pd.read_csv(path_data_file)
correct_submissions = df[df["program_is_correct"] == 1].to_dict(orient="list")["file_name"]
incorrect_submissions = df[(df["program_is_correct"] == 0) & (df["compile_success"] == 1)].to_dict(orient="list")["file_name"]

'''
#If the file given is not in incorrect_submissions, we don't know if it's wrong or correct.
#   We could verify it, but we'll just reject for now.
#   TODO: uncomment this part when you've finished testing.
if sys.argv[1] not in incorrect_submissions:
    print("This file is not found in the incorrect submissions. Exiting.")
    sys.exit(0)
'''

min_naive_similarity = 0.8
print("Total incorrect submissions: ", len(incorrect_submissions))
print()
counter = 1
for i in incorrect_submissions:
    print("----------------------------------------------------------------")	
    print(f"Processing incorrect file {counter}")			
    best_match = find_best_match(correct_submissions, i, min_naive_similarity=min_naive_similarity)
    
    #Querying joern (assume the server is already up)
    if best_match:
        print("Match found, querying joern. Paths of files are: ")
        print("\tCorrect: ", best_match)
        print("\tIncorrect: ", i)
        get_suggested_edits(path_wrong=i, path_correct=best_match)
    else:
        print(f"No matches found for file {i} with naive similarity above {min_naive_similarity}.")
    print("----------------------------------------------------------------")
    print()
    print()
    counter += 1				
