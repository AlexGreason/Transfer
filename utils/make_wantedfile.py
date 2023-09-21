from ImplicationGraph import getlinks
from cgol_utils.paths import cgolroot

if __name__ == "__main__":
    from cgol_utils.utils import cost
    infiles = [
        f"{cgolroot}/transfer/unsynthed-xs22-2023021921.txt",
    ]
    outfile = f"{cgolroot}/transfer/xs22_wanted.txt"
    links = set()
    for file in infiles:
        links = links.union(getlinks(file))
        print(len(links))
    links = [(incode, outcode) for incode, outcode in links if cost(outcode) > 999]
    print(len(links))
    i = 0
    for k in links:
        print(k)
        i += 1
        if i > 10:
            break
    with open(outfile, "w") as o:
        for k in links:
            o.write(f"{k[0]} {k[1]}\n")

