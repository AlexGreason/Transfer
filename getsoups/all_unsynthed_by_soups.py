import operator
import os
from pathlib import Path

from cgol_utils.utils import cata_costs, fetch_if_old, cost


def fetch_oversized_census(file, census):
    print("skipping oversized census", census)


def getall_helper(symmetries=None, folder="/home/exa/Documents/lifestuff/censuses/", unsynthed=False,
                  usecatacosts=False, catagolue_costs=None, oversized_censuses=("D8_1",)):
    os.makedirs(folder, exist_ok=True)
    if symmetries is None:
        symmetries = ["C1", "G1", "D8_1", "D8_4", "C4_4", "8x32", "D4_+2", "D4_+1", "D4_x4", "D4_x1", "D2_+1", "D4_+4",
                      "D2_+2", "D2_x", "4x64", "C2_1", "C4_1", "1x256", "C2_4", "C2_2", "2x128"]
    if oversized_censuses is None:
        oversized_censuses = []

    def costof(code):
        if usecatacosts:
            if code in catagolue_costs:
                return catagolue_costs[code]
            else:
                return 9999
        return cost(code)

    occurrences = {}
    for symmetry in symmetries:
        if symmetry not in oversized_censuses:
            fetch_if_old(folder + f"objects{symmetry}.txt",
                         f"https://catagolue.appspot.com/textcensus/b3s23/{symmetry}/")
        else:
            fetch_oversized_census(folder + f"objects{symmetry}.txt", f"b3s23/{symmetry}")
            if not Path(folder + f"objects{symmetry}.txt").exists():
                continue
        with open(folder + f"objects{symmetry}.txt") as Fin:
            for line in Fin:
                if "occurrences" in line:
                    continue
                parts = line.split(',')
                code = parts[0].strip('"')
                if ('megasized' not in code) and ('messless' not in code) and ('methuselah' not in code) \
                        and code is not None and (costof(code) > 999 or not unsynthed):
                    try:
                        count = int(parts[1].strip().strip('"'))
                    except Exception as e:
                        print(parts, e, symmetry)
                        raise e
                    if code not in occurrences:
                        occurrences[code] = 0
                    occurrences[code] += count
    return occurrences


def getall(symmetries=None, folder="/home/exa/Documents/lifestuff/censuses/", bitcount=None, unsynthed=False,
           usecatacosts=True, catagolue_costs=None, oversized_censuses=None):
    occurrences = getall_helper(symmetries, folder, unsynthed, usecatacosts=usecatacosts,
                                catagolue_costs=catagolue_costs, oversized_censuses=oversized_censuses)

    listocc = []
    for k in occurrences:
        listocc.append((k, occurrences[k]))

    res = []
    listocc.sort(key=operator.itemgetter(1), reverse=True)
    for obj in listocc:
        if obj[0][0:2] == 'xs' and obj[1] > 0 and (
                bitcount is None or obj[0][2:3 + len(str(bitcount))] == str(bitcount) + "_"):
            res.append(obj)
    return res


if __name__ == "__main__":
    # getsortedsls(min_paths, true)
    censusfolder = "/home/exa/Documents/lifestuff/censuses/"
    outfolder = "/home/exa/Documents/lifestuff/updatestuff/"
    os.makedirs(outfolder, exist_ok=True)
    outfile = open(outfolder + "all_unsynthed_with_soups.txt", "w")
    objects = getall(symmetries=None, folder=censusfolder, bitcount=None, unsynthed=True, usecatacosts=True,
                     oversized_censuses=["D8_1"], catagolue_costs=cata_costs)
    # objects = [x for x in objects if cost(x[0]) > 999]
    for obj in objects:
            print(f"{obj[0]} - {obj[1]}")
            outfile.write(f"{obj[0]} {obj[1]}\n")

    outfile = open(outfolder + "c1_unsynthed_with_soups.txt", "w")
    objects = getall(symmetries=["C1"], folder=censusfolder, bitcount=None, unsynthed=True, usecatacosts=True,
                     oversized_censuses=None, catagolue_costs=cata_costs)
    # objects = [x for x in objects if cost(x[0]) > 999]
    for obj in objects:
            print(f"{obj[0]} - {obj[1]}")
            outfile.write(f"{obj[0]} {obj[1]}\n")
    # outfile = open(censusfolder + "/all_unsynthed_with_soups.txt", "w")
    # objects = getall(symmetries=None, folder=censusfolder, bitcount=None, unsynthed=True,
    #                  usecatacosts=True, catagolue_costs=cata_costs,
    #                  oversized_censuses=["D8_1"])
    # for i, obj in enumerate(objects):
    #     if i < 1000:
    #         print(f"{obj[0]} - {obj[1]}")
    #     outfile.write(f"{obj[0]} {obj[1]}\n")
    # print(f"found {len(objects)} unsynthed")
