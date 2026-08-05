import tree_sitter_c as tsc
from tree_sitter import Language, Parser
import json
import sys
from similarity_scorer.TSTree_to_AST import convert_to_ast
import similarity_scorer.AST_Similarity_Score as SS

#Check that command line arguments are given as expected
if len(sys.argv) != 3:
	print("Usage: python3 src/test_custom_gumtree.py <path to correct .c code> <path to incorrect .c code>")
	sys.exit(1)

#Set language
C_LANGUAGE = Language(tsc.language())

#Create parser using language
parser = Parser(C_LANGUAGE)

#Read the two C files to compare.
file = open(sys.argv[1], 'r')
correct_code = file.read()
print("File 1 (correct) contents:")
print(correct_code)
print("------------------------\n")
file = open(sys.argv[2], 'r')
incorrect_code = file.read()
print("File 2 (incorrect) contents:")
print(incorrect_code)
print("------------------------\n")

#Parse the code into a tree sitter tree
tree1 = parser.parse(bytes(correct_code, "utf-8"))
tree2 = parser.parse(bytes(incorrect_code, "utf-8"))
root1 = tree1.root_node
root2 = tree2.root_node

#Convert the tree into ASTNode representation
cursor1 = root1.walk()
ast1 = convert_to_ast(cursor1, "c")
cursor2 = root2.walk()
ast2 = convert_to_ast(cursor2, "c")

print("Correct AST:")
print(json.dumps(ast1.to_dict(), indent=4))
print("------------------------\n")
print("Incorrect AST:")
print(json.dumps(ast2.to_dict(), indent=4))
print("------------------------\n")

#Run custom gumtree implementation
mapping = SS.GT_top_down(ast1, ast2)
print("Number of mapped pairs before bottom up: ", len(mapping))
SS.GT_bottom_up(mapping, ast1, ast2, minDice = 0.5)
score = SS.GT_dice(mapping, ast1, ast2)	

#Pring results
for i in mapping:
	print("MAPPED PAIR: ")
	print(json.dumps(i[0].to_dict_no_children(), indent=4))
	print(json.dumps(i[1].to_dict_no_children(), indent=4))
	print("---")

print("Number of mapped pairs: ", len(mapping))
print("Number of nodes in tree1: ", len(SS.get_descendants(ast1)))
print("Number of nodes in tree2: ", len(SS.get_descendants(ast2)))

print("Naive similarity: ", SS.get_naive_similarity_score(ast1, ast2))
print("Dice similarity score is: ", score)

