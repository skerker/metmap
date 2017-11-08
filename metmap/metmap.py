from random import choice, shuffle
from Bio import SeqIO, SeqRecord, SeqFeature, Seq

# IUPAC nucleotide code
dnc = {
    'R': ['A', 'G'],
    'Y': ['C', 'T'],
    'S': ['G', 'C'],
    'W': ['A', 'T'],
    'K': ['G', 'T'],
    'M': ['A', 'C'],
    'B': ['C', 'G', 'T'],
    'D': ['A', 'G', 'T'],
    'H': ['A', 'C', 'T'],
    'V': ['A', 'C', 'G'],
    'N': ['A', 'T', 'C', 'G']
}


def calculate_number_of_possible_variants(seq: str) -> int:
    """

    :param seq:
    :return:
    """
    res = 1
    for x in [len(dnc[x]) for x in seq if x in dnc]:
        res *= x
    return res


def deambigulate_random(seq: str) -> str:
    """
    Create 1 random variant of seq
    :param seq: A DNA sequence using ATCG or IUPAC degenerate code
    :return: a random deambigulated version of seq
    """
    return "".join([n if n in dnc['N'] else choice(dnc[n]) for n in seq.upper()])


def pick_n_random_without_duplicates(seq: str, n: int) -> set:
    # sanity check
    max_variants = calculate_number_of_possible_variants(seq)
    if max_variants < n:
        raise ValueError(f"I can't possibly find {n} unique variants of {seq}. {max_variants} is max.")
    elif max_variants == n:
        return deambigulate_all(seq)
    else:
        picks = set()
        while len(picks) != n:
            picks.add(deambigulate_random(seq))
        return picks


def deambigulate_all(seq: str, start_pos: int = 0) -> list:
    """
    create all variants of seq
    :param seq: A DNA sequence using ATCG or IUPAC degenerate code
    :param start_pos: Used in the iterative process
    :return: A list of all variants
    """
    for i, nuc in enumerate(seq[start_pos:].upper()):  # go over each nuc
        if nuc in dnc:  # if ambiguous then dig deeper
            variants = []  # we store final results in this
            for snuc in dnc[nuc]:  # go over each mutant
                deamb = seq[:i+start_pos] + snuc + seq[i+start_pos+1:]  # new deambigulated sequence
                variants += deambigulate_all(deamb, i+start_pos+1)  # send it in again to check for additional ambiguity
            return variants  # final return of all the non-ambiguous sequences
    return [seq]  # if you got here you the endpoint of 1 completely deambigulated sequence


def generate_parts_for_cassette(motif_file, copy_rule1: int=10, copy_rule2: int=12) -> list:
    # read file to list
    raw_motifs = [[y.strip() for y in x.strip().split(",")] for x in motif_file.readlines()]

    # go over motifs and identify ambig and non-ambig and de-ambigulate the non-ambigs and randomize the ambigs
    motifs = []
    for i, (motif, rule) in enumerate(raw_motifs):
        how_many = calculate_number_of_possible_variants(motif)
        if rule == '1':
            print(f"{motif}: rule {rule}: {how_many} variants which will each be added in {copy_rule1} copies. {copy_rule1*how_many} total.")
            if how_many > 10:
                print(f"Warning: This motif will be deambigulated into {how_many} variants. Each variant will receive {copy_rule1} copies. Thats {copy_rule1*how_many} targets for just 1 methyltransferase!")
            motifs += deambigulate_all(motif)*copy_rule1
        elif rule == '2':
            print(f"{motif}: rule {rule}: {how_many} variants of which {copy_rule2} copies will be picked at random.")
            if how_many <= copy_rule2:  # make all variants, possibly more than once
                copies = copy_rule2/how_many
                all_variants = deambigulate_all(motif)
                adding = all_variants*int(copies)
                motifs += adding
                motifs += pick_n_random_without_duplicates(motif, copy_rule2-len(adding))
            else:
                motifs += pick_n_random_without_duplicates(motif, copy_rule2)
        else:
            print(f"Rule not recognized for motif '{motif}' on line {i}: '{rule}'. Rule must be either 1 or 2.")

    return motifs


def shuffle_motifs(motif_list):
    motifs = motif_list.copy()  # stupid in place mutability
    searching_for_motif_order = True
    x = 0
    while searching_for_motif_order:
        x += 1
        print(f"Attempt {x} at finding valid motif order")

        # do naive shuffle
        shuffle(motifs)
        # check for repeat motifs
        bad_poss = [i for i, el in enumerate(motifs[:-1]) if el == motifs[i + 1]]
        if not bad_poss:
            return motifs

        # attempt to fix bad positioned motifs
        # THIS METHOD WILL PLACE MORE PREVALENT MOTIFS IN THE LEFT END OF THE CASSETTE, POTENTIALLY A BAD THING FOR SYNTHESIS
        # ALTERNATIVE IS TO ATTEMPT TO RANDOMLY PLACE THE BAD ELEMENTS....but thats left as an exercise for the reader
        bad_elements = [motifs.pop(pos) for pos in bad_poss[::-1]]

        all_placed = True
        for el in bad_elements:
            placed = False
            for i, mel in enumerate(motifs):
                if i == 0:  # first pos
                    if el != mel:  # place here at first pos
                        motifs = [el] + motifs
                        placed = True
                        break
                elif i == len(motifs)-1:  # last pos
                    if el != mel:  # place at last pos
                        motifs.append(el)
                        placed = True
                        break
                else:  # middle pos
                    if el != mel and el != motifs[i-1]:  # place between i-1 and i
                        motifs = motifs[:i] + [el] + motifs[i:]
                        placed = True
                        break
            if not placed:  # no possible position, start over
                all_placed = False
                break
        if all_placed:  # positions fixed
            return motifs


def do_it_all(motif_file, copy_rule1: int=10, copy_rule2: int=12,  how_many_Ns: int=1, nresults: int=1) -> list:
    """
    :param motif_file: a file in a format that i need to come up with
    :param copy_rule1: Copies of each de-ambigulated sequence generated from motifs with less than 2 N's.
    :param copy_ambig: Copies in total of motifs with 2 or more N's.
    :param nresults: number of motif assemblies to output
    return: actual results
    """

    """
    PLAN TO WRITE ANNOTATED GB
    1) motif generator actually generates SeqRecord objects with a single Seq and SeqFeature objects
    2) shuffle_motifs takes into account that its not strings by SeqRecords
    3) Final cassette assembly also remembers that its not strings.
    """


    # generate de-ambigulated motifs in the right copy numbers
    motifs = generate_parts_for_cassette(motif_file, copy_rule1, copy_rule2)

    # shuffle motif positions in the cassette
    motif_set = set()
    while len(motif_set) != nresults:
        motif_set.add(tuple(shuffle_motifs(motifs)))

    cassette_strs = []
    for x in motif_set:
        # link with N's
        cassette_str = ""
        for motif in x:
            cassette_str += deambigulate_random("N"*how_many_Ns)
            cassette_str += motif
        cassette_strs.append(cassette_str)
    return cassette_strs
