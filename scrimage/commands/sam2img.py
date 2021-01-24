from PIL import Image, ImagePalette
import os
import sys

import argparse

from scrimage.palette import SAM_PALETTE


parser = argparse.ArgumentParser(description='Convert SAM Coupe SCREEN$ files to image (PNG, BMP or GIF formats).')
parser.add_argument('screen', type=str, nargs='+',
                    help='source SCREEN$ file(s) to process.')

# parser.add_argument('--palette', '-p', type=int, choices=[0, 1], default=0, help='Palette to use (0, 1) from the screen: 2nd palette used for flashing effects.')

# We can easily support any other formats.
parser.add_argument('--format', '-f', type=str.lower, choices=['png', 'bmp', 'gif'], default='PNG', help='Output file format, one of (PNG, BMP, GIF).')
parser.add_argument('--outfile', '-o', type=str, help='Output file. Will output to {filename}.ext if not provided.')


def main():

    args = parser.parse_args()

    if len(args.screen) > 1 and args.outfile:
        print("Cannot specify output filename when processing multiple files.")
        exit(1)

    for fn in args.screen:

        with open(fn, 'rb') as f:
            data = f.read()

        # Image data, 4bpp, unpack.
        pixels = []

        # Pixel data is the first 24576 bytes.
        pixel_data = data[:24576]

        for b in pixel_data:
            # Unpack 4bpp to 8bpp for PIL.
            high, low = b >> 4, b & 0x0F
            pixels.extend([high, low])

        # Palette data is at the end.
        palette_data = data[24576:]

        # Format is
        # 16 bytes palette
        # 4 bytes of fun (?)
        # 16 bytes palette (repeated) for the alternate color (flash 3x / second)
        # 4 bytes of fun repeated (?)
        # line interrupts.
        # FF

        # are the 4 bytes maybe MODE 3?

        palette_a = palette_data[0:16]

        # We only really care about palette_a, but get the rest anyway.
        # could generate gifs of flashing screens!
        extra4_a = palette_data[16:20]
        palette_b = palette_data[20:36] # 2nd palette, flashing.
        extra4_b = palette_data[36:40] # repeat
        lineint = palette_data[40:-1]  # ends FF

        if palette_a != palette_b:
            print("Two palettes differ, screen was flashing.")

        if extra4_a != extra4_b:
            print("Mismatch in 4 bytes?")

        # Get a list of 3-tuples.
        pindex = [SAM_PALETTE[i] for i in palette_a]

        irgb = b''
        for p in pixels:
            irgb += bytes(pindex[p])

        image = Image.frombytes('RGB', (256, 192), irgb)

        # If we have line interrupts, we need to change the color from particular points
        # in the image downwards. Interrupts are stored as 4-bytes (position, palette, color, color)
        # -- color is repeated, for the flashing effect as before.
        #
        # Interrupt coordinates are from bottom left -18, and go to 172
        # Y is max 172, which means the top of the screen (0, 0 in image)
        # Plot range is 0..173, meaning the interrupt can't affect the first pixel?
        #
        # Line interrupt at 150 is stored in file as 22, i.e. 172-y = value
        # but we can use the positions directly, since it gives the
        # pixel location in the resulting image.

        if lineint:
            # Get a pixel map to the image.
            pixels = image.load()

            for y, c, p1, p2 in zip(lineint[::4], lineint[1::4], lineint[2::4], lineint[3::4]):

                if p1 != p2:
                    print("Two palettes (interrupt) differ, screen was flashing.")

                oldcolor = pindex[c]
                newcolor = SAM_PALETTE[p1]

                # This is inefficient (numpy?) but we've got small images.
                for yp in range(y+1, 192):
                    for x in range(0, 256):
                        if pixels[x, yp] == oldcolor:
                            pixels[x, yp] = newcolor

                pindex[c] = newcolor


        if args.outfile:
            outfile = args.outfile

        else:
            filename, _ = os.path.splitext(fn)
            outfile = f'{filename}.{args.format}'

        image.save(outfile)
