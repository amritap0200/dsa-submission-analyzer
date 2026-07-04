import tree_sitter_c as tsc
from tree_sitter import Language, Parser
import json
import sys
from TSTree_to_Intermediate_AST import convert_to_intermediateAST

#Check that command line arguments are given as expected
if len(sys.argv) != 3:
	print("Usage: python3 ast_diff.py <path to correct .c code> <path to incorrect .c code>")
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

#Before passing the text into the parser.parse() function, we have to make sure they don't have any extra spaces.
#	Otherwise the hashes of two nodes will be different even if they have the exact same content save for the white spaces
correct_code = ' '.join(correct_code.split())
incorrect_code = ' '.join(incorrect_code.split())

#Parse the code into a tree sitter tree
tree1 = parser.parse(bytes(correct_code, "utf-8"))
tree2 = parser.parse(bytes(incorrect_code, "utf-8"))
root1 = tree1.root_node
root2 = tree2.root_node

#Convert the tree into intermediate ASTNode representation
cursor1 = root1.walk()
intermediate1 = convert_to_intermediateAST(cursor1, "c")[0]
cursor2 = root2.walk()
intermediate2 = convert_to_intermediateAST(cursor2, "c")[0]
print("Correct AST:")
print(json.dumps(intermediate1.to_dict(), indent=4))
print("------------------------\n")
print("Incorrect AST:")
print(json.dumps(intermediate1.to_dict(), indent=4))
print("------------------------\n")

#TODO: Implement the diffing of the two trees by following a simplified version of the GumTree algorithm.



