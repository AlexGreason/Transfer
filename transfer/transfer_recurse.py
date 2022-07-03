from multiprocessing import Process, Queue
from time import perf_counter as clock

from Shinjuku.shinjuku.gliderset import gset
from Shinjuku.shinjuku.transcode import realise_comp, decode_comp
from cgol_utils import get_sorted_sls, cost, trueSLs, min_paths, size, density, \
    parse_objects_file, cgolroot, get_date_string
from transfer_shared import all_orientations, apply_tree, convert_objects, convert_triples


def workerfunc(triples, workqueue, resqueue):
    # work queue has tuples (apgcode, maxcost, depth, id)
    # maxcost is "must be made in at most this many gliders to be a reduction"
    # depth is what iteration we're on
    # id is just a global counter
    # apgcode is self-explanatory
    # to start with the workqueue is filled with (target object, current cost - 1, 0, id)
    # at each step the worker function takes in a tuple, finds all components leading to apgcode, deduplicates on
    # the input apgcodes, preferring the lower component costs, then puts (component, maxcost, depth + 1, id)
    # in the result queue for each one.
    # master function fills the original tasks, takes results from result queue, maintains mappings from apgcodes to maxcosts and
    # from input objects to (output object, component)s. Takes in results: if the input object has a known cost which is lower than the maxcost-component cost,
    # reports a reduction and traces it through the input -> output mapping to the relevant target object, then appends that
    # to the lookup_synth result to get the full synthesis chain. If the input object is not in the apgcode->maxcost mapping, or if
    # its maxcost-component cost is higher than the stored value, update the stored value and proceed, otherwise discard the result.
    # if maxcost is 4 or higher or if the input has a known synth, save the component, if maxcost was 4 or higher put
    # (input, maxcost - component cost, depth, newid) into workqueue, otherwise discard the result
    # (since all the small 3-glider constellations are already in shinjuku)
    while True:
        task = workqueue.get()
        if task == "terminate":
            return
        try:
            pats = all_orientations(task[0])
        except ValueError as e:
            print("Hit valueerror with", task, ":", e)
            continue
        comps = list(apply_tree(pats, triples))
        # (c, compcost, input, output)
        inpcosts = {}
        for c in comps:
            if c[2] in inpcosts:
                if inpcosts[c[2]][0] > c[1]:
                    inpcosts[c[2]] = (c[1], c)
            else:
                inpcosts[c[2]] = (c[1], c)
        for input in inpcosts:
            comp = inpcosts[input]
            resqueue.put((comp[1], task[1] - comp[0], task[2], task[3], task[4]))


def synthesise_recurse(triples, objects, costsfile, outfile, nthreads=1, maximum_cost=9999, maximum_size=9999,
                       singlereport=True, mindensity=0, max_size_delta=9999, hopeless_threshold=3):
    objects = convert_objects(objects)
    triples = convert_triples(triples)

    workqueue = Queue()
    resqueue = Queue()
    args = (triples, workqueue, resqueue)
    workers = [Process(target=workerfunc, args=args) for i in range(nthreads)]
    # (apgcode, maxcost, depth, id)
    id = 0
    maxcosts = {}
    for o in objects:
        maxcost = min(maximum_cost, cost(o)) - 1
        maxcosts[o] = maxcost
        task = (o, maxcost, 0, id, o)
        id += 1
        workqueue.put(task)
    uses = {}
    reported = set()
    starttime = clock()
    wroteout = set()
    wrotecosts = {}
    print("Starting workers")
    [w.start() for w in workers]
    currdepth = 0
    with open(outfile, 'a') as g, open(costsfile, 'a') as costsf:
        g.write("\n")
        while True:
            component, maxcost, depth, _, target = resqueue.get()
            compstr, compcost, input, output = component
            if depth > currdepth:
                currdepth = depth
                print(
                    f"reached depth {depth} in {clock() - starttime} seconds and {id} nodes, queue length {workqueue.qsize()}")
            incost = cost(input)
            if (size(input) > maximum_size or
                density(input) < mindensity or
                (size(input) - size(target)) > max_size_delta) and incost == 9999:
                # if input not in maxcosts:
                #     print(input, "rejected due to size")
                #     maxcosts[input] = maxcost
                continue
            if target in reported and singlereport:
                continue
            if input == target:
                continue
            if (input, output, compcost) not in wroteout:
                wroteout.add((input, output, compcost))
                g.write(f'{compstr}\n')
                g.flush()
            if input not in maxcosts or maxcost > maxcosts[input]:
                costsf.write(f"{input} {maxcost} {target}\n")
                costsf.flush()
                if input not in uses:
                    uses[input] = {}
                uses[input][output] = compstr
                maxcosts[input] = maxcost
                if hopeless_threshold < maxcost < incost:
                    id += 1
                    if id % 100 == 0:
                        print(
                            f"traversed {id} nodes in {clock() - starttime} seconds, {len(maxcosts)} unique intermediates, queue length {workqueue.qsize()}")
                    task = (input, maxcost, depth + 1, id, target)
                    workqueue.put(task)
            if maxcost >= incost and (target not in reported or not singlereport):
                reported.add(target)
                print(compstr)
                q = realise_comp(compstr)
                truestr = "(true)" if output in trueSLs else "(pseudo)"
                print(
                    f"wanted {output} {truestr} in {maxcost + compcost}, "
                    f"costs {incost + compcost}, used with \n{q.rle_string()}\n forwards closure {trace_forwards(output, uses, maxcosts)}")
                # duplicate writes - for some reason some outputted synths weren't getting written, this is an attempt
                # to hack around whatever's broken there
                g.write(f'{compstr}\n')
                g.flush()


def trace_forwards(input, uses, maxcosts, currset=None):
    if currset is None:
        currset = set()
    if input in uses:
        for output in uses[input]:
            if input in maxcosts and output in maxcosts and maxcosts[input] < maxcosts[output]:
                currset.add(uses[input][output])
                trace_forwards(output, uses, maxcosts, currset=currset)
    return currset


def find_target(input, uses, maxcosts, targets):
    # TODO: trace cost forwards, report the set of targets and associated minimum implied costs
    if input in targets:
        return input
    if input in uses:
        for output in uses[input]:
            if input in maxcosts and output in maxcosts and maxcosts[input] < maxcosts[output]:
                target = find_target(output, uses, maxcosts, targets)
                if target is not None:
                    return target
    return None


def add_comps(comp1, comp2):
    # TODO: need to determine the orientation and location of the output of comp1 and rotate and translate the gliders
    # of comp2 appropriately, then find the duration of comp1, rewind the gliders of comp2 by that amount plus some margin
    # and add the gliders into the first pat and use encode_comp on the result
    input1, compcost1, output1 = decode_comp(comp1)
    input2, compcost2, output2 = decode_comp(comp2)
    if output1 != input2:
        raise ValueError(f"tried to add nonconsecutive components {comp1} {comp2}")
    pat1 = realise_comp(comp1)
    pat2 = realise_comp(comp2)
    gliders = gset.extract(pat2)


def run():
    triplefile = f"{cgolroot}/transfer/triples.txt"
    prefix = f"{cgolroot}/transfer/all-unsynthed-with-soups-breadthfirst-{get_date_string()}"
    outfile = prefix + ".sjk"
    mosaicfile = prefix + ".rle"
    costsfile = prefix + ".txt"
    write_triples(triplefile, nthreads=20)
    startindex = 191728
    target = "xq5_ug1hmgc865da808ad568cgmh1guz124w6yb6w421"

    stills = get_sorted_sls(min_paths, trueSLs)
    # stills = filter_by_uses(stills, min_uses=200)
    stills = []
    # min_paths = dijkstra()
    # used_by = {}
    # backtrack(target, set([]), used_by, min_paths)
    # stills = list(used_by)
    # for i in range(16):
    # stills += expensive_stills(min_paths, cells=20, cost=999)
    # stills = parse_objects_file("/home/exa/Documents/lifestuff/censuses/unsynthed_c1.txt")
    # stills += ["xs20_03p6426z17853"]
    # stills = ['xs30_wc93ggz64138d0mk13zy2641']
    # stills = []
    # prefix = f"{cgolroot}/transfer/specialrequest"
    # for x in ["2", "2_2", "2_3"]:
    #     stills += get_inputs(f"{prefix}_{x}.sjk")
    # stills += ["xs29_0g8o0u1eoz34iq9871"]

    # apgcodefile = open(f"{cgolroot}/censuses/21_bits_strict_apgcodes.txt", "r")
    # stills = []
    # for line in apgcodefile:
    #     stills.append(line.replace("\n", "").strip())

    # stills = [x for x in stills if x in true]
    stills = parse_objects_file("/home/exa/Documents/lifestuff/censuses/all_unsynthed_with_soups.txt")

    stills = [x for x in stills if cost(x) > 999]
    stills = list(set(stills))
    print("%s target objects" % len(stills))
    synthesise_recurse(triplefile, stills, costsfile, outfile=outfile, nthreads=22, maximum_cost=9999,
                       maximum_size=9999,
                       max_size_delta=9999, mindensity=0, singlereport=True, hopeless_threshold=9)
    # makemosaic_reachable(outfile, sidelen=30, spacing=300)


if __name__ == "__main__":
    starttime = clock()
    run()
    endtime = clock()
    print("Finished in %.2f seconds" % (clock() - starttime))
    # from transfer_opt import *
    #
    # min_paths = dijkstra()
    # improved_synths_mosaic(min_paths, sidelen=60, spacing=400)

"""
from transfer_opt import *
from utils import *
from mosaics import *
stills = getsortedsls(min_paths, trueSLs, printdiffs=True)
unsolved = expensive_stills(min_paths, 20, 999)
print("unsolved", len(unsolved))
a = improved_mosaic()

from transfer_opt import *
improved_synths_mosaic(min_paths)
objects = get_improved(trueSLs)[0]
allcomps = []
for o in objects:
    print(o)
    allcomps += get_synth(min_paths, o)
output = open("/home/exa/Documents/lifestuff/transfer/improved.sjk", "w")
for a in set(allcomps):
    output.write(a + "\n")
from transfer_recurse import *
a = makemosaic_reachable("/home/exa/Documents/lifestuff/transfer/improved.sjk", sidelen=50, spacing=200)


from utils import *
from mosaics import *
stills = parse_objects_file("/home/exa/Documents/lifestuff/censuses/unsynthed_c1.txt")
allcomps = objects_minpaths(min_paths, stills)
output = open("/home/exa/Documents/lifestuff/transfer/improved.sjk", "w")
for a in set(allcomps):
    output.write(a + "\n")
"""
