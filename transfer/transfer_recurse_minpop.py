from heapq import heapify
from multiprocessing import Process, Queue
from queue import PriorityQueue, Empty, Full
from time import perf_counter as clock

from Shinjuku.shinjuku.gliderset import gset
from Shinjuku.shinjuku.search import slock
from Shinjuku.shinjuku.transcode import realise_comp, decode_comp, encode_comp
from cgol_utils import cost, trueSLs, min_paths, size, density, \
    cgolroot, getpop, get_date_string, escapenewlines, expensive_stills
from transfer.triples_utils import write_triples
from transfer_shared import all_orientations, apply_tree, convert_objects, convert_triples


def try_put(obj, queue, delay=0.0):
    try:
        if not delay:
            queue.put_nowait(obj)
        else:
            queue.put(obj, timeout=delay)
        return True
    except Full:
        return False


def try_get(queue, delay=0.0):
    try:
        if not delay:
            return queue.get_nowait()
        else:
            return queue.get(timeout=delay)
    except Empty:
        return False


def multiprocessing_priority_queue(inqueue, outqueue):
    # note: outqueue should have a maxsize of 1 for this to work
    vals = PriorityQueue()
    inputids = {}
    while True:
        newval = try_get(inqueue, delay=0.01)
        if newval:
            vals.put(newval)
        if not vals.empty():
            toadd = vals.get()
            bitcount, _, input, maxcost, depth, taskid, target = toadd
            if input not in inputids:
                inputids[input] = taskid
            if input in inputids and inputids[input] != taskid:
                continue  # removed and not readded, so discarded.
                # TODO: track this case to indicate that the target of the discarded task is also solved if the original task or its descendants are solved
            didput = try_put(toadd, outqueue, delay=0.01)
            if not didput:
                vals.put(toadd)


def handlequeue(taskqueue, vals, inputids, reported, singlereport, newitem=None, checkresults=True):
    if newitem is not None:
        vals.put(newitem)
    if checkresults and not vals.empty():
        didput = True
        while didput:
            toadd = vals.get()
            bitcount, _, _, input, maxcost, depth, taskid, target = toadd
            if input not in inputids:
                inputids[input] = (
                taskid, bitcount)  # note: the "bitcount" field can be either bitcount or bitcount-delta
            if input in inputids and inputids[input][0] != taskid and bitcount >= inputids[input][-1]:
                return
            elif input in inputids and inputids[input][0] != taskid and bitcount < inputids[input][-1]:
                inputids[input] = (taskid, bitcount)
            if target in reported and singlereport:
                return
            didput = try_put(toadd, taskqueue, delay=0)
            if not didput:
                vals.put(toadd)


def get_result(taskqueue, resqueue, vals, inputids, reported, singlereport):
    while True:
        handlequeue(taskqueue, vals, inputids, reported, singlereport)
        newres = try_get(resqueue, delay=0.05)
        if newres:
            return newres


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
        print("got task", task)
        if task == "terminate":
            return
        bitcount, _, _, apgcode, maxcost, depth, id, target = task
        try:
            pats = all_orientations(apgcode)
        except ValueError as e:
            print("Hit valueerror with", task, ":", e)
            continue
        comps = list(apply_tree(pats, triples, allow_noncanonical=True, check_rewind=True))
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
            resqueue.put((comp[1], maxcost - comp[0], depth, id, target))


def synthesise_recurse(triples, objects, costsfile, outfile, improvefile, nthreads=1, maximum_cost=9999,
                       maximum_size=9999, singlereport=True, mindensity=0.0, max_size_delta=9999, hopeless_threshold=3,
                       sortbydelta=False, max_depth=9999, min_component_size_delta=-9999, skip_regenerate_triples=False,
                       max_component_cost=None, anysynth=False):
    """Iterates over a sequence of apgcodes of still-lifes and saves easy
    syntheses to outfile. Takes < 1 second per object, amortized.

    triples: filename;
    objects: list of apgcodes, or filename containing such a list;
    outfile: filename to export Shinjuku synthesis lines"""

    objects = convert_objects(objects)

    write_triples(triples, parallel=True, nthreads=nthreads, skip_regenerate=skip_regenerate_triples,
                  max_cost=max_component_cost)
    triples = convert_triples(triples, min_delta=min_component_size_delta)
    print(f"{len(triples)} eligible distinct components")

    taskqueue = Queue(maxsize=5)
    resqueue = Queue()
    args = (triples, taskqueue, resqueue)
    workers = [Process(target=workerfunc, args=args) for _ in range(nthreads)]

    vals = PriorityQueue()
    inputids = {}
    reported = set()
    implied = set()
    # (apgcode, maxcost, depth, id, target)
    id = 0
    maxcosts = {}
    costdeltas = {}  # costdeltas[(object, target)] = cost of minimum known path from object to target
    tasks = []
    for o in objects:
        maxcost = min(maximum_cost, cost(o)) - 1
        if maxcost <= hopeless_threshold:
            continue
        maxcosts[o] = maxcost
        pop = getpop(o)
        task = (pop if not sortbydelta else 0, -maxcost, pop, o, maxcost, 0, id, o)
        id += 1
        tasks.append(task)
    vals.queue = tasks
    heapify(vals.queue)
    uses = {}

    starttime = clock()
    wroteout = set()
    print("Starting workers")
    [w.start() for w in workers]
    currdepth = 0
    with open(outfile, 'a') as g, open(costsfile, 'a') as costsf, open(improvefile, 'a') as improvef:
        g.write("\n")
        while True:
            component, maxcost, depth, _, target = get_result(taskqueue, resqueue, vals, inputids, reported,
                                                              singlereport)

            compstr, compcost, input, output = component
            if depth > currdepth:
                currdepth = depth
                print(
                    f"reached depth {depth} in {clock() - starttime} seconds and {id} nodes, queue length {vals.qsize()}")
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
            if (input, output, target, compcost) not in wroteout:
                wroteout.add((input, output, target, compcost))
                costsf.write(f"{input} {maxcost} {target}\n")
                costsf.flush()
                g.write(f'{escapenewlines(compstr)} {compcost} {input} {output}\n')
                g.flush()
            if input not in maxcosts or maxcost > maxcosts[input]:
                if input not in uses:
                    uses[input] = {}
                uses[input][output] = compstr
                maxcosts[input] = maxcost
                if hopeless_threshold < maxcost < incost:
                    id += 1
                    if id % 100 == 0:
                        print(
                            f"traversed {id} nodes in {clock() - starttime} seconds,"
                            f" {len(maxcosts)} unique intermediates, queue length {vals.qsize()}")
                    task = (getpop(input) if not sortbydelta else getpop(input) - getpop(target),
                            -maxcost, getpop(input), input, maxcost, depth + 1, id, target)
                    if depth + 1 < max_depth:  # maxdepth 1 only allows tasks at depth 0, etc
                        handlequeue(taskqueue, vals, inputids, reported, singlereport, newitem=task)
            if (maxcost >= incost or (anysynth and input in implied)) and (target not in reported or not singlereport):
                reported.add(target)
                print(encode_comp(compstr))
                truestr = "(true)" if output in trueSLs else "(pseudo)"
                closure = trace_forwards(output, uses, maxcosts)
                closure.add(compstr)
                closure = [encode_comp(x) for x in closure]
                if anysynth:
                    for comp in closure:
                        cin, ccost, cout = decode_comp(comp)
                        implied.add(cout)
                for x in closure:
                    improvef.write(f'{x}\n')
                    improvef.flush()
                seq = find_forwards_sequence(input, closure)
                synthchain = slock(seq)
                print(
                    f"wanted {output} {truestr} in {maxcost + compcost}, "
                    f"costs {incost + compcost if incost < 9999 else 'implied'}, reduces target {target}, found at depth {len(closure)}, "
                    f"used in \n{synthchain.rle_string()}\n forwards closure {closure}")
                # duplicate writes - for some reason some outputted synths weren't getting written, this is an attempt
                # to hack around whatever's broken there
                g.write(f'{escapenewlines(compstr)} {compcost} {input} {output}\n')
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


def get_target_path(input, target, uses, maxcosts):
    closure = trace_forwards(input, uses, maxcosts)
    lines = []
    currtarget = target
    closure = [encode_comp(x) for x in closure]
    while currtarget != input:
        for line in closure:
            if line.endswith(currtarget):
                lines.append(line)
                currtarget = line.split(">")[0]


def find_next(input, compset):
    for x in compset:
        if x.startswith(input):
            return x, x.split(">")[-1]
    return False, False


def find_forwards_sequence(input, compset):
    res = []
    nextcomp = True
    while nextcomp:
        nextcomp, input = find_next(input, compset)
        if nextcomp in res:
            nextcomp = False
        if nextcomp:
            res.append(nextcomp)
    return res


def compcost(componentstr):
    input, compcost, otput = decode_comp(componentstr)
    return compcost


def get_path_cost(path):
    return sum([compcost(x) for x in path])


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
    # runname = f"unsynthed-maxsizedelta3-mindense0.3-{get_date_string()}"
    # runname = "expensive-xs14-18-mindense-030"
    # runname = f"specialrequest-{get_date_string(hour=True, minute=True)}"
    runname = f"unsynthed-xs21-{get_date_string()}"
    # runname = f"unsynthed-mindelta-1-{get_date_string()}"
    triplefile = f"{cgolroot}/transfer/triples.txt"
    prefix = f"{cgolroot}/transfer/{runname}"
    outfile = prefix + ".ecf"
    improvefile = prefix + "-improvements.sjk"
    mosaicfile = prefix + ".rle"
    costsfile = prefix + ".txt"
    startindex = 191728
    # target = 'xs313_4a96yv69a4zwcicxmqy1o4cy3c4oy1qmxciczg88gxraik8wh10cky1kc01hw8kiarxg88gz1221y062iaab8baaa98c89aaab8baai26y01221zy2oka43031p5lllllllllll5p13034akozy28kcw65210haq22622qah01256wck8zxokcy5ggp2qm0mq2pggy5ckozy9252wccxccw252'
    # print(f"target initial cost {cost(target)}")
    #
    stills = []
    # stills = list(set(parse_objects_file("/home/exa/Documents/lifestuff/censuses/all_unsynthed_with_soups.txt")))
    # stills = ["xs16_660gs2qr"]
    # stills = [x for x in stills if getpop(x) <= 40]
    # min_paths = dijkstra()
    # used_by = {}
    # backtrack(target, set([]), used_by, min_paths)
    # stills = list(used_by)
    # stills = [s for s in stills if s.startswith("xs")]
    # for i in range(16):
    stills += expensive_stills(min_paths, cells=21, cost=999)
    stills += expensive_stills(min_paths, cells=20, cost=999)
    # stills += expensive_stills(min_paths, cells=14, cost=10, force_true=True)
    # stills += expensive_stills(min_paths, cells=15, cost=12, force_true=True)
    # stills += expensive_stills(min_paths, cells=16, cost=14, force_true=True)
    # stills += expensive_stills(min_paths, cells=17, cost=16, force_true=True)
    # stills += expensive_stills(min_paths, cells=18, cost=18, force_true=True)
    # import random
    # stills = parse_objects_file("/home/exa/Documents/lifestuff/censuses/all_unsynthed_with_soups.txt")

    stills = [x for x in stills if cost(x) > 999]
    # random.shuffle(stills)
    # stills = ['xs96_wj9ary9ra9jzwdl4cy9c4ldz311yf113z32qkgoy9ogkq23zw6a8cy9c8a6zw3213y93123']
    targetcosts = {}
    for s in stills:
        targetcosts[s] = cost(s)
    # stills = ['xs224_y1g8ka9eg8g0g8g0sik8gz08kit2ib42104v0v401248n45q48gzx4a98c88c8970798c88c89a511zg88q59h311319u0u913113h9ligz0125aiehik8g2v0v2g842t4kb421zy21243w1x1079521']

    # apgcodefile = open(f"{cgolroot}/censuses/21_bits_strict_apgcodes.txt", "r")
    # stills = []
    # for line in apgcodefile:
    #     stills.append(line.replace("\n", "").strip())

    # stills = [x for x in stills if x in true]
    print("%s target objects" % len(stills))
    synthesise_recurse(triplefile, stills, costsfile, outfile=outfile, improvefile=improvefile, nthreads=24,
                       maximum_cost=9999, maximum_size=9999,
                       max_size_delta=9999, mindensity=0.2, singlereport=True, hopeless_threshold=6,
                       max_depth=9999, sortbydelta=True, skip_regenerate_triples=False, min_component_size_delta=-9999,
                       max_component_cost=9999, anysynth=True)
    # TODO list (no particular order):
    # DONE 1. Move queue management (priority queue and deduplication stuff) into main thread
    # DONE 2. Reduce RAM per worker thread (so, ofc, first determine what's *using* that RAM)
    # DONE 3. Add noncanonical component support, only canonicalize as needed
    # DONE 4. Print out the whole forwards closure as a slocked component chain, rather than just the first step
    # 5. try exhausting with one density (keeping things discarded due to density around for later) and when it runs
    # out at one density (or hits max size), it decrements density a bit, runs through everything set aside due
    # to density within the new bound and adds them into the main queue, then resumes?
    # 6. Allow resuming search from a saved search state (e.g. running through sjk and basically replaying everything?)
    # DONE 7. priority queue should sort on size delta rather than pure size - or maybe it should be a toggle?
    # DONE 8. priority queue should sort first on size (priority desc) and secondly on maxcost (priority asc)
    # 9. track multiple targets properly - should report all improved targets when it reports an improvement, and if
    #    a different target later comes across an alread-solved intermediate that should get reported (and written out) too
    # 10. track and write out cost deltas instead of/in addition to maxcosts, update target costs via overrides as it
    #     goes, report multiple times for a given target if the later ones are still *improvements* to that target
    # 11. Write a thing to go through all the costs files (using cost deltas) and generate an updated wantedcosts file
    #     that uses the latest costs of all the righthand objects, get collisearch to handle that properly
    # 12. port apply_tree to C++


if __name__ == "__main__":
    starttime = clock()
    run()
    endtime = clock()
    print("Finished in %.2f seconds" % (clock() - starttime))
    # from transfer_opt import *
    #
    # min_paths = dijkstra()
    # improved_synths_mosaic(min_paths, sidelen=60, spacing=400)
