from multiprocessing import Process, Queue
from time import perf_counter as clock

from Shinjuku.shinjuku.checks import rewind_check
from Shinjuku.shinjuku.transcode import realise_comp, decode_comp, encode_comp
from cgol_utils.fileutils import parse_objects_file
from cgol_utils.mosaics import makemosaic
from cgol_utils.paths import cgolroot
from cgol_utils.utils import cost, overrides, min_paths, trueSLs, printuses, get_sorted_sls, cata_costs, \
    get_date_string, allsls
from transfer_utils.triples_utils import write_triples, write_special_triples
from transfer_shared import all_orientations, apply_tree, split_comp, convert_objects, convert_triples


def workerfunc(triples, workqueue, resqueue, allow_noncanonical=False):
    while True:
        task = workqueue.get()
        if task == "terminate":
            return
        objects = [line for line in task[0] if line.startswith('xs')]
        pats = [a for target in objects for a in all_orientations(target)]
        apply_tree(pats, triples, resqueue, allow_noncanonical=allow_noncanonical)
        resqueue.put("done")


def synthesise_things(triples, objects, outfile, chunksize=64, nthreads=1, storeall=False):
    """Iterates over a sequence of apgcodes of still-lifes and saves easy
    syntheses to outfile. Takes < 1 second per object, amortized.

    triples: fragment tree, or list of triples, or filename;
    objects: list of apgcodes, or filename containing such a list;
    outfile: filename to export Shinjuku synthesis lines"""

    objects = convert_objects(objects)
    triples = convert_triples(triples)

    workqueue = Queue()
    resqueue = Queue()
    args = (triples, workqueue, resqueue, not storeall)
    workers = [Process(target=workerfunc, args=args) for _ in range(nthreads)]
    subchunk = chunksize // 8
    for i in range(0, len(objects), subchunk):
        upper = min(i + subchunk, len(objects))
        chunk = objects[i:upper]
        task = (chunk, i + upper)
        workqueue.put(task)
    anyresults = False
    [w.start() for w in workers]
    with open(outfile, 'w') as g:
        done = 0
        while True:
            res = resqueue.get()
            if res == "done":
                done += subchunk
                print(
                    f"Finished {min(done, len(objects))}/{len(objects)} in {int(clock() - starttime)} "
                    f"seconds, resqueue size {resqueue.qsize()}")
                if done >= len(objects):
                    [workqueue.put("terminate") for _ in workers]
                    [w.terminate() for w in workers]
                    return
            else:
                if not anyresults:
                    anyresults = True
                    print("Got first result from workers: ", res)
                if storeall:
                    comp = res
                    input, compcost, output = decode_comp(comp)
                    g.write(f'{comp}\n')
                    g.flush()
                else:
                    q, compcost, input, output = res
                outcost = cost(output, overrides=overrides)
                if outcost > (cost(input, overrides=overrides) + compcost) and cost(input, overrides=overrides) < 9999:
                    if not storeall:
                        glider_set, constell = split_comp(q)
                        if not rewind_check(constell, glider_set):
                            continue
                        comp = encode_comp(q, remove_spaceships=False)
                        g.write(f'{comp}\n')
                        g.flush()
                    overrides[output] = cost(input, overrides=overrides) + compcost
                    if output not in min_paths or comp != min_paths[output][2]:
                        print(comp)
                        q = realise_comp(comp)
                        truestr = "(true)" if output in trueSLs else "(pseudo)"
                        usestr = f"({printuses(output)})"
                        print(
                            f"reduced {output} {truestr} from {outcost} "
                            f"to {cost(input, overrides=overrides) + compcost} {usestr} with \n{q.rle_string()}")


def run(nthreads, storeall=False, startat=0, chunksize=64, onlyunsynthed=False, onlyc1=False, mincost=0):
    triplefile = f"{cgolroot}/transfer/triples.txt"
    write_triples(triplefile, nthreads=nthreads)
    stills = []
    if not onlyunsynthed:
        stills = get_sorted_sls(min_paths, trueSLs, cata_costs)
    if onlyc1:
        stills += parse_objects_file(f"{cgolroot}/updatestuff/c1_unsynthed_with_soups.txt")
    else:
        stills += parse_objects_file(f"{cgolroot}/updatestuff/all_unsynthed_with_soups.txt")
    stills = sorted(list(set(stills)), key=lambda x: (cost(x), x))
    stills = stills[startat:]
    if mincost > 0:
        stills = [x for x in stills if cost(x) > mincost]
    print(f"{len(stills)} target objects")

    outfile = f"{cgolroot}/transfer/transfer-{'unsynthed' if onlyunsynthed else 'all'}" \
              f"{'-storeall' if storeall else ''}-{get_date_string()}.sjk"
    synthesise_things(triplefile, stills, outfile=outfile, chunksize=chunksize, nthreads=nthreads, storeall=storeall)


def run_collisearch_comps(nthreads, storeall=False, startat=0, chunksize=64):
    print("using just collisearch components!")
    compfile = "/home/exa/Dropbox/Programming/Personal_Projects/GameOfLife/Shinjuku/shinjuku/comp/collisearch_out.sjk"
    triplefile = f"{cgolroot}/transfer/triples-collisearch.txt"
    comps = open(compfile, "r")
    write_special_triples(comps, triplefile, nthreads=nthreads)
    stills = get_sorted_sls(min_paths, trueSLs, cata_costs)
    stills += parse_objects_file(f"{cgolroot}/censuses/all_unsynthed_with_soups.txt")
    stills = sorted(list(set(stills)), key=lambda x: (cost(x), x))
    stills = stills[startat:]
    print(f"{len(stills)} target objects")
    outfile = f"{cgolroot}/transfer/transfer-collisearch-{get_date_string()}.sjk"
    synthesise_things(triplefile, stills, outfile=outfile, chunksize=chunksize, nthreads=nthreads, storeall=storeall)


def run_custom_comps(nthreads, comps, storeall=False, startat=0, chunksize=64):
    print("using custom components!")
    triplefile = f"{cgolroot}/transfer/triples-custom.txt"
    write_special_triples(comps, triplefile, forcewrite=True, parallel=True, nthreads=nthreads)
    stills = get_sorted_sls(min_paths, trueSLs, cata_costs)
    stills += parse_objects_file(f"{cgolroot}/censuses/all_unsynthed_with_soups.txt")
    stills = sorted(list(set(stills)), key=lambda x: (cost(x), x))
    stills = stills[startat:]
    print(f"{len(stills)} target objects")
    outfile = f"{cgolroot}/transfer/transfer-custom-{get_date_string(year=True, month=True, day=True, hour=True)}.sjk"
    synthesise_things(triplefile, stills, outfile=outfile, chunksize=chunksize, nthreads=nthreads, storeall=storeall)
    makemosaic(outfile)


if __name__ == "__main__":
    starttime = clock()
    run(24, storeall=False, startat=0, chunksize=64, onlyunsynthed=True, onlyc1=True, mincost=999)
    # run_custom_comps(nthreads=4, comps=['xs19_j9ari96z11>8 -2 22 -1/-18 5 -13 10//@0L-10 4>xs20_32qj8r9ic'
    #                                     ])
    # triplefile = f"{cgolroot}/transfer/triples.txt"
    # write_triples(triplefile, nthreads=24, forcewrite=True)
    # run(nthreads=22, storeall=False, startat=0, chunksize=512, onlyunsynthed=False, mincost=6)

    # 12/11/23 all-comps all-targets interrupted at Finished 147968/4129440 in 154076 seconds, resqueue size 0
    # run_custom_comps(nthreads=20,
    #                  comps="/home/exa/Dropbox/Programming/Personal_Projects/GameOfLife/Shinjuku/shinjuku/comp/qusrc_out.sjk",
    #                  storeall=False, startat=0, chunksize=1024)
    # objs = allsls
    # wanted = list(set(parse_objects_file("/home/exa/Documents/lifestuff/censuses/c1_unsynthed_with_soups.txt")))
    # collisearch_exa_bash.run(ngliders=2, nthreads=20, targets=objs, wanted=wanted)
    # triplefile = f"{cgolroot}/transfer/triples.txt"
    # write_triples(triplefile)
    # stills = parse_objects_file("/home/exa/Documents/lifestuff/censuses/all_unsynthed_with_soups.txt")
    # print(f"{len(stills)} target objects")
    #
    # outfile = f"{cgolroot}/transfer/transfer-unsynthed-with-soups-{get_date_string()}.sjk"
    # synthesise_things(triplefile, stills, outfile=outfile, chunksize=64, nthreads=8, storeall=False)

    endtime = clock()
    print("Finished in %.2f seconds" % (clock() - starttime))
    # filtercomps(min_paths, "/home/exa/Documents/lifestuff/transfer/minpaths.sjk", "/home/exa/Documents/lifestuff/transfer/minpaths-filt.sjk")
    # write_minpaths(min_paths, getsortedsls(min_paths, true), "/home/exa/Documents/lifestuff/transfer/minpaths.sjk")
    # prevstills = getallprev(9)
    # stills = parse_objects_file("/home/exa/Documents/lifestuff/censuses/unsynthed_allsymms.txt")
    # outfile = "/home/exa/Documents/lifestuff/transfer/souped.sjk"
    # out = open(outfile, "w")
    # min_paths = dijkstra()
    # for s in stills:
    #     if cost(s, overrides=overrides) != 9999:
    #         out.write(min_paths[s][2] + "\n")
