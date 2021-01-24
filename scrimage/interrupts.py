"""
Methods for optimizing the number of colours in an image, using interrupts.
"""

from PIL import Image
from collections import defaultdict
from itertools import permutations
import numpy as np


def color_start_stop_partial(pix):
    # Get start and stop lines for each color, counting partial blocks longer than n
    n_colors = np.max(pix) + 1

    colorst = defaultdict(list)

    for c in range(n_colors):
        start, stop = None, None
        for y in range(192):
            wo = np.any(pix[y, :] == c)
            if wo:
                if not start:
                    start = y
                stop = y
            if not wo or y == 191: # end
                if start:
                    colorst[c].append((c, start, stop))
                    start, stop = None, None

    return colorst


def has_clash(a, b):
    # Return true if either a or b's intervals overlap.
    for _, astart, astop in a:
        for _, bstart, bstop in b:
            if (
                (astart >= bstart and astart <= bstop) or
                (bstart >= astart and bstart <= astop) or
                (astop >= bstart and astop <= bstop) or
                (bstop >= astart and bstop <= astop)
            ):
                return True
    return False


def compress_non_overlapping(cssp):

    has_compressed = True

    def coverage(c):
        return sum((end-start) for _, start, end in cssp[c])

    while has_compressed:

        to_combine = None
        has_compressed = False

        # Sort colors by the total coverage (lines)
        colors = list(cssp.keys())
        colors = sorted(colors, key=coverage)

        for n, a in enumerate(colors):
            for b in colors[n:]:

                if not has_clash(cssp[a], cssp[b]):
                    to_combine = (a, b)
                    break

            if to_combine:
                break

        if to_combine:
            a, b = to_combine
            cssp[a].extend(cssp[b])
            del cssp[b]
            has_compressed = True


    return cssp


def calculate_color_regions(im, n_colors):
    col = im.quantize(colors=n_colors, method=Image.MAXCOVERAGE, kmeans=1)
    pix = np.array(col)
    cssp = color_start_stop_partial(pix)
    return compress_non_overlapping(cssp)



def optimize(im, max_colors, total_n_colors):

    for n_colors in range(max_colors, total_n_colors+1):
        color_regions = calculate_color_regions(im, n_colors)
        total_colors = len(color_regions)
        print("Optimizing: %d colors, using %d colors" % (n_colors, ))
        if total_colors <= max_colors:
            last_n_colors = n_colors
            continue
        break
        print("Total colors %d" % total_colors)


    return color_regions


