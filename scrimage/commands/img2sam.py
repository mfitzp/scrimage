from PIL import Image, ImagePalette, ImageOps

import os
import sys
import argparse

import numpy as np
from scrimage.palette import SAM_PALETTE, SAM_PALETTE_IMAGE, pil_to_tuples, RGB_TO_SAM, convert_image_to_sam_palette, pil_to_sam_palette
from scrimage.interrupts import optimize, split_initial_colors, normalize_colors

SAM_COUPE_MODE4 = (256, 192, 16)
WIDTH, HEIGHT, MAX_COLORS = SAM_COUPE_MODE4


parser = argparse.ArgumentParser(description='Convert Image to SAM Coupe SCREEN$ format. Optional interrupt optimizations.')
parser.add_argument('image', type=str, nargs='+',
                    help='source image file(s) to process.')

parser.add_argument('--interrupts', '-i', default=False, action="store_true", help='Add (automatic) interrupts to maximise image colors.')
parser.add_argument('--dither', '-d', default=False, action="store_true", help='Dither image using SAM palette before reducing colors.')
parser.add_argument('--outfile', '-o', type=str, help='Output file. Will output to {filename}.scr if not provided.')



def main():

    args = parser.parse_args()

    for fn in args.image:
        im = Image.open(fn)

        # Resize with crop to fit.
        im = ImageOps.fit(im, (WIDTH, HEIGHT), Image.ANTIALIAS, 0, (0.5, 0.5))

        # Dither
        if args.dither:
            # Apply a dither, using the full SAM palette. Reduced in subsequent steps.
            im = im.quantize(palette=SAM_PALETTE_IMAGE, dither=1)


        if args.interrupts:
            # How many colors are in the image? Upper bounds of what we can achieve (max 127)
            max127 = im.quantize(colors=127, method=Image.MAXCOVERAGE, kmeans=1)
            total_n_colors = np.max(max127) + 1

            # Optimized color regions.
            optimal_n_colors, color_regions = optimize(im, MAX_COLORS, total_n_colors)

            # Convert image to our target max colors (this repeats operation)
            image16 = im.quantize(colors=optimal_n_colors, method=Image.MAXCOVERAGE, kmeans=1)

            # Apply the SAM Coupe palette.
            image16 = convert_image_to_sam_palette(image16, colors=optimal_n_colors)

            # Extract the complete palette, so we can use for interrupts.
            pilpal = image16.getpalette()[:optimal_n_colors*3]
            large_palette = pil_to_sam_palette(pilpal)

            pixels = np.array(image16)

            # Our palette has values > 16. We need to normalize the color regions, so colors are
            # numbered in valid range (0-15). Then replace all blocks with that colour.
            # We need to re-map our base palette in the same way.

            # Replace values > 16; and apply the interrupt map.
            pixels, color_regions = normalize_colors(pixels, color_regions)

            # Seperate initial colors (represented in the palette) from the interrupts.
            initial_colors, interrupt_regions = split_initial_colors(color_regions)

            # Build the palette form the initial colors
            palette = [large_palette[v] for k, v in initial_colors.items()]

            palette = bytearray(palette)
            interrupts = b''

            # Build the interrupt map as: position, palette, color, color
            interrupts = []
            for color, regions in interrupt_regions.items():
                # We don't need the stop.
                for to_color, y, _ in regions:
                    target = large_palette[to_color]
                    interrupts.append((y-1, color, target, target))

            interrupts = sorted(interrupts)
            interrupts = [x for i in interrupts for x in i]
            interrupts = bytearray(interrupts)

        else:
            # Convert image to our target max colors
            image16 = im.quantize(colors=MAX_COLORS, method=Image.MAXCOVERAGE, kmeans=1)

            interrupts = b''

            # Apply the SAM Coupe palette.
            image16 = convert_image_to_sam_palette(image16)

            pixels = np.array(image16)

            # Get pillow palette, extract
            pilpal = image16.getpalette()[:MAX_COLORS*3]  # 768
            palette = pil_to_sam_palette(pilpal)
            palette = bytearray(palette)


        image_data = []
        pixel_data = pixels.flatten()
        # Generate bytestream and palette; pack to 2 pixels/byte.
        for a, b in zip(pixel_data[::2], pixel_data[1::2]):
            byte = (a << 4) | b
            image_data.append(byte)

        image_data = bytearray(image_data)



        # Lookup


        # If not all colors used, write default palette over remainder.
        # Avoids loading making text invisible, etc.


        if args.outfile:
            outfile = args.outfile

        else:
            basename = os.path.basename(fn)
            filename, _ = os.path.splitext(basename)
            outfile = f'{filename}.scr'

        # Additional 4 bytes 0, 17, 34, 127; unknown.
        bytes4 = b'\x00\x11\x22\x7F'

        # Ensure palette is 16.
        if len(palette) < 16:
            palette += b'\x7F' * (16 - len(palette))

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



