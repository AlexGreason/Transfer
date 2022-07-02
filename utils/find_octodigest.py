import os


def load_digests(digestfile):
    digests = []
    file = open(digestfile, "rb")
    size = os.stat(digestfile).st_size
    ncolls = size//2048
    if size%2048 != 0:
        print("invalid digest file!")
        raise ValueError
    for i in range(ncolls):
        curr = []
        val = file.read(2048)
        for j in range(256):
            curr.append(val[8*j:8*(j+1)])
        digests.append(curr)
    return digests


def lookup_no_dictionary(digest, digestfile):
    digestbytes = to_bytes(digest)
    file = open(digestfile, "rb")
    size = os.stat(digestfile).st_size
    ncolls = size//2048
    results = []
    if size%2048 != 0:
        print("invalid digest file!")
        raise ValueError
    for i in range(ncolls):
        val = file.read(2048)
        for j in range(256):
            thisdigest = val[8*j:8*(j+1)]
            if thisdigest == digestbytes:
                results.append((i, j))
    return results


def get_rle_by_index_from_file(index, rlefile):
    i = 0
    with open(rlefile, "r") as f:
        tmp = []
        for line in f:
            if line == "\n":
                rle = "".join(tmp)
                if i == index:
                    return rle
                i += 1
                tmp = []
            else:
                tmp.append(line)
    return False

def load_rles(rlefile):
    rles = []
    with open(rlefile, "r") as f:
        tmp = []
        for line in f:
            if line == "\n":
                rles.append("".join(tmp))
                tmp = []
            else:
                tmp.append(line)
    return rles

def digests_dict(digests):
    result = {}
    for i in range(len(digests)):
        d = digests[i]
        for j in range(len(d)):
            val = digests[i][j]
            if val not in result:
                result[val] = []
            result[val].append((i, j))
    return result

def to_bytes(digeststr):
    vals = digeststr.split(" ")
    return bytes([int(x) for x in vals])

def lookup(bytestr, ddict, rles):
    print(rles[ddict[to_bytes(bytestr)][0][0]])



if __name__ == "__main__":
    id = 9017
    basepath = "/media/exa/36dc0dbb-9592-429e-b763-0c9682dc28f1/home/exa/Documents/lifestuff"
    # digests = load_digests(f"{basepath}/colllibrary/digests-{id}.txt")
    # ddict = digests_dict(digests)
    # rles = load_rles(f"{basepath}/colllibrary/rles-{id}.txt")
    # print(len(rles))
    digestfile = f"{basepath}/colllibrary/digests-{id}.txt"
    rlefile = f"{basepath}/colllibrary/rles-{id}.txt"
    results = lookup_no_dictionary("4 227 224 172 223 169 214 142", digestfile)
    print(results)
