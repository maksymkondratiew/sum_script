from PIL import Image, UnidentifiedImageError
import sys
import os


def image_to_bitmap(image_path):
    """
    Converts any image to a black and white bitmap.
    """
    try:
        img = Image.open(image_path)
    except UnidentifiedImageError:
        print(f"Error: Unable to open image file '{image_path}'.")
        sys.exit(1)

    # Checking the format for alpha channel support
    supports_alpha = img.format in {"PNG", "GIF", "WEBP", "TIFF"}

    if img.format == "GIF":  # For multi-frame GIFs
        img.seek(0)  # We use only the first frame

    img = img.convert("RGBA") if supports_alpha else img.convert("RGB")

    # If alpha is supported, we check for its presence
    alpha_present = False
    if supports_alpha:
        alpha_channel = img.getchannel("A")
        alpha_present = any(pixel < 255 for pixel in alpha_channel.getdata())

    # Convert to bitmap
    img_bw = img.convert("1")  # Conversion to b/w

    return img_bw, alpha_present


def bitmap_to_sum_script(img_bw, alpha_present, script_path):
    """
    Generates the text script `sum1.0` from a black and white image.
    """
    width, height = img_bw.size
    pixels = img_bw.load()
    background = "t" if alpha_present else "w"

    pixel_data = {}

    # We read pixels and write only black ones
    for y in range(height):
        black_pixels = []
        for x in range(width):
            if pixels[x, y] == 0:  # Black pixel
                black_pixels.append(x + 1)

        # We generate data only for rows with black pixels
        if black_pixels:
            ranges = []
            start = black_pixels[0]
            for i in range(1, len(black_pixels)):
                if black_pixels[i] != black_pixels[i - 1] + 1:  # End of range
                    ranges.append(f"{start}-{black_pixels[i - 1]}" if start != black_pixels[i - 1] else f"{start}")
                    start = black_pixels[i]
            ranges.append(f"{start}-{black_pixels[-1]}" if start != black_pixels[-1] else f"{start}")
            pixel_data[y + 1] = ",".join(ranges)

    # Generating a script
    with open(script_path, "w") as f:
        f.write(f"!sum1.0\n")
        f.write(f"s={width}x{height};\n")
        f.write(f"bpx={background};\n")
        f.write("b{\n")
        for row, data in pixel_data.items():
            f.write(f"{row}:{data};\n")
        f.write("}\n")
    print(f"Script saved as {script_path}")


def convert_image_to_sum(image_path):
    """
    The main function for converting an image to `sum1.0`.
    """
    base_name, _ = os.path.splitext(image_path)
    script_path = f"{base_name}.txt"

    # Convert to bitmap and determine the presence of an alpha channel
    img_bw, alpha_present = image_to_bitmap(image_path)

    # Generating a script
    bitmap_to_sum_script(img_bw, alpha_present, script_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python img2sum.py <image_file>")
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.isfile(image_path):
        print(f"Error: File '{image_path}' not found.")
        sys.exit(1)

    try:
        convert_image_to_sum(image_path)
    except Exception as e:
        print(f"Error: {e}")
