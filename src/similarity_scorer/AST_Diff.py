import heapq as hq
from similarity_scorer.TSTree_to_AST import ASTNode

#Possible optimizations:
#   - instead of storing entire nodes in structures, keep a global nodes list and store indexes instead
#   - use a different data structure instead of a list for the mappings set M to improve search speed.

def get_descendants(node):
    nodes = [] + node.children
    for child in node.children:
        nodes.extend(get_descendants(child))
    return nodes


def GT_dice(mapping, parent1, parent2):
    descendants1 = get_descendants(parent1)
    descendants2 = get_descendants(parent2)
    mapped_pairs = 0
    for pair in mapping:
        if pair[0] in descendants1 and pair[1] in descendants2:
            mapped_pairs += 1
    return (2*mapped_pairs) / (len(descendants1) + len(descendants2))


def GT_candidate(node, mapping):
    best_node = None
    maxdice = -0.5
    for pair in mapping:
        if pair[0] == node and pair[1].type == node.type and pair[1].label == node.label: #added a type check here on top of the label check
            diceval = GT_dice(mapping, node.parent, pair[1].parent)
            if diceval > maxdice:
                maxdice = diceval
                best_node = pair[1]
    return best_node


def GT_pop(queue):
    neg_height = queue[0][0]
    nodes = []
    while queue and queue[0][0] == neg_height:
        nodes.append(hq.heappop(queue)[2])
    return nodes
    

def GT_top_down(tree1, tree2, minHeight = 2):
    #Note: Each element in the heapq is (-height, counter, node)
    #   The priority queue is a minheap, so to make it a maxheap, the priorities (heights) are made negative. This is why the comparisons are all inverted
    #   A counter is stored in this tuple because the ASTNode has no builtin comparison function. It is the fix suggested by the official docs (https://docs.python.org/3/library/heapq.html#priority-queue-implementation-notes)
    #   Preserving the order of insertion isn't really required by this algorithm, so the counter is stored as a positive number instead of a negative one.

    counter = 1
    A = []
    M = []
    L1 = [(-tree1.height, 0, tree1)]
    L2 = [(-tree2.height, 0, tree2)]
    hq.heapify(L1)
    hq.heapify(L2)
    while L1 and L2 and -max(L1[0][0], L2[0][0]) > minHeight:
        nodes = []
        if L1[0][0] != L2[0][0]:
            if L1[0][0] < L2[0][0]:
                nodes = GT_pop(L1)
                for node in nodes:
                    for child in node.children:
                        hq.heappush(L1, (-child.height, counter, child))
                        counter += 1
            else:
                nodes = GT_pop(L2)
                for node in nodes:
                    for child in node.children:
                        hq.heappush(L2, (-child.height, counter, child))
                        counter += 1
        else:
            nodes1 = GT_pop(L1)
            nodes2 = GT_pop(L2)
            isomorphic = []
            used1 = set()
            used2 = set()
            for i in range(len(nodes1)):
                hashval = nodes1[i].calc_structure_hash()
                for j in range(len(nodes2)):
                    if hashval == nodes2[j].calc_structure_hash():
                        isomorphic.append((i, j, hashval))
                        used1.add(i)
                        used2.add(j)

            while isomorphic:
                same = []
                pair = isomorphic.pop()
                for i in reversed(range(len(isomorphic))):
                    item = isomorphic[i]
                    if pair[2] == item[2] and ((pair[0] in item) or (pair[1] in item)):
                        same.append((item[0], item[1]))
                        del isomorphic[i]
                if same: 
                    A.append((nodes1[pair[0]], nodes2[pair[1]]))
                    for i in same:
                        A.append((nodes1[i[0]], nodes2[i[1]]))
                else:
                    descendants1 = get_descendants(nodes1[pair[0]])
                    descendants2 = get_descendants(nodes2[pair[1]])
                    for i in range(len(descendants1)):
                        M.append((descendants1[i], descendants2[i]))
            
            for i in range(len(nodes1)):
                if i not in used1:
                    for child in nodes1[i].children:
                        hq.heappush(L1, (-child.height, counter, child))
                        counter += 1
            for i in range(len(nodes2)):
                if i not in used2:
                    for child in nodes2[i].children:
                        hq.heappush(L2, (-child.height, counter, child))
                        counter += 1

    A.sort(key = lambda pair: GT_dice(M, pair[0].parent, pair[1].parent)) 
    while A:
        pair = A.pop()
        descendants1 = get_descendants(pair[0])
        descendants2 = get_descendants(pair[1])
        for i in range(len(descendants1)):
            M.append((descendants1[i], descendants2[i]))
        for i in reversed(range(len(A))):
            if A[i][0] == pair[0] or A[i][1] == pair[1]:
                del A[i]

    return M

def GT_bottom_up(tree1, tree2, M, minDice = 0.5, maxSize = 100):
    pass    

if __name__ == "__main__":
    print("This file is an implementation of the GumTree algorithm for diffing two ASTNode trees.")

