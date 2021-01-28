"""
Methods for optimizing the number of colours in an image, using interrupts.
"""

from PIL import Image
from collections import defaultdict
from itertools import permutations
from itertools import permutations
import numpy as np

MAX_INTERRUPTS = 50

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
            blocks = colors[n:]
            for b in blocks[::-1]:  # Reverse, smallest coverage into largest.

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



def simplify(cssp):

    # Decomplexify: if a given color still exists, and we fit, may as
    # well use it for it's own colors to minimize transitions & interrupts.
    csspr = cssp.copy()
    for k, v in cssp.items():
        for b in v:
            color = b[0]
            if color in csspr and not has_clash(csspr[color], [b]):
                # Color still exists.
                csspr[color].append(b)
                csspr[k].remove(b)

    # Sort blocks.
    for k in csspr.keys():
        csspr[k] = sorted(csspr[k], key=lambda x:x[1])

    # Decomplexify: remove redundant blocks where adjacent colors are the same.
    csspm = defaultdict(list)
    for k, v in csspr.items():
        last_block = v[0]
        for b in v[1:]:
            if b[0] == last_block[0]: # Same color.
                last_block = (last_block[0], last_block[1], b[2])  # updated end.

            else:
                csspm[k].append(last_block)
                last_block = b

        csspm[k].append(last_block)

    # Reduce color numbers: here color values can be anything up to max n_colors
    # with gaps, etc. Normalize these down to fill the range 0-MAX_COLORS.
    # We can remap to palette index here, as it's meaningless.
    csspm = {n:v for n, (k, v) in enumerate(csspm.items())}

    return csspm

def calculate_color_regions(im, n_colors):
    """
    Quantize the image to a given n_colors and then calculate all the
    color regions in the image: a (start, stop) for each block of a given colour.

    Each color is calculated individually, then compressed to reduce the number
    of colors in the image.
    """
    col = im.quantize(colors=n_colors, method=Image.MAXCOVERAGE, kmeans=1)
    pix = np.array(col)
    cssp = color_start_stop_partial(pix)
    return compress_non_overlapping(cssp)


def n_interrupts(regions):
    """ Calculate the number of interrupts required """
    return len([v for region in regions.values() for v in region])


def optimize(im, max_colors, total_n_colors):
    """
    Attempts to optimize the number of colors in the screen using interrupts. The
    result is a dictionary of color regions, keyed by color number
    """
    optimal_n_colors = max_colors
    optimal_color_regions = {}
    optimal_total_interrupts = 0

    for n_colors in range(max_colors, total_n_colors+1):
        color_regions = calculate_color_regions(im, n_colors)
        total_colors = len(color_regions)

        # Simplify our color regions.
        color_regions = simplify(color_regions)

        # Calculate home many interrupts we're using, length drop initial.
        _, interrupts = split_initial_colors(color_regions)
        total_interrupts = n_interrupts(interrupts)

        print("- trying %d colors, with interrupts uses %d colors & %d interrupts" % (n_colors, total_colors, total_interrupts))

        if total_colors <= max_colors and total_interrupts <= MAX_INTERRUPTS:
            optimal_n_colors = n_colors
            optimal_color_regions = color_regions
            optimal_total_interrupts = total_interrupts
            continue
        break

    print("Optimized to %d colors with %d interrupts (using %d palette slots)" % (optimal_n_colors, optimal_total_interrupts, len(optimal_color_regions)))
    return optimal_n_colors, optimal_color_regions


def split_initial_colors(color_regions):
    """
    Split initial color from the rest of the (interrupts)
    """
    initial_colors = {}
    interrupt_regions = defaultdict(list)

    for k, v in color_regions.items():
        initial_color, _, _ = v[0]

        interrupt_regions[k] = v[1:]
        initial_colors[k] = initial_color

    return initial_colors, interrupt_regions

def normalize_colors(data, color_regions):
    """
    Modify the image to set all pixels to a SAM palette value (0-15).
    Applies for both base colors and those modified by interrupts.
    """

    # Map from the color in the image, to the palette index (SAM Palette) keys of the color_regions.
    color_map = {k:i for i, v in color_regions.items() for k, _, _ in v}

    result = data.copy()

    for color, i in color_map.items():
        result[data == color] = i

    return result, color_regions
