import operator
import subprocess

from cgol_utils.fileutils import parse_objects_file
from cgol_utils.paths import cgolroot
from cgol_utils.utils import get_sorted_sls, cata_costs, min_paths, trueSLs, cost


def run(command):
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    return output, error


bitcount = 22
xs22codes = parse_objects_file(f"{cgolroot}/censuses/22_bits_strict_apgcodes.txt")
unsynthed = [x for x in xs22codes if cost(x) > 999]

run(f"curl -o xs{bitcount}.txt https://catagolue.appspot.com/textcensus/b3s23/C1/xs{bitcount}")
# run(f"curl -o xs{bitcount}-synth.txt https://catagolue.appspot.com/textcensus/b3s23/synthesis-costs/xs{bitcount}")

# stills = get_sorted_sls(min_paths, trueSLs, cata_costs)

# unsynthed = []
# with open(f"xs{bitcount}-synth.txt") as Fin:
#     for line in Fin.readlines():
#         if not line[1:5] == f"xs{bitcount}":
#             continue
#         parts = line.split(',')
#         code = parts[0].strip('"')
#         cost = parts[1].strip().strip('"')
#         if code not in cata_costs or cata_costs[code] == 9999:
#             unsynthed.append(code)

occurrences = []
with open(f"xs{bitcount}.txt") as Fin:
    for line in Fin.readlines():
        if not line[1:5] == f"xs{bitcount}":
            continue
        parts = line.split(',')
        code = parts[0].strip('"')
        if code in unsynthed:
            cost = int(parts[1].strip().strip('"'))
            occurrences.append((code, cost))

occurrences.sort(key=operator.itemgetter(1), reverse=True)
for object in occurrences:
    print("{} - {}".format(object[0], object[1]))
