class TreeConversionError(Exception):
	pass

class ASTNode:
	def __init__(self, node_type, label = None, parent = None, text = None): #only give text argument if node is a leaf
		self.type = node_type
		self.label = label
		self.parent = parent
		self.children = []
		self.text = text
	
	#Problem: keeping the hashes up to date. Must do one of the following
	#	guarantee that the tree is immutable after the creation function convert() is called so that the hash can be stored in each node
	#	recalculate the hash fully whenever it is required, do not store it.
	#The second approach is what we are using for now. Can change to the first approach if performance is an issue.
	def calculate_hash(self):
		child_hashes = tuple(child.calculate_hash() for child in self.children) 
		return hash((self.type, self.label, self.text, child_hashes))
	
	def to_dict(self):
		obj = {"type": self.type, "label": self.label, "text": self.text}
		if self.children:
			children = []
			for child in self.children:
				children.append(child.to_dict())
			obj["children"] = children
		return obj

class TSNodeCategory:
	#Check node-types.json from the tree-sitter-<language> repository to help classify the nodes. Leaves are listed at the bottom. 
	#	Hard rule for NAMED_REGULAR: If the node is a named node and is an internal type, it falls into this category. 
	#	Hard rule for NAMED_SAVE_TEXT: If the node is named and is a leaf type, it likely contains meaningful text and hence it goes in this category. Note: comments are named, but they are ignored.
	#	Soft rule for ANON_SAVE_TEXT: Typically includes literals and operators.
	#	Hard rule for IGNORE_THIS_NODE: comments and anonymous nodes which aren't in ANON_SAVE_TEXT.
	#Development note: It's possible that we have exceptions to the hard rules, but there are none as of now. 
	NAMED_REGULAR = 0
	NAMED_SAVE_TEXT = 1 
	ANON_SAVE_TEXT = 2
	IGNORE_THIS_NODE = 3


class Python_Language: #This needs to be updated to match the style of C_Language
	operators = ["!=", "%", "%=", "&", "&=", "*", "**", "**=", "*=", "+", "+=", "-", "-=", "->", ".", #do we keep the dot operator or not?
				"/", "//", "//=", "/=", ":=", "<", "<<", "<<=", "<=", "<>", "=", "==", ">", ">=", ">>", ">>=", "@", "@=", "^", "^=", "|", "|=", "~", 
				"and", "in", "is", "not", "or"]
	
	literals = ["false", "true", "float", "integer", "none"]
	
	def is_operator(self, node):
		return node.type in self.operators

	def is_literal(self, node):
		return node.type in self.literals

	def get_TS_node_category(self, node):
		if node.is_named:
			if node.type == "comment":
				return TSNodeCategory.IGNORE_THIS_NODE
			elif node.type == "identifier":
				return TSNodeCategory.NAMED_SAVE_TEXT
			else:
				return TSNodeCategory.NAMED_REGULAR
		else:
			if self.is_operator(node) or self.is_literal(node):
				return TSNodeCategory.ANON_SAVE_TEXT
			else:
				return TSNodeCategory.IGNORE_THIS_NODE

class C_Language:
	operators = ["!", "!=", "%", "%=", "&", "&&", "&=", "*", "*=", "+", "++", "+=", "-", "--", "-=", "->", ".", #do we keep the dot operator or not?
				"/", "/=", "<", "<<", "<<=", "<=", "=", "==", ">", ">=", ">>", ">>=", "^", "^=", "|", "|=", "||", "~"]

	literals = ["character", "escape_sequence", "false", "number_literal", "string_content", "system_lib_string", "true"]
	
	_named_leaves = ["comment", "character", "escape_sequence", "false", "number_literal", "string_content", "system_lib_string", "true", 
					 "field_identifier", "identifier", "ms_restrict_modifier", "ms_signed_ptr_modifier", "ms_unsigned_ptr_modifier", 
					 "preproc_arg", "preproc_directive", "primitive_type", "statement_identifier", "type_identifier"]
	
	def is_operator(self, node):
		return node.type in self.operators

	def is_literal(self, node):
		return node.type in self.literals

	def get_TS_node_category(self, node):
		if node.is_named:
			if node.type == "comment":
				return TSNodeCategory.IGNORE_THIS_NODE
			elif node.type in self._named_leaves:
				return TSNodeCategory.NAMED_SAVE_TEXT
			else:
				return TSNodeCategory.NAMED_REGULAR
		else:
			if self.is_operator(node) or self.is_literal(node):
				return TSNodeCategory.ANON_SAVE_TEXT
			else:
				return TSNodeCategory.IGNORE_THIS_NODE

	
def convert(TSCursor, parentNode, languageClass):
	#If you come across an internal node in the TSNodeCategory.IGNORE_THIS_NODE category, 
	#	do not create a node for it. Instead return a list of its children.
	#Edge case: If the root itself falls into this category, the list returned by this function will contain many nodes rather than just one.
	#	Not sure if this will ever occur, however.
	
	category = languageClass.get_TS_node_category(TSCursor.node)
	
	if category == TSNodeCategory.IGNORE_THIS_NODE:
		childNodes = []
		if TSCursor.goto_first_child():
			while True:
				childNodes.extend(convert(TSCursor, parentNode, languageClass))		
				if not TSCursor.goto_next_sibling():
					break
			TSCursor.goto_parent()
		return childNodes
	
	else:
		curNode = None
		if category == TSNodeCategory.NAMED_SAVE_TEXT:
			curNode = ASTNode(node_type = TSCursor.node.type, label = TSCursor.field_name, text = TSCursor.node.text.decode("utf-8"), parent = parentNode)
		elif category == TSNodeCategory.NAMED_REGULAR:
			curNode = ASTNode(node_type = TSCursor.node.type, label = TSCursor.field_name, parent = parentNode)
		elif category == TSNodeCategory.ANON_SAVE_TEXT:
			curNode = ASTNode(node_type = TSCursor.node.type, text = TSCursor.node.text.decode("utf-8"), parent = parentNode)
		else:
			raise TreeConversionError("Value of TSNodeCategory not recognized for this language")

		childNodes = []
		if TSCursor.goto_first_child():
			while True:
				childNodes.extend(convert(TSCursor, curNode, languageClass))
				if not TSCursor.goto_next_sibling():
					break
			TSCursor.goto_parent()

		curNode.children.extend(childNodes)
		return [curNode]

def convert_to_ast(TSCursor, language):
	if language.lower() == "c": 
		return convert(TSCursor, None, C_Language())
	elif language.lower() == "python":
		return convert(TSCursor, None, Python_Language())
	else:
		raise TreeConversionError("Unsupported language")
		
	
if __name__ == "__main__":
	print("This is the file which contains all material to convert a tree-sitter tree into our AST (which is a simplified and pruned version of the original tree).")
	