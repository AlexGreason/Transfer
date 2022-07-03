from cgol_utils import cost, expensive_stills, min_paths, cgolroot


def getimps(sources, targets, links):
    imps = {}
    for s in sources:
        imps[s] = set()
    for l in links:
        if l[0] in sources and l[1] in targets and l[0] != l[1]:
            imps[l[0]].add(l[1])
    return imps


def impstolist(sources, targets, imps):
    res = []
    for s in sources:
        res.append((s, [x for x in list(imps[s]) if x in targets]))
    res.sort(key=lambda x: len(x[1]), reverse=True)
    return res


def getlinks_costs(costfile):
    links = set()
    with open(costfile, "r") as infile:
        for line in infile:
            line = line.replace("\n", "")
            line = line.split(" ")
            try:
                source, target = line[0], line[2]
            except IndexError as e:
                print(costfile, line, e)
                continue
            links.add((source, target))
    return list(links)


def getlinks_comps(compfile):
    links = set()
    with open(compfile, "r") as infile:
        for line in infile:
            line = line.replace("\n", "")
            try:
                incode, comp, outcode = line.split(">")
                links.add((incode, outcode))
            except:
                pass
    return list(links)


def getlinks_ecf(compfile):
    links = set()
    with open(compfile, "r") as infile:
        for line in infile:
            line = line.replace("\n", "")
            try:
                _, _, incode, outcode = line.split(" ")
                links.add((incode, outcode))
            except:
                pass
    return list(links)


def enforce_transitive(imps):
    addedany = True
    firstpass = True
    changed = set()
    justadded = {}
    while addedany:
        addedany = False
        oldchanged = changed.copy()
        changed = set()
        for s in imps:
            outs = imps[s]
            currlen = len(outs)
            tocheck = outs if firstpass else outs.intersection(oldchanged).union(justadded[s])
            for o in tocheck:
                children = imps[o]
                outs = outs.union(children)
            if s in outs:
                outs.remove(s)
            justadded[s] = outs.difference(imps[s])
            imps[s] = outs
            if len(outs) != currlen:
                addedany = True
                changed.add(s)
        firstpass = False
    return imps


if __name__ == "__main__":
    stills = expensive_stills(min_paths, 21, 999)

    basedir = f"{cgolroot}/transfer"
    filenames = ["unsynthed-xs21-mindense-0.2-20210918.ecf"]
    costfiles = [f"{basedir}/{name}" for name in filenames]
    links = []
    for f in costfiles:
        links += getlinks_ecf(f)
    inputs = set()
    for l in links:
        inputs.add(l[0])
    inputs = set(list(inputs) + stills)
    stills = set(stills)
    imps = getimps(inputs, stills, links)
    imps = enforce_transitive(imps)
    imps = impstolist(inputs, stills, imps)
    for i in imps:
        if cost(i[0]) < 9999 and len(i[-1]) > 0:
            print(f"known synth for {i[0]} should have already implied {i[-1]}")
    from all_unsynthed_by_soups import getall_helper
    occurrences = getall_helper()
    imps = [(i[0], occurrences[i[0]] if i[0] in occurrences else 0, i[1]) for i in imps]
    imps = [x for x in imps if x[0] in stills or x[1] > 0]
    imps.sort(key=lambda x: x[1], reverse=True)
    outfile = "/home/exa/Documents/lifestuff/updatestuff/xs21Implications_all.txt"
    with open(outfile, "w") as out:
        for i in imps:
            res = ", ".join(i[-1])
            if len(i[-1]) > 0:
                line = f"{i[0]} ({i[1]} soup{'s' if i[1] != 1 else ''}) implies {res}"
                print(line)
                out.write(line + "\n")
