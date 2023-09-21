from cgol_utils.fileutils import parse_objects_file, write_improved_synths
from cgol_utils.mosaics import improved_synths_mosaic
from cgol_utils.paths import cgolroot
from cgol_utils.utils import min_paths, expensive_stills, cost

if __name__ == "__main__":
    xs22codes = parse_objects_file(f"{cgolroot}/censuses/22_bits_strict_apgcodes.txt")
    unsynthed_with_soups = parse_objects_file(f"{cgolroot}/censuses/all_unsynthed_with_soups.txt")
    unsynthed_with_soups = [x for x in unsynthed_with_soups if cost(x) > 999]
    write_improved_synths(min_paths, redundancies=False, forcecheck=xs22codes + unsynthed_with_soups)
    improved_synths_mosaic(min_paths, redundancies=False, forcecheck=xs22codes + unsynthed_with_soups,
                           sidelen=40)
    print("Unsynthed with soups:", len(unsynthed_with_soups))
    print("Unsynthed xs22s:", len([x for x in xs22codes if cost(x) > 999]))
    print("Synthed xs22s:", len([x for x in xs22codes if cost(x) < 999]))
    print("Expensive xs21s:", len(expensive_stills(min_paths, cells=21, cost=21, force_true=True)))
    print("Expensive xs20s:", len(expensive_stills(min_paths, cells=20, cost=20, force_true=True)))
    print("Expensive xs19s:", len(expensive_stills(min_paths, cells=19, cost=19, force_true=True)))
    print("Expensive xs18s:", len(expensive_stills(min_paths, cells=18, cost=18, force_true=True)))
    print("Expensive xs17s:", len(expensive_stills(min_paths, cells=17, cost=17, force_true=True)))
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