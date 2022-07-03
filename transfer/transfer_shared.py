import os

from Shinjuku.shinjuku import lt, lt4
from Shinjuku.shinjuku.checks import rewind_check
from Shinjuku.shinjuku.gliderset import gset
from Shinjuku.shinjuku.transcode import realise_comp, encode_comp
from cgol_utils.paths import cgolroot


def all_orientations(pat):
    if isinstance(pat, str):
        pat = lt.pattern(pat)

    pats = []

    for o in ["identity", "rot270", "rot180", "rot90", "flip_x", "flip_y", "swap_xy", "swap_xy_flip"]:
        pato = pat(o).centre()
        for p in pats:
            if p == pato:
                break
        else:
            pats.append(pato)

    return pats


# @profile
def split_comp(comp):
    """Splits and returns the glider set and the constellation of the component.
    Assumes the gliders are well-spaced and the lifetime is finite."""

    if isinstance(comp, str):
        comp = lt.pattern(comp)

    glider_set = gset.extract(comp)
    constell = comp - glider_set.s
    return glider_set, constell


# @profile
def component_info(comp, glider_set, constell):
    # compcost, input, output
    if isinstance(comp, str):
        comp = lt.pattern(comp)
    out_apgcode = comp.oscar(verbose=False, return_apgcode=True)["apgcode"]
    compcost = sum(glider_set.ngliders())
    if constell:
        in_apgcode = constell.apgcode
    else:
        in_apgcode = "xs0_0"
    return compcost, in_apgcode, out_apgcode


# @profile
def apply_tree(pats, tr, queue=None, allow_noncanonical=False, check_rewind=False):
    """Applies the fragment tree in the second argument to one orientation
    of every pattern in the first argument. This minimises the number of
    calls to lifelib by assembling all of the targets into a mosaic and
    performing matches on the mosaic."""

    mosaic = lt.pattern()

    # Obtain integer square-root:
    modulus = int(len(pats) ** 0.5) - 1
    if modulus < 0:
        modulus = 0
    while modulus * modulus < len(pats):
        modulus += 1

    # Determine spacing of patterns:
    diam = 1
    for p in pats:
        bbox = p.bounding_box
        diam = max(diam, bbox[2], bbox[3])
    diam += 3
    log2d = len(bin(diam)) - 2
    radius = 1 << (log2d - 1)
    diam = radius + radius

    # Assemble mosaic:
    for (k, p) in enumerate(pats):
        i = (k % modulus)
        j = (k // modulus)
        mosaic += p((i << log2d) + radius, (j << log2d) + radius)

    sols = set()

    for (live, dead, replacements) in tr.values():
        m = mosaic.match(live=live, dead=dead)
        if m.empty():
            continue
        coords = map(tuple, m.coords())
        for (x, y) in coords:
            lx = (x >> log2d) << log2d
            x -= lx
            ly = (y >> log2d) << log2d
            y -= ly
            p = mosaic[lx: lx + diam, ly: ly + diam]
            p = p(-lx, -ly)
            for (n, r) in replacements:
                q = p - live(x, y) + r(x, y)
                if q[n + 1] != p:
                    continue
                try:
                    glider_set, constell = split_comp(q)
                    if allow_noncanonical:
                        if check_rewind and not rewind_check(constell, glider_set):
                            continue
                        compcost, input, output = component_info(q, glider_set, constell)
                        qstr = "\n".join(
                            q.rle_string(filename=f"{cgolroot}/tempfiles/pattern{os.getpid()}.rle").split("\n")[2:])
                        if queue is not None:
                            queue.put((qstr, compcost, input, output))
                        else:
                            try:
                                sols.add((qstr, compcost, input, output))
                            except TypeError as e:
                                print(f"got error {e} with values {(qstr, compcost, input, output)}")
                    else:
                        if rewind_check(constell, glider_set):
                            c, compcost, input, output = encode_comp(q, remove_spaceships=False, report_cost=True)
                            if queue is not None:
                                queue.put(c)
                            else:
                                try:
                                    sols.add((c, compcost, input, output))
                                except TypeError as e:
                                    print(f"got error {e} with values {(c, compcost, input, output)}")
                            # if input.startswith("xp"):
                            #     qstr = q.rle_string(filename=f"/home/exa/Documents/lifestuff/tempfiles/pattern{os.getpid()}.rle")
                            #     print(f"Got an xp input with values {(qstr, c, compcost, input, output)}")
                except (KeyError, ValueError) as e:
                    # print("got error", e)
                    continue
    return sols


# @profile
def components_to_triples(shinjuku_lines):
    s2s = set()

    if isinstance(shinjuku_lines, str):
        shinjuku_lines = open(shinjuku_lines, 'r')
    for s in shinjuku_lines:
        sp = s.split('>')
        if len(sp) == 1:
            continue
            # since ecf files are only produced by transfer, they cannot possibly include
            # components not found in sjk files
        if (len(sp) >= 3) and (sp[0].startswith('xs')) and (sp[2].startswith('xs')) and (sp[0] != sp[2]):
            op = int(sp[0][2:].split('_')[0])
            fp = int(sp[2][2:].split('_')[0])
            s2s.add((fp - op, s))
    s2s = list(s2s)
    s2s.sort()
    print("%d components to analyse." % len(s2s))

    triples = []
    wech_cache = set([])

    n5 = lt.pattern('bo$3o$bo!').centre()
    n9 = lt.pattern('3o$3o$3o!').centre()
    n21 = lt.pattern('b3o$5o$5o$5o$b3o!').centre()

    for (i, (m, s)) in enumerate(s2s):

        if i % 100 == 0 and i != 0:
            print("%d components analysed." % i)

        x = realise_comp(s, advance=-16)
        y = lt.pattern('')
        z = x
        n = 0

        while z != z[1]:
            y += (z ^ z[1])  # makes y be everything that at some point changed
            z = z[1]
            n += 1

        y = y.convolve(n9)

        x &= y
        z &= y

        if (z == x) or z.empty():
            continue
        wech2 = x.wechsler
        if wech2 in wech_cache:
            continue
        wech_cache.add(wech2)

        y &= z.convolve(n21)

        triples.append('%d:%d:%s' % (m, n, lt4.unify(z, y, x).wechsler))

    return triples


# @profile
def triples_to_tree(triples, min_delta=-9999, max_delta=9999):
    replacements = {}

    for triple in triples:

        ts = triple.split(':')
        m = int(ts[0])
        if m < min_delta or m > max_delta:
            continue
        n = int(ts[1])
        pat = lt4.pattern('xp0_' + ts[2], verify_apgcode=False)
        z, y, x = tuple(((lt.pattern() + a) for a in pat.layers()[:3]))

        fmatch = lt4.unify(z, y)
        wech = fmatch.wechsler
        fmatch2 = lt4.pattern('xp0_' + wech, verify_apgcode=False)
        z, y = tuple(((lt.pattern() + a) for a in fmatch2.layers()[:2]))

        for o in ["identity", "rot270", "rot180", "rot90", "flip_x", "flip_y", "swap_xy", "swap_xy_flip"]:
            fmatch3 = fmatch(o)
            if fmatch3.centre() == fmatch2.centre():
                x = x(o)
                b3 = fmatch3.bounding_box
                b2 = fmatch2.bounding_box
                x = x(b2[0] - b3[0], b2[1] - b3[1])
                break

        if lt4.unify(z, y, x).wechsler != ts[2]:
            raise ValueError("This should never happen!")

        if wech not in replacements:
            replacements[wech] = (z, y, [])

        replacements[wech][-1].append((n, x))

    return replacements


def convert_triples(triples, min_delta=-9999, max_delta=9999):
    if isinstance(triples, str):
        with open(triples) as f:
            triples = [l.strip() for l in f]

    if isinstance(triples, list, ):
        triples = triples_to_tree(triples, min_delta=min_delta, max_delta=max_delta)

    return triples


def convert_objects(objects):
    if isinstance(objects, str):
        with open(objects) as f:
            objects = [l.strip() for l in f]
    return objects
