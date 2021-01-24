from PIL import Image, ImagePalette, ImageOps

import os
import sys
import argparse

import numpy as np
from scrimage.palette import SAM_PALETTE, SAM_PALETTE_IMAGE, pil_to_tuples, RGB_TO_SAM
from scrimage.interrupts import optimize

SAM_COUPE_MODE4 = (256, 192, 16)
WIDTH, HEIGHT, MAX_COLORS = SAM_COUPE_MODE4


parser = argparse.ArgumentParser(description='Convert Image to SAM Coupe SCREEN$ format. Optional interrupt optimizations.')
parser.add_argument('image', type=str, nargs='+',
                    help='source image file(s) to process.')

parser.add_argument('--interrupts', '-i', type=bool, default=False, help='Add (automatic) interrupts to maximise image colors.')
parser.add_argument('--dither', '-d', type=bool, default=False, help='Dither image using SAM palette before reducing colors.')
parser.add_argument('--outfile', '-o', type=str, help='Output file. Will output to {filename}.scr if not provided.')



def main():

    args = parser.parse_args()

    for fn in args.image:
        im = Image.open(fn)


        # Resize with crop to fit.
        im = ImageOps.fit(im, (WIDTH, HEIGHT), Image.ANTIALIAS, 0, (0.5, 0.5))

        # How many colors are in the image? Upper bounds of what we can achieve (max 127)
        max127 = im.quantize(colors=127, method=Image.MAXCOVERAGE, kmeans=1)
        total_n_colors = np.max(max127) + 1

        # Dither
        if args.dither:
            # Apply a dither, using the full SAM palette. Reduced in next steps.
            im = im.quantize(palette=SAM_PALETTE_IMAGE, dither=1)


        if args.interrupts:
            # Optimized color regions.
            color_regions = optimize(im, MAX_COLORS, total_n_colors)
            opt_max_colors = len(color_regions)

        else:
            # Normal 16 color image.
            opt_max_colors = MAX_COLORS

            # Convert image to our target max colors
            image16 = im.quantize(colors=MAX_COLORS, method=Image.MAXCOVERAGE, kmeans=1)

            # Generate bytestream and palette; need to pack to 2 colors/byte.
            pixel_data = np.array(image16).flatten()

            image_data = []
            for a, b in zip(pixel_data[::2], pixel_data[1::2]):
                byte = a | (b << 4)
                image_data.append(byte)

            image_data = bytearray(image_data)

            interrupts = b''

            # Get pillow palette, extract
            pilpal = image16.getpalette()[:MAX_COLORS*3]  # 768
            palette = pil_to_tuples(pilpal)

            # Lookup
            palette = [RGB_TO_SAM[c] for c in palette]
            palette = bytearray(palette)

            # If not all colors used, write default palette over remainder.
            # Avoids loading making text invisible, etc.


        if args.outfile:
            outfile = args.outfile

        else:
            basename = os.path.basename(fn)
            filename, _ = os.path.splitext(basename)
            outfile = f'{filename}.scr'

        # Additional bytes, mode 3 palette?
        bytes4 = b'\x00\x11\x22\x7F'


        with open(outfile, 'wb') as f:
            f.write(image_data)
            # Write palette.
            f.write(palette)

            # Write extra bytes (4 bytes, 2nd palette, 4 bytes)
            f.write(bytes4)
            f.write(palette)
            f.write(bytes4)

            # Write line interrupts
            f.write(interrupts)

            # Write final byte.
            f.write(b'\xff')



