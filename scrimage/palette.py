from PIL import Image

# Colors
def get_sam_palette(i):
    """
    For a given SAM Coupe palette index, return the RGB value.
    """
    intensity = [0x00, 0x24, 0x49, 0x6d, 0x92, 0xb6, 0xdb, 0xff ]

    r = (i&0x02)     | ((i&0x20) >> 3) | ((i&0x08) >> 3)
    g = (i&0x04) >> 1| ((i&0x40) >> 4) | ((i&0x08) >> 3)
    b = (i&0x01) << 1| ((i&0x10) >> 2) | ((i&0x08) >> 3)
    return intensity[r], intensity[g], intensity[b]


def distance(c1, c2):
    """
    Calculate distance between two colors in RGB space.

    This isn't perception adjusted, just raw. Pass colors as tuples of (r, g, b).
    """
    r1, g1, b1 = c1
    r2, g2, b2 = c2

    return (
        ((r2-r1))**2 +
        ((g2-g1))**2 +
        ((b2-b1))**2
    )


# SAM Coupe palette as a list of tuples.
SAM_PALETTE = [get_sam_palette(i) for i in range(128)]

# Reverse lookup from RGB value to palette number.
RGB_TO_SAM = {
    c: i for i, c in enumerate(SAM_PALETTE)
}

FLATTENED_SAM_PALETTE = [c for i in SAM_PALETTE for c in i]

# An image containing the SAM Coupe palette, for quantizing.
SAM_PALETTE_IMAGE = Image.new('P', (128, 128))
SAM_PALETTE_IMAGE.putpalette(FLATTENED_SAM_PALETTE)


def pil_to_tuples(rgb):
    result = []
    for r, g, b in zip(rgb[::3], rgb[1::3], rgb[2::3]):
        result.append((r,g,b))
    return result


def convert_image_to_sam_palette(image, colors=16):
    new_palette = []
    rgb = image.getpalette()[:colors*3]
    for r, g, b in zip(rgb[::3], rgb[1::3], rgb[2::3]):

        def distance_to_color(o):
            return distance(o, (r, g, b))

        spalette = sorted(SAM_PALETTE, key=distance_to_color)
        new_palette.append(spalette[0])

    palette = [c for i in new_palette for c in i]
    image.putpalette(palette)
    return image



def pil_to_sam_palette(pilpal):
    palette = pil_to_tuples(pilpal)
    return [RGB_TO_SAM[c] for c in palette]
