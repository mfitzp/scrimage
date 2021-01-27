from PIL import Image, ImagePalette
import os
import sys

import argparse

from scrimage.palette import SAM_PALETTE


parser = argparse.ArgumentParser(description='Convert SAM Coupe SCREEN$ files to image (PNG, BMP or GIF formats).')
parser.add_argument('screen', type=str, nargs='+',
                    help='source SCREEN$ file(s) to process.')

# We can easily support any other formats.
parser.add_argument('--format', '-f', type=str.lower, choices=['png', 'bmp', 'gif'], default='PNG', help='Output file format, one of (PNG, BMP, GIF).')
parser.add_argument('--outfile', '-o', type=str, help='Output file. Will output to {filename}.ext if not provided.')



def generate_image(pixels, indexed_palette):
    """
    Create an RGB Pillow image from an array of pixels & an indexed palette.
    """
    irgb = b''
    for p in pixels:
        irgb += bytes(indexed_palette[p])

    image = Image.frombytes('RGB', (256, 192), irgb)
    return image


def apply_line_interrupts(image, lineint, palette, indexed_palette):

    pixels = image.load()

    for y, c, p1, p2 in zip(lineint[::4], lineint[1::4], lineint[2::4], lineint[3::4]):

        p = p1 if palette == 0 else p2

        oldcolor = indexed_palette[c]
        newcolor = SAM_PALETTE[p]

        # This is inefficient (numpy?) but we've got small images.
        for yp in range(y+1, 192):
            for x in range(0, 256):
                if pixels[x, yp] == oldcolor:
                    pixels[x, yp] = newcolor

        indexed_palette[c] = newcolor

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


        # Get a list of 3-tuples.
        palette_index_a = [SAM_PALETTE[i] for i in palette_a]
        image_a = generate_image(pixels, palette_index_a)

        # Normally these are not set.
        palette_index_b = None
        image_b = None

        if palette_a != palette_b:
            if args.format == 'gif':
                palette_index_b = [SAM_PALETTE[i] for i in palette_b]
                image_b = generate_image(pixels, palette_index_b)

            else:
                print("Two palettes differ, screen was flashing. Use GIF export to capture animation.")

        if extra4_a != extra4_b:
            print("Mismatch in 4 bytes? I don't know what this means, do you?")

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
            apply_line_interrupts(image_a, lineint, 0, palette_index_a)

            if image_b:
                apply_line_interrupts(image_b, lineint, 1, palette_index_b)

        save_args = {}

        if image_b:
            # Convert images to paletted, to avoid dither on export to GIF.
            image_a = image_a.convert('P', palette=Image.ADAPTIVE)
            image_b = image_b.convert('P', palette=Image.ADAPTIVE)

            save_args = {'save_all': True, 'append_images': [image_b], 'duration':333, 'loop':0, 'interlace':False}

        if args.outfile:
            outfile = args.outfile

        else:
            filename, _ = os.path.splitext(fn)
            outfile = f'{filename}.{args.format}'

        image_a.save(outfile, **save_args)

