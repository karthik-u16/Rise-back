from PIL import Image, ImageDraw
import math

# Output dir
OUT_DIR = 'static/workouts'

WIDTH, HEIGHT = 420, 360
BG = (0, 0, 0, 0)  # transparent

# helper to draw stick figure given parameters
def draw_frame(draw, cx, cy, scale, head_offset, torso_angle, left_arm_angle, right_arm_angle, left_leg_angle, right_leg_angle):
    # head
    head_r = int(10 * scale)
    draw.ellipse((cx-head_r, cy-head_r+head_offset, cx+head_r, cy+head_r+head_offset), fill=(252,191,73,255))
    # torso
    torso_len = int(48*scale)
    tx1 = cx
    ty1 = cy+head_r+int(2*scale)+head_offset
    tx2 = tx1 + int(math.sin(math.radians(torso_angle))*6*scale)
    ty2 = ty1 + torso_len
    draw.line((tx1, ty1, tx2, ty2), fill=(241,236,224,255), width=int(6*scale))
    # arms
    arm_len = int(40*scale)
    lax = tx1 + int(math.sin(math.radians(left_arm_angle))*arm_len)
    lay = ty1 + int(math.cos(math.radians(left_arm_angle))*arm_len)
    draw.line((tx1, ty1+6, lax, lay), fill=(241,236,224,255), width=int(6*scale))
    rax = tx1 + int(math.sin(math.radians(right_arm_angle))*arm_len)
    ray = ty1 + int(math.cos(math.radians(right_arm_angle))*arm_len)
    draw.line((tx1, ty1+6, rax, ray), fill=(241,236,224,255), width=int(6*scale))
    # legs
    leg_len = int(50*scale)
    lx = tx2 + int(math.sin(math.radians(left_leg_angle))*leg_len)
    ly = ty2 + int(math.cos(math.radians(left_leg_angle))*leg_len)
    draw.line((tx2, ty2, lx, ly), fill=(241,236,224,255), width=int(6*scale))
    rx = tx2 + int(math.sin(math.radians(right_leg_angle))*leg_len)
    ry = ty2 + int(math.cos(math.radians(right_leg_angle))*leg_len)
    draw.line((tx2, ty2, rx, ry), fill=(241,236,224,255), width=int(6*scale))


def make_gif(name, frames, duration_ms=80, loop=0):
    imgs = []
    for im in frames:
        imgs.append(im.convert('RGBA'))
    out_path = f"{OUT_DIR}/{name}.gif"
    imgs[0].save(out_path, save_all=True, append_images=imgs[1:], optimize=True, duration=duration_ms, loop=loop, disposal=2, transparency=0)
    print('Saved', out_path)


# simple animations

def gen_pushup():
    frames = []
    for i in range(40):
        t = i/39.0
        # up-down ease
        y = math.sin(t*math.pi*2)*8
        im = Image.new('RGBA', (WIDTH, HEIGHT), BG)
        d = ImageDraw.Draw(im)
        draw_frame(d, WIDTH//2, HEIGHT//2-20, 1.0, 0, 8, 20-20*math.sin(t*math.pi), -20+20*math.sin(t*math.pi), 12-6*math.sin(t*math.pi), -12+6*math.sin(t*math.pi))
        # translate
        im = im.transform(im.size, Image.AFFINE, (1,0,0,0,1,-y))
        frames.append(im)
    make_gif('push-up', frames, duration_ms=100)


def gen_squat():
    frames = []
    for i in range(48):
        t = i/47.0
        y = abs(math.sin(t*math.pi))*18
        im = Image.new('RGBA', (WIDTH, HEIGHT), BG)
        d = ImageDraw.Draw(im)
        draw_frame(d, WIDTH//2, HEIGHT//2-10, 1.0, 0, 0, -20, 20, 30, -30)
        im = im.transform(im.size, Image.AFFINE, (1,0,0,0,1,-y))
        frames.append(im)
    make_gif('squat', frames, duration_ms=100)


def gen_plank():
    frames = []
    for i in range(40):
        t = i/39.0
        y = math.sin(t*math.pi*2)*3
        torso_angle = 0
        im = Image.new('RGBA', (WIDTH, HEIGHT), BG)
        d = ImageDraw.Draw(im)
        draw_frame(d, WIDTH//2, HEIGHT//2+10, 1.0, 0, torso_angle, 80, -80, 10, -10)
        im = im.transform(im.size, Image.AFFINE, (1,0,0,0,1,-y))
        frames.append(im)
    make_gif('plank', frames, duration_ms=120)


def gen_lunge():
    frames = []
    for i in range(48):
        t = i/47.0
        shift = math.sin(t*2*math.pi)*6
        left_leg = 20 + 12*math.sin(t*2*math.pi)
        right_leg = -20 - 12*math.sin(t*2*math.pi)
        im = Image.new('RGBA', (WIDTH, HEIGHT), BG)
        d = ImageDraw.Draw(im)
        draw_frame(d, WIDTH//2+int(shift), HEIGHT//2-5, 1.0, 0, 0, -10, 10, left_leg, right_leg)
        frames.append(im)
    make_gif('lunge', frames, duration_ms=100)


def gen_burpee():
    frames = []
    for i in range(60):
        t = i/59.0
        # simulate tuck and jump
        if t < 0.4:
            y = (math.sin(t/0.4*math.pi))*10
        else:
            y = -abs(math.sin((t-0.4)/0.6*math.pi))*18
        im = Image.new('RGBA', (WIDTH, HEIGHT), BG)
        d = ImageDraw.Draw(im)
        draw_frame(d, WIDTH//2, HEIGHT//2+10, 1.0, 0, 0, -18, 18, 20, -20)
        im = im.transform(im.size, Image.AFFINE, (1,0,0,0,1,-y))
        frames.append(im)
    make_gif('burpee', frames, duration_ms=80)


def gen_mountain():
    frames = []
    for i in range(36):
        t = i/35.0
        leg_offset = 20*math.sin(t*2*math.pi)
        im = Image.new('RGBA', (WIDTH, HEIGHT), BG)
        d = ImageDraw.Draw(im)
        draw_frame(d, WIDTH//2, HEIGHT//2-10, 1.0, 0, 0, 120-30*math.sin(t*2*math.pi), -120+30*math.sin(t*2*math.pi), 30+leg_offset, -30-leg_offset)
        frames.append(im)
    make_gif('mountain-climber', frames, duration_ms=80)


def gen_jacks():
    frames = []
    for i in range(44):
        t = i/43.0
        spread = 30*math.sin(t*2*math.pi)
        arm_angle = -60 + spread*0.6
        leg_angle = 24 + spread*0.5
        im = Image.new('RGBA', (WIDTH, HEIGHT), BG)
        d = ImageDraw.Draw(im)
        draw_frame(d, WIDTH//2, HEIGHT//2-10, 1.0, 0, 0, arm_angle, -arm_angle, leg_angle, -leg_angle)
        frames.append(im)
    make_gif('jumping-jacks', frames, duration_ms=90)


if __name__ == '__main__':
    gen_pushup()
    gen_squat()
    gen_plank()
    gen_lunge()
    gen_burpee()
    gen_mountain()
    gen_jacks()
    print('All GIFs generated.')
