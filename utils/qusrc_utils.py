"""
encoded = []
expected_pop = 25
for i, synth in enumerate(synths_split):
    try:
        print(i, synth)
        if lt.pattern(synth).population != expected_pop:
            print("overlap")
            continue
        glider_set, constell = split_comp(synth)
        if not rewind_check(constell, glider_set):
            print("not rewindable")
            continue
        sjk = encode_comp(synth)
        encoded.append(sjk)    
        print(sjk)
    except Exception as e:
        print(e)
    
canonicalized = [(x, realise_comp(x)) for x in encoded]
    
n_gliders = 5
target_cost = 0
min_improved = n_gliders + target_cost + 1
targets = expensive_stills(min_paths, cells=None, cost=min_improved, force_true=False)
    
seenproducts = []
unique = []
for x in canonicalized:
    product = x[0].split(">")[-1]
    if product in seenproducts:
        print(product, "already seen")
        continue
    if product not in targets:
        print(product, "not in targets")
        continue
    seenproducts.append(product)    
    unique.append(x)
    
for x in seenproducts:
    print(x, cost(x), x in targets)

for x in unique:
    output = x[0].split(">")[-1]
    print(output, cost(output), output in targets, printuses(output))
    print(x[1].rle_string())

"""
import os

from Shinjuku.shinjuku import lt
from cgol_utils.paths import cgolroot
from transfer_utils.transfer_shared import split_comp
from Shinjuku.shinjuku.transcode import encode_comp, decode_comp, realise_comp
from Shinjuku.shinjuku.checks import rewind_check
from cgol_utils.fileutils import parse_objects_file
from cgol_utils.mosaics import makemosaic_helper, makemosaic, synthlist_to_synthmap
from cgol_utils.utils import printuses, usecount, allsls, min_paths, used_by, trueSLs, cost, add_costs, getpop, \
    remove_useless_gliders, expensive_stills
import multiprocessing as mp

if __name__ == "__main__":
    filepath = "/home/exa/Dropbox/Programming/C Code/CLion/lifelib/stdout_5clean_15x15_5.log"
    # outfile = "/home/exa/Dropbox/Programming/Personal_Projects/GameOfLife/Shinjuku/shinjuku/transfer/qusrc_out.sjk"
    outfile = "/home/exa/Dropbox/Programming/Personal_Projects/GameOfLife/Shinjuku/shinjuku/comp/qusrc_out.sjk"
    skip = 300199 + 150899 + 254499 + 625199 + 748496 + 404299 + 636299
    n_gliders = 5
    target_cost = 0
    target_pop = 0
    min_improved = n_gliders + target_cost + 1
    expected_pop = 5 * n_gliders + target_pop
    unsynthed_with_soups = parse_objects_file(f"{cgolroot}/updatestuff/c1_unsynthed_with_soups.txt")
    unsynthed_with_soups = [x for x in unsynthed_with_soups if cost(x) > 999]
    targets = expensive_stills(min_paths, cells=None, cost=min_improved, force_true=False) + unsynthed_with_soups
    with open(filepath, "r") as f, open(outfile, "a") as compfile:
        synths = f.read()
        synths_split = synths.split("\n\n")
        synths_split[0] = "x = 64" + synths_split[0].split("x = 64")[1]
        print(f"{len(synths_split)} candidates")

        def handle_candidate(x):
            i, synth = x
            try:
                print(i, synth)
                pat = lt.pattern(synth)
                if pat.population != expected_pop:
                    print("overlap")
                    return None
                evolved = pat[200]
                bbox = evolved.bounding_box
                if any(-64 > x > 64 for x in bbox):
                    print(i, "out of bounds")
                    return None
                if evolved.apgcode not in targets:
                    print(i, "not in targets")
                    return None
                glider_set, constell = split_comp(synth)
                if not rewind_check(constell, glider_set, ncheck=8):
                    print(i, "not rewindable")
                    return None
                sjk = encode_comp(synth)
                print(i, sjk)
                return sjk
            except Exception as e:
                print(i, e)
                return None


        pool = mp.Pool(22)
        print(f"Skipping {skip} candidates")
        print(f"{len(synths_split[skip:])} candidates to process")
        results = pool.imap(handle_candidate, enumerate(synths_split[skip:]), chunksize=100)
        encoded = [x for x in results if x is not None]
        print(f"{len(encoded)} valid components")
        canonicalized = [(x, realise_comp(x)) for x in encoded]
        seenproducts = []
        unique = []
        targetset = set(targets)
        for i, x in enumerate(canonicalized):
            product = x[0].split(">")[-1]
            if product not in targetset:
                print(i, product, "not in targets")
                continue
            if product in seenproducts:
                print(i, product, "already seen")
                continue
            seenproducts.append(product)
            unique.append(x)
            print(i, len(unique), product, cost(product))
        print(f"{len(unique)} unique-output synths")
        compfile.write("\n")
        for x in unique:
            output = x[0].split(">")[-1]
            truestr = "true" if output in trueSLs else "pseudo"
            filename = f"%spattern.rle" % os.getpid()
            msg = f"Object {output} ({truestr}) (previous cost {cost(output)}, this cost {n_gliders + target_cost}) " \
                  f"({printuses(output)}) produced by the following collision: \n" \
                  f"{x[1].rle_string(filename=filename)}"
            print(msg)
            compfile.write(x[0] + "\n")
        makemosaic_helper(synthlist_to_synthmap([x[0] for x in unique]))
