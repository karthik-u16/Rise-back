from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os

out_dir = os.path.join('riseback_mobile', 'assets', 'images')
os.makedirs(out_dir, exist_ok=True)

sizes = [(1800, 600), (1200, 400), (900, 300)]  # large base sizes

# theme colors
level_colors = ((14,17,21), (255,80,0))  # dark to ember
xp_colors = ((10,16,30), (212,164,55))   # dark to gold
evo_colors = ((12,10,20), (123,65,255))  # dark to purple

fonts = None
try:
    fonts = ImageFont.truetype('arial.ttf', 48)
except Exception:
    fonts = None

def draw_gradient(img, color1, color2):
    w,h = img.size
    base = Image.new('RGB', img.size, color1)
    top = Image.new('RGB', img.size, color2)
    mask = Image.new('L', img.size)
    mask_data = []
    for y in range(h):
        mask_data.extend([int(255 * (y / h))] * w)
    mask.putdata(mask_data)
    return Image.composite(top, base, mask)

def add_texture(draw, w, h, color):
    for i in range(0, w, 80):
        draw.line(((i,0),(i-200,h)), fill=(255,255,255,8), width=2)

for name, colors in [('level_card', level_colors), ('xp_card', xp_colors), ('evolution_card', evo_colors)]:
    for size in sizes:
        img = Image.new('RGB', size, colors[0])
        grad = draw_gradient(img, colors[0], colors[1])
        grad = grad.filter(ImageFilter.GaussianBlur(radius=8))
        draw = ImageDraw.Draw(grad, 'RGBA')
        # add soft circles
        w,h = size
        for i in range(3):
            rx = int(w * (0.2 + 0.25*i))
            ry = int(h * (0.3 + 0.1*i))
            r = int(min(w,h) * (0.25 - i*0.06))
            draw.ellipse((rx-r, ry-r, rx+r, ry+r), fill=(255,255,255,15))
        # subtle diagonal lines
        for x in range(-w, w*2, 200):
            draw.line((x,0,x-200,h), fill=(255,255,255,10), width=3)
        # overlay vignette
        vign = Image.new('L', size, 0)
        vd = ImageDraw.Draw(vign)
        vd.ellipse((-w*0.2, -h*0.2, w*1.2, h*1.2), fill=255)
        grad.putalpha(vign)
        # flatten to RGB with darken
        bg = Image.new('RGB', size, (6,6,8))
        bg.paste(grad, mask=grad.split()[-1])
        # save
        filename = f"{name}_{size[0]}x{size[1]}.png"
        path = os.path.join(out_dir, filename)
        bg.save(path, optimize=True)
        print('Wrote', path)

# also save default base filenames for easiest reference (largest size)
for name in ['level_card', 'xp_card', 'evolution_card']:
    src = os.path.join(out_dir, f"{name}_{sizes[0][0]}x{sizes[0][1]}.png")
    dst = os.path.join(out_dir, f"{name}.png")
    if os.path.exists(src):
        Image.open(src).save(dst, optimize=True)
        print('Copied', dst)
