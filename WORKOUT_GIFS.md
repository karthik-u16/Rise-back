Workout GIFs for Rise Back

Overview

Place transparent-background animated GIFs for exercise tutorials in the repository at:

    static/workouts/

The challenge page will look for GIFs by a simple slug derived from the challenge name and display the GIF in the demo modal when present. If no GIF is found, the page falls back to the CSS-based animation demo.

Slug rules (filename format)

- Lowercase
- Remove any characters other than a-z, 0-9, space and hyphen
- Replace spaces with single hyphens
- Use the `.gif` extension

Example conversions

- "Incline Push-Up Flow" → `incline-push-up-flow.gif`
- "Bodyweight Squat Ladder" → `bodyweight-squat-ladder.gif`
- "Jog in Place" → `jog-in-place.gif`
- "Burpee Intervals" → `burpee-intervals.gif`

Recommended GIF specs

- Transparent background (PNG/GIF transparency) so the demo overlays the app UI cleanly
- Duration: the modal supports looping; target 3–8 seconds per loop
- Size: 420×360px or similar (keep width ≤ 420px) to fit modal comfortably
- Optimized for web: aim for < 500KB each where possible

How it works

1. When users click the "Visual Demo" button, the page computes a slug from the challenge name and checks for `/static/workouts/{slug}.gif`.
2. If the GIF exists (HTTP HEAD returns 200), the GIF is shown in the modal. Otherwise the CSS animation demo is used.

Previewing locally

1. Place your GIF files under `static/workouts/` following the slug naming rules.
2. Run the app locally (use your virtualenv):

```powershell
python -m flask --app app run --debug
```

3. Open the challenge page for a region, e.g. `http://127.0.0.1:5000/challenges/1`, and click "Visual Demo" on any challenge.

If you'd like, I can generate simple placeholder GIFs for the key movements (push-ups, squats, plank, lunges, burpees, mountain climbers, jumping jacks) or help convert the CSS prototypes into actual GIF files using a headless browser capture. Let me know which option you prefer.
