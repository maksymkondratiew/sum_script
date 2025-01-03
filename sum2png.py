import sys
from PIL import Image

def parse_sum_script(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Ініціалізуємо змінні
    size = (0, 0)
    background = "w"  # White background by default
    pixel_data = {}

    # Парсинг рядків
    for line in lines:
        line = line.strip()
        if line.startswith('!'):  # Ignore the title
            continue
        if line.startswith('s='):  # Size
            size = tuple(map(int, line[2:].strip(';').split('x')))
        elif line.startswith('bpx='):  # background
            background = line[4:].strip(';')
        elif line.startswith('b{'):  # Start of section
            continue
        elif line.startswith('}'):  # End of section
            break
        else:  # Pixel rows
            row, data = line.split(':')
            row = int(row)
            data = data.strip(';')  # Remove the extra semicolon
            if data.startswith('d'):  # draw command
                pixel_data[row] = pixel_data[int(data[1:])]
            else:  # Ranges
                pixel_data[row] = []
                for part in data.split(','):
                    part = part.strip()  # Removing extra spaces
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        pixel_data[row].extend(range(start, end + 1))
                    else:
                        pixel_data[row].append(int(part))

    return size, background, pixel_data

def generate_image(size, background, pixel_data, output_path='output.png'):
    width, height = size

    # We determine the color model depending on the background
    if background == "w":
        mode = "1"  # Black and white, Indexed 2 colors
        img = Image.new(mode, (width, height), 1)  # 
    else:
        mode = "LA"  # Grayscale + Alpha
        img = Image.new(mode, (width, height), (255, 0))  # Transparent background

    pixels = img.load()

    # Filling in black pixels
    for row, cols in pixel_data.items():
        for col in cols:
            if background == "w":
                pixels[col - 1, row - 1] = 0  # Black pixel
            else:
                pixels[col - 1, row - 1] = (0, 255)  # Black + opaque

    # Saving the image
    img.save(output_path, optimize=True)
    print(f"Image saved as {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sum2png.py <script_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    output_path = file_path.rsplit('.', 1)[0] + ".png"

    # Parsing and image generation
    size, background, pixel_data = parse_sum_script(file_path)
    generate_image(size, background, pixel_data, output_path)
