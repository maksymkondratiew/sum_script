import argparse
from PIL import Image
import sys

def convert_image_to_sum(image_path, output_path):
    img = Image.open(image_path)
    img = img.convert("RGBA")  # Перевести в RGBA, щоб працювати з прозорістю

    # Визначаємо розміри зображення
    width, height = img.size
    sum_script = []
    
    # Визначаємо, чи є прозорість
    has_transparency = False
    pixels = img.load()

    for y in range(height):
        row = []
        for x in range(width):
            r, g, b, a = pixels[x, y]

            # Якщо піксель чорний
            if r == 0 and g == 0 and b == 0:
                row.append(f"{x+1}")
            # Якщо піксель білий
            elif r == 255 and g == 255 and b == 255:
                continue  # Білий піксель не записуємо
            # Якщо піксель прозорий
            elif a == 0:
                has_transparency = True
                continue  # Прозорі пікселі не записуємо

        if row:
            sum_script.append(f"{y+1}:{','.join(row)};")

    # Зберігаємо результат у файл
    with open(output_path, 'w') as f:
        f.write(f"!sum1.1\n")
        f.write(f"s={width}x{height};\n")
        f.write("bpx=w;\n")  # Білий фон
        f.write("b{\n")
        for line in sum_script:
            f.write(line + "\n")
        f.write("}\n")
    
    print(f"SUM script saved to {output_path}")


def draw_frame(frame_data, img, width, height):
    img = img.convert("RGBA")  # Конвертуємо в формат RGBA (для підтримки альфа-каналу)

    # Проходимо по всіх пікселях у frame_data
    for row_data in frame_data:
        for pixel in row_data:
            row = int(pixel[0]) - 1  # Конвертуємо до індексу (0-based)
            pixel_pos = int(pixel[1]) - 1  # Те саме для стовпця

            # Заміна кольору пікселя: чорний або білий залежно від типу пікселя
            if pixel[2] == 'd1':  # Якщо чорний піксель
                img.putpixel((pixel_pos, row), (0, 0, 0, 255))  # Чорний піксель (RGB)
            elif pixel[2] == 'w':  # Якщо білий піксель
                img.putpixel((pixel_pos, row), (255, 255, 255, 255))  # Білий піксель (RGB)
            else:  # Прозорі пікселі
                img.putpixel((pixel_pos, row), (0, 0, 0, 0))  # Прозорий піксель

    return img


def parse_sum_script(input_path):
    with open(input_path, 'r') as file:
        lines = iter(file.readlines())  # Робимо ітератор для зручності

    fps = None
    frames = []
    body_pixels = {'width': 0, 'height': 0, 'pixels': []}

    for line in lines:
        line = line.strip()

        if line.startswith('s='):  # Розмір зображення
            size = line.split('=')[1].strip(';')
            width, height = map(int, size.split('x'))
            body_pixels['width'] = width
            body_pixels['height'] = height

        elif line.startswith('fps='):  # FPS для анімації
            fps = float(line.split('=')[1])

        elif line.startswith('bpx='):  # Тип фону (білий або прозорий)
            body_pixels['bpx'] = line.split('=')[1].strip(';')

        elif line.startswith('b{'):  # Початок статичних пікселів
            while True:
                line = next(lines).strip()
                if line.startswith('}'):  # Кінець секції
                    break
                if ':' not in line:  # Пропускаємо некоректні рядки
                    continue
                row, cols = line.split(':')
                cols = parse_pixels(cols.strip(';'), body_pixels['width'], [])
                body_pixels['pixels'].append((int(row), cols))

        elif line.startswith('f'):  # Початок кадру
            current_frame = []
            current_frame_rows = []  # Локальний список для дублювання в межах кадру
            while True:
                line = next(lines).strip()
                if line.startswith('}'):  # Кінець кадру
                    break
                if ':' not in line:  # Пропускаємо некоректні рядки
                    continue
                row, cols = line.split(':')
                cols = parse_pixels(cols.strip(';'), body_pixels['width'], current_frame_rows)
                current_frame.append((int(row), cols))
                current_frame_rows.append(cols)
            frames.append(current_frame)  # Додаємо кадр після завершення секції

    # Якщо немає кадрів, використовуємо статичні пікселі
    if not frames:
        frames = [body_pixels['pixels']]

    print(f"Parsed SUM Script:\nFPS: {fps}\nFrames: {len(frames)}\nBody Pixels: {body_pixels}")
    return fps, frames, body_pixels


def export_to_image(frames, fps, body_pixels, format_type, input_path, is_animated=False):
    if not frames:
        print("Error: No frames found in the SUM script.")
        return

    if format_type == 'GIF':
        image_frames = [
            create_image_from_frame(frame, body_pixels['width'], body_pixels['height'], body_pixels['bpx'])
            for frame in frames
        ]
        output_path = input_path.replace('.sum', '.gif')
        if is_animated and len(image_frames) > 1:
            image_frames[0].save(
                output_path,
                save_all=True,
                append_images=image_frames[1:],
                duration=int(1000 / fps) if fps else 100,  # Використовуємо fps або 100 мс за замовчанням
                loop=0,
                disposal=2  # Очищення попереднього кадру
            )
            print(f"Saved animated GIF to {output_path}")
        else:
            print("Error: Cannot export animated GIF with less than 2 frames.")
    else:
        img = create_image_from_frame(frames[0], body_pixels['width'], body_pixels['height'], body_pixels['bpx'])
        output_path = input_path.replace('.sum', '.png')
        img.save(output_path, 'PNG')
        print(f"Saved PNG image to {output_path}")

def parse_pixels(pixel_data, width, current_frame_rows):
    """
    Парсинг рядка пікселів, підтримує діапазони (наприклад, 1-5), одиничні значення,
    та дублікати рядків (наприклад, d1, d2) в межах поточного кадру.
    """
    result = []
    for part in pixel_data.split(','):
        part = part.strip()
        if not part:  # Пропускаємо порожні значення
            continue
        if '-' in part:  # Якщо це діапазон
            start, end = map(int, part.split('-'))
            result.extend(range(start, end + 1))
        elif part.startswith('d'):  # Якщо це дублікати (наприклад, d1)
            duplicate_row = int(part[1:])  # Номер рядка для дублювання
            if duplicate_row - 1 < len(current_frame_rows):
                result.extend(current_frame_rows[duplicate_row - 1])  # Дублюємо рядок з поточного кадру
            else:
                print(f"Warning: Invalid duplicate reference '{part}' in the current frame. Skipping.")
        else:  # Одиничний піксель
            result.append(int(part))
    return result


def create_image_from_frame(frame_data, width, height, bpx):
    """
    Створює зображення з кадру.
    frame_data: список кортежів (номер рядка, список пікселів).
    width, height: розміри зображення.
    bpx: тип фону ('w' для білого, 't' для прозорого).
    """
    # Вибір кольору фону на основі bpx
    if bpx == 'w':
        background_color = (255, 255, 255, 255)  # Білий фон
    elif bpx == 't':
        background_color = (255, 255, 255, 0)  # Прозорий фон
    else:
        raise ValueError(f"Unsupported bpx value: {bpx}")

    img = Image.new("RGBA", (width, height), background_color)  # Створюємо зображення з фоном

    for row, pixels in frame_data:
        for pixel in pixels:
            img.putpixel((pixel - 1, row - 1), (0, 0, 0, 255))  # Чорний піксель

    return img



def main():
    parser = argparse.ArgumentParser(description="Convert SUM script to image or vice versa.")
    parser.add_argument('input_file', help="Input file (image or SUM script)")
    parser.add_argument('-f', choices=['png', 'gif'], required=True, help="Output format: png or gif")
    parser.add_argument('-a', action='store_true', help="Export as animated GIF (only with -f gif)")
    parser.add_argument('-c', action='store_true', help="Convert image to SUM script")

    args = parser.parse_args()

    # Якщо вказано ключ -c, конвертуємо зображення в SUM
    if args.c:
        if not args.input_file.lower().endswith(('.png', '.jpg', '.jpeg')):
            print("Error: -c option requires an image file (png, jpg, jpeg).")
            sys.exit(1)
        
        output_path = args.input_file.replace('.png', '.sum').replace('.jpg', '.sum')
        convert_image_to_sum(args.input_file, output_path)

    # Якщо вказано SUM-скрипт для експорту, обробляємо його
    else:
        if not args.input_file.lower().endswith('.sum'):
            print("Error: Input file must be a .sum script.")
            sys.exit(1)
        
        fps, frames, body_pixels = parse_sum_script(args.input_file)
        
        if args.f == 'png':
            export_to_image(frames, fps, body_pixels, 'PNG', args.input_file, False)
        elif args.f == 'gif':
            if args.a:
                export_to_image(frames, fps, body_pixels, 'GIF', args.input_file, True)
            else:
                # Якщо GIF без ключа -a, то тільки перший кадр
                export_to_image(frames[:1], fps, body_pixels, 'GIF', args.input_file, False)


if __name__ == "__main__":
    main()
