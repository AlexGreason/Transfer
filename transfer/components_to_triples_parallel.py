from Shinjuku.shinjuku import lt, lt4
from Shinjuku.shinjuku.transcode import realise_comp, encode_comp, decode_comp
from multiprocessing import Pool

n9 = lt.pattern('3o$3o$3o!').centre()
n21 = lt.pattern('b3o$5o$5o$5o$b3o!').centre()


def process_comp(ims):
    i, (m, s, op) = ims
    x = realise_comp(s, advance=-16)
    input, ngliders, output = decode_comp(s)
    y = lt.pattern('')
    z = x
    n = 0

    while z != z[1]:
        y += (z ^ z[1])  # makes y be everything that at some point changed
        # could potentially be extended to non-xs patts (indeed, generic patterns) by instead tracking the diffs between
        # initial-patt and initial-patt-plus-gliders? and stop once it equals the output patt?
        z = z[1]
        n += 1

    y = y.convolve(n9)

    x &= y
    z &= y

    if (z == x) or z.empty():
        return i, None, None, None, None, None
    wech2 = x.wechsler

    y &= z.convolve(n21)

    triple = '%d:%d:%s' % (m, n, lt4.unify(z, y, x).wechsler)
    return i, triple, wech2, s, op, ngliders


def components_to_triples_parallel(shinjuku_lines, nthreads=8, getrepresentatives=False):
    s2s = set()
    if isinstance(shinjuku_lines, str):
        shinjuku_lines = open(shinjuku_lines, 'r')
    for s in shinjuku_lines:
        s = s.replace("\n", "")
        sp = s.split('>')
        if len(sp) == 1:
            continue
            # since ecf files are only produced by transfer_, they cannot possibly include
            # components not found in sjk files
        if (len(sp) >= 3) and (sp[0].startswith('xs')) and (sp[2].startswith('xs')) and (sp[0] != sp[2]):
            op = int(sp[0][2:].split('_')[0])
            fp = int(sp[2][2:].split('_')[0])
            s2s.add((fp - op, s, op))
    s2s = list(s2s)
    s2s.sort()
    print(f"{len(s2s)} components to analyse. Using {nthreads} threads.")
    representatives = {}
    triples = {}
    wech_cache = set([])
    with Pool(nthreads) as p:
        results = p.imap(process_comp, enumerate(s2s), chunksize=16)

        for i, triple, wech2, compstr, inputpop, ngliders in results:
            if i % 1000 == 0 and i != 0:
                print("%d components analysed." % i)
            if triple is None:
                continue
            if wech2 in triples:
                existing = representatives[wech2]
                if inputpop < representatives[wech2][1]:
                    representatives[wech2] = (compstr, inputpop, existing[2]+1)
                else:
                    representatives[wech2] = (existing[0], existing[1], existing[2]+1)
                if ngliders < triples[wech2][1]:
                    triples[wech2] = (triple, ngliders)
                    existing = representatives[wech2]
                    representatives[wech2] = (compstr, inputpop, existing[2])
                continue
            representatives[wech2] = (compstr, inputpop, 1)

            triples[wech2] = (triple, ngliders)
    triples = triples.values()
    triples = [x[0] for x in triples]
    if getrepresentatives:
        return triples, representatives
    return triples
