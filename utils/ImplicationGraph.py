from cgol_utils.fileutils import parse_objects_file
from cgol_utils.paths import cgolroot


def getimps(sources, targets, links):
    imps = {}
    for s in sources:
        imps[s] = set()
    for link in links:
        if link[0] in sources and link[1] in targets and link[0] != link[1]:
            imps[link[0]].add(link[1])
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


def getlinks_txt(path):
    links = set()
    for line in open(path, "r"):
        incode, _, target = line.replace("\n", "").split()
        links.add((incode, target))
    return links


def getlinks_comps(compfile):
    links = set()
    i = 0
    with open(compfile, "r") as infile:
        for line in infile:
            line = line.replace("\n", "")
            try:
                incode, comp, outcode = line.split(">")
                links.add((incode, outcode))
                i += 1
                if i % 1000 == 0:
                    print(i, len(links))
            except:
                pass
    return links


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
    return links


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


def getlinks(path):
    print(path)
    suffix = path.split(".")[-1]
    if suffix == "sjk":
        return getlinks_comps(path)
    if suffix == "ecf":
        return getlinks_ecf(path)
    if suffix == "txt":
        return getlinks_txt(path)


if __name__ == "__main__":
    from cgol_utils.utils import expensive_stills, min_paths, cost

    # stills = expensive_stills(min_paths, 22, 999)
    xs22codes = parse_objects_file(f"{cgolroot}/censuses/22_bits_strict_apgcodes.txt")
    stills = [x for x in xs22codes if cost(x) > 999]
    basedir = f"{cgolroot}/transfer"
    filenames = ["unsynthed-xs22-2023021921.txt"]
    costfiles = [f"{basedir}/{name}" for name in filenames]
    links = set()
    for f in costfiles:
        links = links.union(getlinks(f))
    print(len(links), "links")
    links = list(links)
    inputs = set()
    for link in links:
        inputs.add(link[0])
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
    outfile = "/home/exa/Documents/lifestuff/updatestuff/xs22Implications_all.txt"
    with open(outfile, "w") as out:
        for i in imps:
            res = ", ".join(i[-1])
            if len(i[-1]) > 0:
                line = f"{i[0]} ({i[1]} soup{'s' if i[1] != 1 else ''}) implies {res}"
                print(line)
                out.write(line + "\n")
    outfile = "/home/exa/Documents/lifestuff/updatestuff/unsynthed_xs22.txt"
    with open(outfile, "w") as out:
        for s in stills:
            out.write(f"{s}\n")
