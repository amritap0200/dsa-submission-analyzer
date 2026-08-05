import json
import os
import sys
import subprocess
from cpgqls_client import CPGQLSClient
import re
from bisect import bisect_right 

def get_line_and_col(line_ranges, offset_to_search):
	#Joern uses 1-based indexing
	line = bisect_right(line_ranges, offset_to_search)
	return (line, offset_to_search - line_ranges[line-1] + 1) #problem: non-ASCII characters will throw off the column calculation. Hence we should force everything to be in ascii for now.
		
def get_joern_jsonPretty_query_result(client, command): #Expected format of value: string wrapped in triple quotes ("""<string>""") only. Must use toJsonPretty in command.
	#print("----------------Joern traversal command: ", )
	#print(command)
	nodes = client.execute(command)["stdout"]
	#print("---------------------------Joern command stdout result: ", )
	#print(nodes)
	nodes = nodes[nodes.find("=")+5:len(nodes) - 4:]
	#print("---------------------------Joern command stdout result stripped: ", )
	#print(nodes)
	nodes = json.loads(nodes)
	return nodes

def get_joern_scalaString_query_result(client, command):
	#print("----------------Joern traversal command: ", )
	#print(command)
	nodes = client.execute(command)["stdout"]
	#print("---------------------------Joern command stdout result: ", )
	#print(nodes)
	nodes = nodes[nodes.find("=")+3:len(nodes) - 2:]
	#print(nodes)
	nodes = json.loads(nodes)
	return nodes

#Paths to executables
GUMTREE = "/home/sam/Programming/DAA_IDE/gumtree-4.0.0-beta7/bin/gumtree"
JOERN = "/home/sam/Programming/DAA_IDE/joern-4.0.579/joern"
CPGGEN_C = "/home/sam/Programming/DAA_IDE/joern-4.0.579/c2cpg.sh"

def get_suggested_edits(path_wrong, path_correct):
	#Reading the pair of programs
	code_correct = ""
	code_wrong = ""
	try:
		with open(path_correct, 'r', encoding="ascii", newline="") as file:
			code_correct = file.read()
		with open(path_wrong, 'r', encoding="ascii", newline="") as file:
			code_wrong = file.read()
	except UnicodeDecodeError as e:
		print("\tUnicodeDecodeError has been found")
		print(f"\t{e}")
		return

	#Write gumtree diff output into a file and read that file
	path_tmp_editscript = "./tmp_script.txt"	
	process_result = subprocess.run([GUMTREE, "textdiff", "-f", "JSON", path_wrong, path_correct], capture_output=True, text=True)
	gumtree_output = json.loads(process_result.stdout)
	#print("----------------Gumtree output")
	#print(json.dumps(gumtree_output, indent=4))

		
	#For translating bytes to line numbers 
	line_ranges_wrong = []
	cur = 0
	for line in code_wrong.splitlines(keepends=True):
		line_ranges_wrong.append(cur)
		cur += len(line)

	#Getting relevant edits from the script:
	rewrites = []
	inserts = []
	deletes = [] #ignore move-tree, move-node and update-node for now
	for i in gumtree_output["actions"]:
		if i["action"] in ["insert-node", "insert-tree"]:
			if i["tree"][:7:] == "comment":
				continue
			(typ, text, dest_startbyte, dest_endbyte) = (None,)*4
			m = re.fullmatch(r"(.+?):\s*(.+)\s+\[(\d+),\s*(\d+)\]", i["tree"])
			if m:
				(typ, text, dest_startbyte, dest_endbyte) = m.groups()
			else:
				m = re.fullmatch(r"(.+?) \[(\d+),\s*(\d+)\]", i["tree"])
				(typ, dest_startbyte, dest_endbyte) = m.groups()
			(p_typ, p_startbyte, p_endbyte) = re.fullmatch(r"(.+?) \[(\d+),\s*(\d+)\]", i["parent"]).groups()
			inserts.append({"type": typ, "text": text,
							"desttree_byterange": (int(dest_startbyte), int(dest_endbyte)),
						"parent_type": p_typ, "parent_byterange": (int(p_startbyte), int(p_endbyte))
						})
		elif i["action"] in ["delete-node", "delete-tree"]:
			if i["tree"][:7:] == "comment":
				continue
			(typ, text, startbyte, endbyte) = (None,)*4
			m = re.fullmatch(r"(.+?):\s*(.+)\s+\[(\d+),\s*(\d+)\]", i["tree"])
			if m:
				(typ, text, startbyte, endbyte) = m.groups()
			else:
				m = re.fullmatch(r"(.+?) \[(\d+),\s*(\d+)\]", i["tree"])
				(typ, startbyte, endbyte) = m.groups()
			deletes.append({"type": typ, "text":text, "byterange": (int(startbyte), int(endbyte))})

	#Find overlapping inserts and deletes
	for i in deletes:
		for j in inserts:
			if j["parent_byterange"][0] <= i["byterange"][0] and i["byterange"][1] <= j["parent_byterange"][1]:
				rewrites.append({"old_type": i["type"], "new_type": j["type"], 
								"old_text": i["text"], "new_text": j["text"],
								"delete_byterange" : i["byterange"],
								"parent_type" : j["parent_type"],
								"parent_byterange" : j["parent_byterange"]
								})
	#print("----------------Rewrites found from gumtree edit script: ", len(rewrites))
	#print(json.dumps(rewrites, indent=4))
		
	#JOERN SCRIPT
	#assume server is already on for now (all it takes is running "joern --server")
	server_endpoint = "localhost:8080"
	client = CPGQLSClient(server_endpoint)
	res = client.execute(f"importCode(\"{path_wrong}\", \"wrong\")") #rather than opening the code, generate the cpg and then open the cpg directly
	C_operators = ["!", "!=", "%", "%=", "&", "&&", "&=", "*", "*=", "+", "++", "+=", "-", "--", "-=", #removed dot and pointer dereferencing operator
					"/", "/=", "<", "<<", "<<=", "<=", "=", "==", ">", ">=", ">>", ">>=", "^", "^=", "|", "|=", "||", "~"] #note: ternary operators come wrapped as type = "conditional_expression" in gumtree and name="<operator>.conditional" in joern.
	C_ops_to_Joern_ops = {"!" : "<operator>.logicalNot", "!=" : "<operator>.notEquals", "%" : "<operator>.modulo", "%=" : "<operators>.assignmentModulo",  #-> : "<operator>.indirectFieldAccess",
						"&" : "<operator>.and", "&&" : "<operator>.logicalAnd", "&=" : "<operators>.assignmentAnd", "*" : "<operator>.multiplication", 
						"*=" : "<operator>.assignmentMultiplication", "+" : "<operator>.addition", "++" : "<operator>.postIncrement", "+=" : "<operator>.assignmentPlus", 
						"-" : "<operator>.subtraction", "--" : "<operator>.postDecrement", "-=" : "<operator>.assignmentMinus", "/": "<operator>.division", 
						"/=": "<operator>.assignmentDivision", "<":"<operator>.lessThan", "<<":"<operator>.shiftLeft", "<<=": "<operators>.assignmentShiftLeft", 
						"<=" : "<operator>.lessEqualsThan", "=": "<operator>.assignment", "==" : "<operator>.equals", ">": "<operator>.greaterThan", ">=":"<operator>.greaterEqualsThan", 
						">>": "<operator>.arithmeticShiftRight", ">>=" : "<operators>.assignmentArithmeticShiftRight", "^": "<operator>.xor", "^=" : "<operators>.assignmentXor", 
						"|" : "<operator>.or", "|=": "<operators>.assignmentOr", "||" : "<operator>.logicalOr", "~" : "<operator>.not"} #note: ternary operators come wrapped as conditional_expression in gumtree.

	print("==========SUGGESTIONS==========")

	for i in rewrites:
		if i["old_text"] in C_operators and i["new_text"] in C_operators:
			#get parent instead of child, because the operator itself doesn't have its own node in joern. It is part of a larger node which includes the arguments of the operator.
			(line, col) = get_line_and_col(line_ranges_wrong, i["parent_byterange"][0])
			nodes = get_joern_jsonPretty_query_result(client, f"cpg.file.ast.filter {{ n => n.lineNumber.contains({line}) && n.columnNumber.contains({col})}}.map(node => Map(\"_id\" -> node.id, \"code\" -> node.code)).toJsonPretty")
			node = None
			for j in nodes: #filter out the nodes which may have the same start but don't span the same length (we want the biggest node in the given range)
				if len(j["code"]) == i["parent_byterange"][1] - i["parent_byterange"][0]:
					node = j
					break
			#Check if operator is enclosed inside a controlStructure condition
			checkInControlStructure = get_joern_jsonPretty_query_result(client, f"cpg.call.filter{{_.id == {node["_id"]}L}}.repeat(_.astParent)(_.until(_.isControlStructure)).headOption.toJsonPretty")
			if checkInControlStructure:
				controlstructure_id = checkInControlStructure[0]["_id"]
				res = get_joern_scalaString_query_result(client, f"cpg.controlStructure.filter{{_.id == {controlstructure_id}L}}.condition.ast.exists(_.id == {node["_id"]}L).toString")
				if res:
					print(f"::::Line {line}: possible incorrect condition in control structure {checkInControlStructure[0]["controlStructureType"]} ({i["old_text"]} instead of {i["new_text"]})")
			
			#Check if operator is enclosed in an assignment's value
			checkInAssignment = get_joern_jsonPretty_query_result(client, f"cpg.call.filter{{_.id == {node["_id"]}L}}.repeat(_.astParent)(_.until(n => n.isCall.isAssignment)).headOption.toJsonPretty")
			if checkInAssignment:
				print(f"::::Line {line}: possible incorrect operator in RHS of assignment ({i["old_text"]} instead of {i["new_text"]})")
			
			#Check if operator is an assignment
			checkAssignment = get_joern_jsonPretty_query_result(client, f"cpg.assignment.filter{{_.id == {node["_id"]}L}}.headOption.toJsonPretty")
			if checkAssignment:
				print(f"::::Line {line}: possible incorrect assignment operator used ({i["old_text"]} instead of {i["new_text"]})")
			
			#Check if operator is inside a return statement
			checkInReturn = get_joern_jsonPretty_query_result(client, f"cpg.file.ast.filter{{_.id == {node["_id"]}L}}.repeat(_.astParent)(_.until(_.isReturn)).headOption.toJsonPretty")
			if checkInReturn:
				print(f"::::Line {line}: possible incorrect operator used in return expression ({i["old_text"]} instead of {i["new_text"]})")

		elif i["parent_type"] == "return_statement":
			#Targetting return statement now. In this case, we already know the parent is a return statement, so no need to query Joern.
			(line, col) = get_line_and_col(line_ranges_wrong, i["parent_byterange"][0])
			print(f"::::Line {line}: possible incorrect return expression")

		elif i["old_type"] ==  "expression_statement" and i["new_type"] == "expression_statement":
			#Targetting assignments now. Assignment sites are still call nodes.
			(line, col) = get_line_and_col(line_ranges_wrong, i["delete_byterange"][0])
			nodes = None
			nodes = get_joern_jsonPretty_query_result(client, f"cpg.file.ast.filter {{ n => n.lineNumber.contains({line}) && n.columnNumber.contains({col})}}.map(node => Map(\"_id\" -> node.id, \"code\" -> node.code)).toJsonPretty")
			node = None
			for j in nodes:
				if len(j["code"]) == i["delete_byterange"][1] - i["delete_byterange"][0] - 1: #byterange includes the semicolon but the code does not, so subtract 1
					node = j
					break
			#Check if expression is an assignment
			checkAssignment = get_joern_jsonPretty_query_result(client, f"cpg.assignment.filter{{_.id == {node["_id"]}L}}.headOption.toJsonPretty")
			if checkAssignment:
				print(f"::::Line {line}: possible incorrect assignment")
		
		elif i["old_type"] ==  "parenthesized_expression" and i["new_type"] == "parenthesized_expression":
			#Targetting assignments now. Assignment sites are still call nodes.
			(line, col) = get_line_and_col(line_ranges_wrong, i["delete_byterange"][0])
			#If it's a parenthesized expression, the parentheses are removed in the Joern AST's code attribute. You have to query with col+1
			nodes = get_joern_jsonPretty_query_result(client, f"cpg.file.ast.filter {{ n => n.lineNumber.contains({line}) && n.columnNumber.contains({col+1})}}.map(node => Map(\"_id\" -> node.id, \"code\" -> node.code)).toJsonPretty")	
			node = None
			for j in nodes:
				if len(j["code"]) == i["delete_byterange"][1] - i["delete_byterange"][0] - 2: #byterange includes the parentheses but the code does not, so subtract 2
					node = j
					break
			#Check if expression is an assignment
			checkAssignment = get_joern_jsonPretty_query_result(client, f"cpg.assignment.filter{{_.id == {node["_id"]}L}}.headOption.toJsonPretty")
			if checkAssignment:
				print(f"::::Line {line}: possible incorrect assignment")
	

		elif i["parent_type"] == "parenthesized_expression":
			#Targetting returns now.
			(line, col) = get_line_and_col(line_ranges_wrong, i["parent_byterange"][0]) #we are traversing upwards until we find a return, so get the parent now itself
			#If it's a parenthesized expression, the parentheses are removed in the Joern AST's code attribute. You have to query with col+1
			nodes = get_joern_jsonPretty_query_result(client, f"cpg.file.ast.filter {{ n => n.lineNumber.contains({line}) && n.columnNumber.contains({col+1})}}.map(node => Map(\"_id\" -> node.id, \"code\" -> node.code)).toJsonPretty")	
			node = None
			for j in nodes:
				if len(j["code"]) == i["parent_byterange"][1] - i["parent_byterange"][0] - 2: #byterange includes the parentheses but the code does not, so subtract 2
					node = j
					break
			#Check if expression is inside a return
			checkInReturn = get_joern_jsonPretty_query_result(client, f"cpg.file.ast.filter{{_.id == {node["_id"]}L}}.repeat(_.astParent)(_.until(_.isReturn)).headOption.toJsonPretty")
			if checkInReturn:
				print(f"::::Line {line}: possible incorrect return expression")
		
		elif "_expression" in i["parent_type"]: #a few possible values for this case are call_expression, parenthesized_expression (which has been covered above), and binary_expression
			#Targetting returns now.
			(line, col) = get_line_and_col(line_ranges_wrong, i["parent_byterange"][0]) #we are traversing upwards until we find a return, so get the parent now itself
			nodes = get_joern_jsonPretty_query_result(client, f"cpg.file.ast.filter {{ n => n.lineNumber.contains({line}) && n.columnNumber.contains({col})}}.map(node => Map(\"_id\" -> node.id, \"code\" -> node.code)).toJsonPretty")	
			if not nodes:
				continue
			node = None
			for j in nodes:
				if len(j["code"]) == i["parent_byterange"][1] - i["parent_byterange"][0]:
					node = j
					break
			if not node:
				continue
			#Check if expression is inside a return
			checkInReturn = get_joern_jsonPretty_query_result(client, f"cpg.file.ast.filter{{_.id == {node["_id"]}L}}.repeat(_.astParent)(_.until(_.isReturn)).headOption.toJsonPretty")
			if checkInReturn:
				print(f"::::Line {line}: possible incorrect return expression")			
				

	res = client.execute("delete(\"wrong\")") #rather than opening the code, generate the cpg and then open the cpg directly
		#TODO: Go through the matched nodes for identifiers, log the matches so that you can look them up. 
		#	Then, when there is an update-node action, check if the updation is just from the old variable to the new one
		# 	If so, ignore
		#	Else: the variable here has changed. Go into joern and figure out where this is, then print an error message
	
