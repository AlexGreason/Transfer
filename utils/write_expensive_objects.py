from cgol_utils.fileutils import parse_objects_file
from cgol_utils.paths import cgolroot
from cgol_utils.utils import min_paths, expensive_stills, cost

for mincost in range(6, 100):
    unsynthed_with_soups = parse_objects_file(f"{cgolroot}/updatestuff/c1_unsynthed_with_soups.txt")
    unsynthed_with_soups = [x for x in unsynthed_with_soups if cost(x) > 999]
    outfile = open(f"/home/exa/Dropbox/Programming/C Code/CLion/lifelib/wantedfiles/test_sls_{mincost}cost.txt", "w")
    objects = expensive_stills(min_paths, cells=None, cost=mincost, force_true=False) + unsynthed_with_soups
    print(f"Cost {mincost} objects: {len(objects)}")
    for obj in objects:
        # print(f"{obj}")
        outfile.write(f"{obj}\n")