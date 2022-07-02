import os
import time

from cgol_utils import get_useful_components, min_paths, get_all_components
from transfer.components_to_triples_parallel import components_to_triples_parallel
from transfer.transfer_shared import components_to_triples


def write_special_triples(comps, filename, forcewrite=False, parallel=True, nthreads=8, skip_regenerate=False):
    if os.path.isfile(filename) and not forcewrite:
        print("triples file already exists! Are you sure you want to overwrite it?")
        if (time.time() - os.path.getmtime(filename)) > 172800 and not skip_regenerate:
            print("triples file too old, regenerating")
        elif (time.time() - os.path.getmtime(filename)) > 172800 and skip_regenerate:
            print("triples file too old, but regeneration was skipped")
            return
        else:
            return
    if forcewrite:
        print("file check overriden! Generating triples")
    if parallel:
        triples, representatives = components_to_triples_parallel(comps, nthreads=nthreads, getrepresentatives=True)
    else:
        triples = components_to_triples(comps)
        representatives = []
    trips = open(filename, "w")
    for t in triples:
        trips.write(t + "\n")
    return representatives


def write_triples(filename, forcewrite=False, parallel=True, nthreads=8, onlyminpaths=False, skip_regenerate=False, max_cost=None):
    if onlyminpaths:
        lines = get_useful_components(min_paths, max_cost=max_cost)
        print("Only using components on min-paths!")
    else:
        lines = get_all_components(max_cost=max_cost)
    return write_special_triples(lines, filename, forcewrite=forcewrite, parallel=parallel, nthreads=nthreads, skip_regenerate=skip_regenerate)
