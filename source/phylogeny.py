import math
from Bio import Phylo
from cStringIO import StringIO
from itertools import product


class Phylogeny:
    def __init__(self, newick_string):
        self.tree = Phylo.read(StringIO(newick_string), "newick")
        self.validate_tree()


    def validate_tree(self):
        #TODO: validation here
        pass


    def estimate_tree(self, adjacencies):
        new_tree = reconstruct_tree(self.tree, adjacencies)
        return max_likelihood_score(new_tree)


def reconstruct_tree(tree, adjacencies):
    def tree_helper(node):
        if node.is_terminal():
            if node.name in adjacencies:
                new_clade = Phylo.Newick.Clade()
                new_clade.comment = [adjacencies[node.name]]
                new_clade.name = node.name
                new_clade.branch_length = node.branch_length
                return new_clade
            else:
                return None

        subnodes = map(tree_helper, node.clades)
        subnodes = filter(lambda n : n, subnodes)
        if not subnodes:
            return None
        elif len(subnodes) == 1:
            subnodes[0].branch_length += node.branch_length
            return subnodes[0]
        else:
            new_clade = Phylo.Newick.Clade()
            new_clade.clades = subnodes
            new_clade.branch_length = node.branch_length
            return new_clade

    return tree_helper(tree.clade)


def print_tree(root, depth=0):
    print "\t" * depth, "({0}, {1}, {2})".format(root.name, root.branch_length, root.comment)
    for clade in root.clades:
        print_tree(clade, depth + 1)


def tree_to_dot(root, dot_file):
    last_vid = [0]

    dot_file.write("digraph {\n")
    edges_buf = StringIO()

    def dot_rec(node, node_id):
        for clade in node.clades:
            last_vid[0] += 1
            edges_buf.write("{0} -> {1} [label=\"{2}\"];\n".format(node_id, last_vid[0], clade.branch_length))

            label = str(clade.comment) + " " + (clade.name if clade.name else "")
            dot_file.write("{0} [label=\"{1}\"];\n".format(last_vid[0], label))
            dot_rec(clade, last_vid[0])

    dot_rec(root, last_vid[0])
    dot_file.write(edges_buf.getvalue())
    dot_file.write("}\n")


def intersection(first, *others):
    return set(first).intersection(*others)


def go_up(root):
    if root.is_terminal():
        return root.comment

    value_lists = []
    for clade in root.clades:
        value_lists.append(go_up(clade))
    intersect = list(intersection(*value_lists))

    if intersect:
        root.comment = intersect
    else:
        root.comment = sum(value_lists, [])
    return root.comment


def go_down(root):
    for clade in root.clades:
        intersect = [l for l in clade.comment if l in root.comment]
        if intersect:
            clade.comment = intersect
        go_down(clade)


def subs_cost(v1, v2, length):
    #MU = 0.01
    MU = 1
    length = max(length, 0.0000001)
    if v1 == v2:
        #return -MU * length
        return 0
    else:
        #print math.log(1 - math.exp(-MU * length))
        #return math.log(1 - math.exp(-MU * length))
        return 1 - math.exp(-MU * length)


def tree_likelihood(root):
    prob = 0.0
    nbreaks = 0
    for clade in root.clades:
        subtree_likelihood, subtree_nbreaks = tree_likelihood(clade)
        subtree_prob = (subtree_likelihood +
                        subs_cost(root.comment[0], clade.comment[0], clade.branch_length))
        prob += subtree_prob
        if root.comment[0] != clade.comment[0]:
            nbreaks += 1
    return prob, nbreaks


def enumerate_trees(root):
    child_trees = []
    for clade in root.clades:
        child_trees.append(enumerate_trees(clade))

    trees = []
    for val in root.comment:
        if root.is_terminal():
            clade = Phylo.Newick.Clade()
            clade.comment = [val]
            clade.name = root.name
            trees.append(clade)
            continue

        for children in product(*child_trees):
            clade = Phylo.Newick.Clade()
            for i, child in enumerate(children):
                clade.clades.append(child)
                clade.clades[-1].branch_length = root.clades[i].branch_length
            clade.comment = [val]
            trees.append(clade)
    return trees


def max_likelihood_score(tree):
    #print_tree(tree.clade)
    go_up(tree)
    go_down(tree)
    #print_tree(tree.clade)
    max_score = float("-inf")
    max_tree = None
    min_breaks = None
    for t in enumerate_trees(tree):
        #print_tree(t)
        likelihood, nbreaks = tree_likelihood(t)
        #print likelihood

        if likelihood > max_score:
            max_score = likelihood
            max_tree = t
            min_breaks = nbreaks

    return max_score, min_breaks, max_tree


def test():
    p = Phylogeny("((A:0.1,B:0.1):0.1,(C:0.1,D:0.1):0.1);")
    adjacencies = {"A" : "1", "B" : "1", "C" : "2", "D" : "2"}
    p.estimate_adjacency(adjacencies)


if __name__ == "__main__":
    test()