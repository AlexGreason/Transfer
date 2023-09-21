from multiprocessing import Pool

from cgol_utils.fileutils import write_components, parse_objects_file, read_file
from cgol_utils.paths import cgolroot
from cgol_utils.utils import min_paths, get_date_string, get_minpaths, get_sorted_sls, trueSLs, cata_costs, cost
from Shinjuku.shinjuku.transcode import encode_comp, realise_comp


def get_all_synths():
    all_synths = set()
    for _, _, component in min_paths.values():
        if component:
            all_synths.add(component)
    return all_synths


def write_all_synths():
    all_synths = get_all_synths()
    print(f"{len(all_synths)} components")
    all_synths = sorted(all_synths)
    write_components(all_synths, f"all_synths-{get_date_string(True, True, True, True, True, True)}.sjk")


def deduplicate_components(comps):
    # remove components that are already in min_paths
    all_synths = get_all_synths()
    print(f"{len(all_synths)} components in total min_paths")
    res = set()
    for comp in comps:
        if comp not in all_synths:
            res.add(comp)
    return res


def write_minpaths(objects):
    comps = get_minpaths(min_paths, objects)
    print(f"{len(comps)} components used to make {len(objects)} objects")
    filename = f"minpaths-{get_date_string(True, True, True, True, True, True)}"
    write_components(comps, filename)
    return filename


def canonicalize_component(comp):
    return encode_comp(realise_comp(comp), remove_spaceships=False)


def parallel_canonicalize(comps, nthreads=24):
    sjkcomps = [x for x in comps if '>' in x]
    ecfcomps = [x for x in comps if '>' not in x]
    print(f"converting {len(ecfcomps)} components")
    with Pool(nthreads) as pool:
        comps = pool.map(canonicalize_component, ecfcomps)
    return sjkcomps + comps


def deduplicate_minpaths(infile):
    comps = read_file(infile)
    print(f"read {len(comps)} components from {infile}")
    comps = set(parallel_canonicalize(comps))
    print("canonicalized")
    comps = deduplicate_components(comps)
    print(f"found {len(comps)} components not already in min_paths")
    write_components(comps, f"filtered-{infile.split('/')[-1]}")


def write_relevant():
    stills = get_sorted_sls(min_paths, trueSLs, cata_costs)
    stills += parse_objects_file(f"{cgolroot}/censuses/22_bits_strict_apgcodes.txt")
    stills += parse_objects_file(f"{cgolroot}/censuses/all_unsynthed_with_soups.txt")
    print(f"checking {len(stills)} stills")
    stills = [x for x in stills if cost(x) < 999]
    print(f"{len(stills)} stills have synths")
    return write_minpaths(stills)


if __name__ == '__main__':
    # write_relevant()
    # write_all_synths()
    deduplicate_minpaths(f"/home/exa/Documents/lifestuff/transfer/all_synths-{get_date_string()}.sjk")
    # deduplicate_minpaths("/home/exa/Documents/lifestuff/transfer/minpaths-20221127181913")