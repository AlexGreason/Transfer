from cgol_utils.fileutils import parse_objects_file, write_improved_synths
from cgol_utils.mosaics import improved_synths_mosaic
from cgol_utils.paths import cgolroot
from cgol_utils.utils import min_paths, expensive_stills, cost

if __name__ == "__main__":
    unsynthed_with_soups = parse_objects_file(f"{cgolroot}/updatestuff/all_unsynthed_with_soups.txt")
    c1_unsynthed_with_soups = parse_objects_file(f"{cgolroot}/updatestuff/c1_unsynthed_with_soups.txt")
    write_improved_synths(min_paths, redundancies=False, forcecheck= set(unsynthed_with_soups + c1_unsynthed_with_soups))
    improved_synths_mosaic(min_paths, redundancies=False, forcecheck= set(unsynthed_with_soups + c1_unsynthed_with_soups),
                           sidelen=40)
    unsynthed_with_soups = [x for x in unsynthed_with_soups if cost(x) > 999]
    c1_unsynthed_with_soups = [x for x in c1_unsynthed_with_soups if cost(x) > 999]
    print("Unsynthed with soups:", len(unsynthed_with_soups))
    print("C1 unsynthed with soups:", len(c1_unsynthed_with_soups))
    print("Cost >21 xs22s:", len(expensive_stills(min_paths, cells=22, cost=22, force_true=True)))
    print("Cost >20 xs21s:", len(expensive_stills(min_paths, cells=21, cost=21, force_true=True)))
    print("Cost >19 xs20s:", len(expensive_stills(min_paths, cells=20, cost=20, force_true=True)))
    print("Cost >18 xs19s:", len(expensive_stills(min_paths, cells=19, cost=19, force_true=True)))
    print("Cost >17 xs18s:", len(expensive_stills(min_paths, cells=18, cost=18, force_true=True)))
    print("Cost >14 xs17s:", len(expensive_stills(min_paths, cells=17, cost=15, force_true=True)))
    print("Cost >12 xs16s:", len(expensive_stills(min_paths, cells=16, cost=13, force_true=True)))
    print("Cost >9 xs15s:", len(expensive_stills(min_paths, cells=15, cost=10, force_true=True)))
    print("Cost >8 xs14s:", len(expensive_stills(min_paths, cells=14, cost=9, force_true=True)))
    print("Cost >7 xs13s:", len(expensive_stills(min_paths, cells=13, cost=8, force_true=True)))
    print("Cost >6 xs12s:", len(expensive_stills(min_paths, cells=12, cost=7, force_true=True)))
    # cheaper, catacosts = get_improved(min_paths, trueSLs, forcecheck=xs21codes + unsynthed_with_soups)
    # print(f"{len(cheaper)} improved, including forcechecked")
    # cheaper = [x for x in cheaper if not (x in cata_costs and cost(x) == cata_costs[x])]
    # print(f"{len(cheaper)} improved, after doublecheck")
    # synths = get_minpaths(min_paths, cheaper)
    # print(f"got minpaths, {len(synths)} steps")
    # synths = convert_synths_to_sjk(synths, nthreads=24)
    # print("converted synths")
    # synths = filter_invalid_synths(synths, nthreads=24)
    # print(f"validated synths, {len(synths)} passed")
    # write_components(synths, f"improvedsynths-{get_date_string(True, True, True, True, True, True)}.sjk")