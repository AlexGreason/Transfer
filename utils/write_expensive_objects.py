from cgol_utils.utils import min_paths, expensive_stills

cost = 6
outfile = open(f"/home/exa/Dropbox/Programming/C Code/CLion/lifelib/test_sls_{cost}cost.txt", "w")
objects = expensive_stills(min_paths, cells=None, cost=cost, force_true=False)
for obj in objects:
    print(f"{obj}")
    outfile.write(f"{obj}\n")