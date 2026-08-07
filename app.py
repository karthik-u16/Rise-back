from functools import wraps
from flask import session
from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta , datetime
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required, get_jwt_identity

load_dotenv()
import os
import random
import requests

app = Flask(__name__)
               
# Secret key: reads from environment variable in production, fallback for local dev only
app.secret_key = os.environ.get("SECRET_KEY", "riseback_dev_key_change_in_prod")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
)
csrf = CSRFProtect(app)

from flask_jwt_extended import JWTManager

app.config["JWT_SECRET_KEY"] = os.environ.get("SECRET_KEY")
jwt = JWTManager(app)

CRON_SECRET = os.environ.get("CRON_SECRET", "change-this-locally")

import firebase_admin
from firebase_admin import credentials, messaging

if os.path.exists("/etc/secrets/firebase-service-account.json"):
    # Render
    cred = credentials.Certificate("/etc/secrets/firebase-service-account.json")
else:
    # Local development
    cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)                            

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

# Production: set DATABASE_URL env var to a PostgreSQL connection string (e.g. from Render/Railway)
# Local dev:  falls back to SQLite automatically — no setup needed
_db_url = os.environ.get("DATABASE_URL", "sqlite:///riseback.db")

# SQLAlchemy 2.x dropped the legacy "postgres://" scheme — fix it transparently
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

MAX_DAILY_WATER_ML = 3000


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def migrate_legacy_schema():
    """Apply the one backwards-compatible column needed by pre-cleanup databases."""
    inspector = inspect(db.engine)
    if "water_tracker" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("water_tracker")}
    if "water_date" not in columns:
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE water_tracker ADD COLUMN water_date DATE")
            )
            connection.execute(
                text(
                    "UPDATE water_tracker SET water_date = :today WHERE water_date IS NULL"
                ),
                {"today": date.today()},
            )


REGION_CONFIG = {
    1: {
        "name": "Foundation Camp",
        "weeks": 2,
        "target_progress": 8,
        "challenges": [
            {
                "icon": "🧘",
                "name": "Breathing Reset",
                "focus": "Mobility",
                "desc": "5 minutes of calm breathwork to center your body.",
                "duration": 300,
            },
            {
                "icon": "🦵",
                "name": "Bodyweight Squat Ladder",
                "focus": "Legs",
                "desc": "Build a solid base with 3 rounds of 10 controlled squats.",
                "duration": 480,
            },
            {
                "icon": "💪",
                "name": "Incline Push-Up Flow",
                "focus": "Push",
                "desc": "Work light upper-body strength with 3 steady sets of incline push-ups.",
                "duration": 480,
            },
            {
                "icon": "🪢",
                "name": "Band Row Builder",
                "focus": "Pull",
                "desc": "Train your posture and pull strength with 15 slow rows.",
                "duration": 480,
            },
            {
                "icon": "🧱",
                "name": "Plank Hold",
                "focus": "Core",
                "desc": "Hold a strong plank for 30 seconds to stabilize your midsection.",
                "duration": 30,
            },
            {
                "icon": "🟠",
                "name": "Shoulder Tap Circuit",
                "focus": "Shoulders",
                "desc": "Build shoulder stability with 20 alternating taps.",
                "duration": 480,
            },
            {
                "icon": "🏃",
                "name": "Jog in Place",
                "focus": "Cardio",
                "desc": "Complete a real jog or sustained in-place cardio block before moving on.",
                "duration": 2700,
            },
            {
                "icon": "⚡",
                "name": "Mini Mobility Finish",
                "focus": "Cardio",
                "desc": "Finish the week with a brisk walk and light mobility flow.",
                "duration": 600,
            },
        ],
    },
    2: {
        "name": "Combat Valley",
        "weeks": 4,
        "target_progress": 12,
        "challenges": [
            {
                "icon": "💥",
                "name": "Push-Up Circuit",
                "focus": "Push",
                "desc": "Complete 3 rounds of 10 clean push-ups with good form.",
                "duration": 480,
            },
            {
                "icon": "🪢",
                "name": "Bent-Over Rows",
                "focus": "Pull",
                "desc": "Drive your back and pull strength through 20 reps.",
                "duration": 480,
            },
            {
                "icon": "🦵",
                "name": "Walking Lunges",
                "focus": "Legs",
                "desc": "Walk strong through 20 lunges to fire your lower body.",
                "duration": 480,
            },
            {
                "icon": "🟠",
                "name": "Pike Shoulder Press",
                "focus": "Shoulders",
                "desc": "Hold the pike position and press for 12 controlled reps.",
                "duration": 480,
            },
            {
                "icon": "🔥",
                "name": "Jump Rope Burst",
                "focus": "Cardio",
                "desc": "Push your pace for 2 minutes of jump rope movement.",
                "duration": 120,
            },
            {
                "icon": "💪",
                "name": "Decline Push-Up Prep",
                "focus": "Push",
                "desc": "Use a sturdy surface and train the lower chest with 8 to 12 reps.",
                "duration": 480,
            },
            {
                "icon": "🧗",
                "name": "Inverted Row Drill",
                "focus": "Pull",
                "desc": "Build pulling strength with 12 controlled bodyweight rows.",
                "duration": 480,
            },
            {
                "icon": "🚀",
                "name": "Reverse Lunge Set",
                "focus": "Legs",
                "desc": "Complete 3 rounds of 10 reverse lunges with control.",
                "duration": 480,
            },
            {
                "icon": "🏋️",
                "name": "Wall Shoulder Press",
                "focus": "Shoulders",
                "desc": "Press the bodyweight overhead with slow tempo reps.",
                "duration": 480,
            },
            {
                "icon": "⚡",
                "name": "Burpee Intervals",
                "focus": "Cardio",
                "desc": "Finish strong with 8 burpees every minute for 4 minutes.",
                "duration": 240,
            },
            {
                "icon": "🧘",
                "name": "Recovery Flow",
                "focus": "Mobility",
                "desc": "Recover with mobility and breathing after a hard training block.",
                "duration": 360,
            },
            {
                "icon": "🏃‍♂️",
                "name": "Tempo Run",
                "focus": "Cardio",
                "desc": "Run for 15 minutes at a strong pace without rushing.",
                "duration": 900,
            },
        ],
    },
    3: {
        "name": "Elite Arena",
        "weeks": 8,
        "target_progress": 16,
        "challenges": [
            {
                "icon": "🔻",
                "name": "Diamond Push-Ups",
                "focus": "Push",
                "desc": "Tighten your form with 20 diamond-style push-ups.",
                "duration": 480,
            },
            {
                "icon": "🧗",
                "name": "Chin-Ups",
                "focus": "Pull",
                "desc": "Strengthen your back with 10 challenging chin-ups.",
                "duration": 480,
            },
            {
                "icon": "🎯",
                "name": "Bulgarian Split Squats",
                "focus": "Legs",
                "desc": "Perform 16 split squats for focused leg power.",
                "duration": 480,
            },
            {
                "icon": "🟡",
                "name": "Pike Shoulder Press",
                "focus": "Shoulders",
                "desc": "Hold the pike position and press for 12 reps.",
                "duration": 480,
            },
            {
                "icon": "🏃‍♂️",
                "name": "400m Run",
                "focus": "Cardio",
                "desc": "Complete a fast 400m run or equivalent sprint set.",
                "duration": 600,
            },
            {
                "icon": "💥",
                "name": "Close-Grip Push-Up Ladder",
                "focus": "Push",
                "desc": "Move through 3 rounds of close-grip push-ups with control.",
                "duration": 480,
            },
            {
                "icon": "🪢",
                "name": "Chest-Supported Row",
                "focus": "Pull",
                "desc": "Train back strength with 12 slow rows and full range.",
                "duration": 480,
            },
            {
                "icon": "🦵",
                "name": "Step-Up Strength",
                "focus": "Legs",
                "desc": "Drive through 12 step-ups per leg for balance and power.",
                "duration": 480,
            },
            {
                "icon": "🤸",
                "name": "Handstand Hold",
                "focus": "Shoulders",
                "desc": "Hold the handstand for 20 seconds to test balance.",
                "duration": 20,
            },
            {
                "icon": "⚡",
                "name": "Sprint Intervals",
                "focus": "Cardio",
                "desc": "Complete alternating sprint and recovery sets.",
                "duration": 600,
            },
            {
                "icon": "🧘",
                "name": "Flow Reset",
                "focus": "Mobility",
                "desc": "Use this reset block to move better and stay fresh.",
                "duration": 360,
            },
            {
                "icon": "💨",
                "name": "EMOM Burpees",
                "focus": "Cardio",
                "desc": "Push your endurance with 10 burpees each minute.",
                "duration": 600,
            },
            {
                "icon": "🔺",
                "name": "Wide Push-Up Set",
                "focus": "Push",
                "desc": "Train the chest and shoulders with wide push-ups.",
                "duration": 480,
            },
            {
                "icon": "🪝",
                "name": "Neutral-Grip Pull",
                "focus": "Pull",
                "desc": "Hold your back tight and pull with control.",
                "duration": 480,
            },
            {
                "icon": "🏋️",
                "name": "Goblet Squat Press",
                "focus": "Legs",
                "desc": "Combine squatting and pressing for power and control.",
                "duration": 480,
            },
            {
                "icon": "🧱",
                "name": "Side Plank Hold",
                "focus": "Core",
                "desc": "Hold each side for 30 seconds and build trunk stiffness.",
                "duration": 30,
            },
        ],
    },
    4: {
        "name": "Legend Citadel",
        "weeks": 16,
        "target_progress": 20,
        "challenges": [
            {
                "icon": "⬇️",
                "name": "Decline Push-Ups",
                "focus": "Push",
                "desc": "Challenge your upper chest with 20 decline push-ups.",
                "duration": 480,
            },
            {
                "icon": "↕️",
                "name": "Inverted Rows",
                "focus": "Pull",
                "desc": "Build pulling strength with 15 bodyweight rows.",
                "duration": 480,
            },
            {
                "icon": "🚀",
                "name": "Squat Jumps",
                "focus": "Legs",
                "desc": "Explode through 15 squat jumps for power.",
                "duration": 480,
            },
            {
                "icon": "🏋️",
                "name": "Shoulder Presses",
                "focus": "Shoulders",
                "desc": "Press through 20 reps with controlled shoulder strength.",
                "duration": 480,
            },
            {
                "icon": "💨",
                "name": "EMOM Burpees",
                "focus": "Cardio",
                "desc": "Push your endurance with 10 burpees each minute.",
                "duration": 600,
            },
            {
                "icon": "🔥",
                "name": "One-Arm Push-Up Prep",
                "focus": "Push",
                "desc": "Build elite pushing strength with progression work.",
                "duration": 480,
            },
            {
                "icon": "💪",
                "name": "Weighted Pull-Ups",
                "focus": "Pull",
                "desc": "Add resistance to 12 strong pull-ups.",
                "duration": 480,
            },
            {
                "icon": "🦵",
                "name": "Pistol Squats",
                "focus": "Legs",
                "desc": "Master single-leg control with 10 pistol squat reps.",
                "duration": 480,
            },
            {
                "icon": "🤸",
                "name": "Handstand Hold",
                "focus": "Shoulders",
                "desc": "Hold the handstand for 20 seconds to test balance.",
                "duration": 20,
            },
            {
                "icon": "⚡",
                "name": "Sprint Intervals",
                "focus": "Cardio",
                "desc": "Complete alternating sprint and recovery sets.",
                "duration": 600,
            },
            {
                "icon": "🥋",
                "name": "Tempo Push-Up Ladder",
                "focus": "Push",
                "desc": "Push slowly and deliberately to sharpen form and strength.",
                "duration": 480,
            },
            {
                "icon": "🪝",
                "name": "Weighted Row Set",
                "focus": "Pull",
                "desc": "Use resistance and drive the elbows back under tension.",
                "duration": 480,
            },
            {
                "icon": "🦿",
                "name": "Single-Leg Romanian Deadlift",
                "focus": "Legs",
                "desc": "Train balance and posterior chain with clean single-leg reps.",
                "duration": 480,
            },
            {
                "icon": "🛡",
                "name": "Overhead Stability Hold",
                "focus": "Shoulders",
                "desc": "Hold a stable overhead position and build control.",
                "duration": 480,
            },
            {
                "icon": "🏃",
                "name": "Hill Sprints",
                "focus": "Cardio",
                "desc": "Use short uphill sprints to build power and durability.",
                "duration": 600,
            },
            {
                "icon": "🧘",
                "name": "Deep Recovery Reset",
                "focus": "Mobility",
                "desc": "Use a focused mobility block to stay healthy through hard training.",
                "duration": 360,
            },
            {
                "icon": "💥",
                "name": "Hybrid Push Circuit",
                "focus": "Push",
                "desc": "Combine push-ups and dips for a demanding upper-body finisher.",
                "duration": 480,
            },
            {
                "icon": "🪢",
                "name": "Pull-Up Progression",
                "focus": "Pull",
                "desc": "Use assisted work and strengthen the full pull motion.",
                "duration": 480,
            },
            {
                "icon": "🦵",
                "name": "Jump Squat Finish",
                "focus": "Legs",
                "desc": "Finish the week with explosive squat jumps and good form.",
                "duration": 480,
            },
            {
                "icon": "⚔",
                "name": "Warrior Cardio Circuit",
                "focus": "Cardio",
                "desc": "Finish with a serious conditioning circuit that tests your grit.",
                "duration": 600,
            },
        ],
    },
    5: {
        "name": "Legacy Throne",
        "weeks": 32,
        "target_progress": 24,
        "challenges": [
            {
                "icon": "👑",
                "name": "One-Arm Push-Up Prep",
                "focus": "Push",
                "desc": "Build elite pushing strength with progression work.",
                "duration": 480,
            },
            {
                "icon": "🏆",
                "name": "Weighted Pull-Ups",
                "focus": "Pull",
                "desc": "Add resistance to 12 strong pull-ups.",
                "duration": 480,
            },
            {
                "icon": "🦿",
                "name": "Pistol Squats",
                "focus": "Legs",
                "desc": "Master single-leg control with 10 pistol squat reps.",
                "duration": 480,
            },
            {
                "icon": "🤸",
                "name": "Handstand Hold",
                "focus": "Shoulders",
                "desc": "Hold the handstand for 20 seconds to test balance.",
                "duration": 20,
            },
            {
                "icon": "⚡",
                "name": "Sprint Intervals",
                "focus": "Cardio",
                "desc": "Complete alternating sprint and recovery sets.",
                "duration": 600,
            },
            {
                "icon": "🔥",
                "name": "Explosive Push-Up Ladder",
                "focus": "Push",
                "desc": "Move through strong explosive push-up reps with clean form.",
                "duration": 480,
            },
            {
                "icon": "🪢",
                "name": "Weighted Row Mastery",
                "focus": "Pull",
                "desc": "Drive the chest up and pull through a full range of motion.",
                "duration": 480,
            },
            {
                "icon": "🦵",
                "name": "Split Squat Mastery",
                "focus": "Legs",
                "desc": "Develop controlled power in single-leg squatting.",
                "duration": 480,
            },
            {
                "icon": "🛡",
                "name": "Overhead Press Endurance",
                "focus": "Shoulders",
                "desc": "Hold a strong overhead position through a demanding set.",
                "duration": 480,
            },
            {
                "icon": "🏃",
                "name": "Tempo Hill Run",
                "focus": "Cardio",
                "desc": "Train your engine with a controlled hill run session.",
                "duration": 600,
            },
            {
                "icon": "🧘",
                "name": "Longevity Mobility Flow",
                "focus": "Mobility",
                "desc": "Use this flow to maintain movement quality and durability.",
                "duration": 360,
            },
            {
                "icon": "💥",
                "name": "Advanced Push Circuit",
                "focus": "Push",
                "desc": "Stack challenging push variations into a serious upper-body block.",
                "duration": 480,
            },
            {
                "icon": "🪝",
                "name": "Pull-Up Strength Test",
                "focus": "Pull",
                "desc": "Push your pull-up volume and strength with purpose.",
                "duration": 480,
            },
            {
                "icon": "🦿",
                "name": "Single-Leg Romanian Deadlift",
                "focus": "Legs",
                "desc": "Train balance and posterior chain with clean single-leg reps.",
                "duration": 480,
            },
            {
                "icon": "♻️",
                "name": "Shoulder Stability Circuit",
                "focus": "Shoulders",
                "desc": "Build resilience through deliberate shoulder-strength work.",
                "duration": 480,
            },
            {
                "icon": "⚔",
                "name": "Warrior Conditioning",
                "focus": "Cardio",
                "desc": "Finish the week with a stamina challenge that tests grit.",
                "duration": 600,
            },
            {
                "icon": "🔥",
                "name": "Elite Push Finisher",
                "focus": "Push",
                "desc": "Use a tough push finisher to close the week strong.",
                "duration": 480,
            },
            {
                "icon": "🪢",
                "name": "Pull Strength Builder",
                "focus": "Pull",
                "desc": "Stack rows and pull-ups into a back-focused session.",
                "duration": 480,
            },
            {
                "icon": "🦵",
                "name": "Power Squat Circuit",
                "focus": "Legs",
                "desc": "Combine squat strength with controlled explosive reps.",
                "duration": 480,
            },
            {
                "icon": "🏃",
                "name": "Endurance Builder",
                "focus": "Cardio",
                "desc": "Train your breath, pacing, and durability for the long haul.",
                "duration": 600,
            },
            {
                "icon": "🧘",
                "name": "Recovery Reset",
                "focus": "Mobility",
                "desc": "Use this block to recover and keep your body moving well.",
                "duration": 360,
            },
            {
                "icon": "⚔",
                "name": "Final Ascension Circuit",
                "focus": "Cardio",
                "desc": "Test your endurance and discipline one more time.",
                "duration": 600,
            },
            {
                "icon": "💪",
                "name": "Legendary Push Day",
                "focus": "Push",
                "desc": "Finish the long cycle with a deliberate push session.",
                "duration": 480,
            },
            {
                "icon": "🪢",
                "name": "Legendary Pull Day",
                "focus": "Pull",
                "desc": "Push your back strength to the next level.",
                "duration": 480,
            },
        ],
    },
}


def get_region_challenges(level):
    region = REGION_CONFIG.get(level, REGION_CONFIG[1])
    return region["challenges"]


def get_region_target(level):
    region = REGION_CONFIG.get(level, REGION_CONFIG[1])
    return region["target_progress"]


def get_region_weeks(level):
    region = REGION_CONFIG.get(level, REGION_CONFIG[1])
    return region["weeks"]


def award_region_progress(progress, amount=1):
    if not progress:
        return progress

    progress.completed += amount
    target = get_region_target(progress.level)

    if progress.completed >= target:
        progress.completed = 0
        progress.level = min(5, progress.level + 1)

    return progress


REGIONS = {
    1: {"name": "🏕 Foundation Camp", "next": "⚔ Combat Valley"},
    2: {"name": "⚔ Combat Valley", "next": "🏛 Elite Arena"},
    3: {"name": "🏛 Elite Arena", "next": "👑 Legend Citadel"},
    4: {"name": "👑 Legend Citadel", "next": "🔥 Legacy Throne"},
    5: {"name": "🔥 Legacy Throne", "next": "MAX REGION"},
}

BOSSES = {
    1: {
        "name": "Foundation Guardian",
        "tasks": ["50 Squats", "25 Pushups", "30s Plank"],
        "reward": 20,
    },
    2: {
        "name": "Combat Warlord",
        "tasks": ["75 Squats", "50 Pushups", "60s Plank"],
        "reward": 30,
    },
    3: {
        "name": "Elite Champion",
        "tasks": ["100 Squats", "75 Pushups", "90s Plank"],
        "reward": 40,
    },
    4: {
        "name": "Citadel King",
        "tasks": ["120 Squats", "100 Pushups", "120s Plank"],
        "reward": 50,
    },
    5: {
        "name": "Legacy Throne Guardian",
        "tasks": ["150 Squats", "125 Pushups", "180s Plank"],
        "reward": 75,
    },
}

BOSS_IMAGES = {
    1: "bosses/foundation_guardian.png",
    2: "bosses/combat_warlord.png",
    3: "bosses/arena_destroyer.png",
    4: "bosses/legend_emperor.png",
    5: "bosses/legacy_throne_guardian.png",
}

REWARDS = {
    1: {
        "name": "💪 Confidence Core",
        "description": "Believe in your ability to improve.",
    },
    2: {
        "name": "⚡ Discipline Spark",
        "description": "Action before motivation You became something no one has else.",
    },
    3: {
        "name": "🦁 Warrior Mindset",
        "description": "Consistency creates strength your mindset became has an arrow.",
    },
    4: {"name": "🛡 Man of Steel Mindset", "description": "Resilience under pressure."},
    5: {
        "name": "🔥 Phoenix Man",
        "description": "You rose from setbacks and rebuilt yourself stronger than before.",
    },
}

QUOTES = [
    "Success starts with self-discipline.",
    "The body achieves what the mind believes.",
    "Small steps every day.",
    "Consistency beats motivation.",
    "Rise stronger than yesterday.",
]

WORKOUT_SCHEDULE = {
    0: {
        "day": "Monday",
        "focus": "Push Day",
        "icon": "💥",
        "exercises": [
            "Push Ups",
            "Bench Press",
            "Shoulder Press",
            "Tricep Dips",
            "Incline Press",
        ],
    },
    1: {
        "day": "Tuesday",
        "focus": "Pull Day",
        "icon": "🪢",
        "exercises": [
            "Pull Ups",
            "Bent-Over Rows",
            "Bicep Curls",
            "Lat Pulldown",
            "Face Pulls",
        ],
    },
    2: {
        "day": "Wednesday",
        "focus": "Leg Day",
        "icon": "🦵",
        "exercises": [
            "Squats",
            "Lunges",
            "Leg Press",
            "Calf Raises",
            "Romanian Deadlift",
        ],
    },
    3: {
        "day": "Thursday",
        "focus": "Core & Cardio",
        "icon": "🔥",
        "exercises": ["Plank", "Burpees", "Mountain Climbers", "Running", "Jump Rope"],
    },
    4: {
        "day": "Friday",
        "focus": "Full Body Strength",
        "icon": "⚔",
        "exercises": ["Deadlifts", "Push Ups", "Squats", "Rows", "Overhead Press"],
    },
    5: {
        "day": "Saturday",
        "focus": "Active Recovery",
        "icon": "🧘",
        "exercises": ["Stretching", "Yoga Flow", "Light Walk", "Foam Rolling"],
    },
    6: {
        "day": "Sunday",
        "focus": "Rest Day",
        "icon": "🛌",
        "exercises": ["Full Rest", "Light Stretching", "Walk"],
    },
}

CATEGORY_CALORIES_PER_MIN = {
    "Push Day": 7,
    "Pull Day": 7,
    "Leg Day": 8,
    "Core & Cardio": 10,
    "Full Body Strength": 9,
    "Active Recovery": 4,
    "Rest Day": 2,
    "General": 6,
}

class DeviceToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    fcm_token = db.Column(db.String(300), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)

    password = db.Column(db.String(200), nullable=False)


class UserProgress(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True)

    level = db.Column(db.Integer, default=1)

    xp = db.Column(db.Integer, default=0)

    streak = db.Column(db.Integer, default=1)

    completed = db.Column(db.Integer, default=0)


class UserProfile(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True)

    age = db.Column(db.Integer)

    gender = db.Column(db.String(20))

    height = db.Column(db.Float)

    weight = db.Column(db.Float)

    target_weight = db.Column(db.Float)

    fitness_goal = db.Column(db.String(50))

    activity_level = db.Column(db.String(50))


class WeightLog(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    weight = db.Column(db.Float)

    log_date = db.Column(db.Date, nullable=False, default=date.today, index=True)


class WorkoutLog(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )

    workout_date = db.Column(db.Date, nullable=False)

    exercise_name = db.Column(db.String(150), nullable=False)

    category = db.Column(db.String(50))

    sets = db.Column(db.Integer)

    reps = db.Column(db.Integer)

    weight_kg = db.Column(db.Float)

    duration_minutes = db.Column(db.Integer)

    calories_burned = db.Column(db.Integer)

    notes = db.Column(db.String(255))


class WaterTracker(db.Model):

    __table_args__ = (db.UniqueConstraint("user_id", "water_date"),)

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )

    water_ml = db.Column(db.Integer, default=0)

    water_date = db.Column(db.Date, nullable=False, default=date.today, index=True)


class DailyMission(db.Model):

    __table_args__ = (db.UniqueConstraint("user_id", "mission_name", "mission_date"),)

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer)

    mission_name = db.Column(db.String(200))

    mission_date = db.Column(db.Date)

    completed = db.Column(db.Boolean, default=False)


class UserStreak(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, unique=True)

    streak_count = db.Column(db.Integer, default=0)

    last_active = db.Column(db.Date)


class BossBattle(db.Model):

    __table_args__ = (db.UniqueConstraint("user_id", "boss_level"),)

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)

    boss_level = db.Column(db.Integer, nullable=False)

    defeated = db.Column(db.Boolean, default=True)


class RewardChest(db.Model):

    __table_args__ = (db.UniqueConstraint("user_id", "reward_name"),)

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)

    reward_name = db.Column(db.String(100), nullable=False)

    reward_description = db.Column(db.String(255))


class ShadowBoss(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer)

    defeated = db.Column(db.Boolean, default=False)
    
class Achievement(db.Model):

    __table_args__ = (db.UniqueConstraint("user_id", "achievement_name"),)

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)

    achievement_name = db.Column(db.String(100), nullable=False)
    
def send_push_to_user(user_id, title, body):
    tokens = DeviceToken.query.filter_by(user_id=user_id).all()

    print(f"\n===== USER {user_id} =====")
    print(f"Found {len(tokens)} device token(s)")

    results = []

    for device in tokens:
        print(f"Sending to token: {device.fcm_token[:25]}...")

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=device.fcm_token,
        )

        try:
            response = messaging.send(message)

            print("✅ Success:", response)

            results.append({
                "token": device.fcm_token[:20] + "...",
                "success": True,
                "id": response
            })

        except Exception as e:

            print("❌ Firebase Error:", e)

            results.append({
                "token": device.fcm_token[:20] + "...",
                "success": False,
                "error": str(e)
            })

    return results


def get_badges(level):

    badges = [
        {"name": "MORTAL", "level": 1},
        {"name": "WARRIOR", "level": 2},
        {"name": "DEMIGOD", "level": 3},
        {"name": "GOD", "level": 4},
        {"name": "CELESTIAL", "level": 5},
    ]

    for badge in badges:
        badge["unlocked"] = level >= badge["level"]

    return badges

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.1-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

SELF_HARM_PHRASES = [
    "hurt myself",
    "self harm",
    "suicide",
    "end my life",
    "kill myself",
    "want to die",
]


def check_self_harm(user_message):
    lowered = user_message.lower()
    return any(phrase in lowered for phrase in SELF_HARM_PHRASES)


def build_mentor_system_prompt(context):
    weight_line = f"{context['weight']}kg" if context['weight'] else "not set"
    target_line = f"{context['target_weight']}kg" if context['target_weight'] else "not set"
    calorie_line = f"{context['calorie_target']} kcal/day maintenance" if context['calorie_target'] else "not calculated yet (profile incomplete)"

    return f"""You are a fitness mentor inside a gamified fitness app called Rise Back.
The app has a warrior/ascension theme — your personality is intense, direct, and encouraging, like a mentor training a warrior.

Current player state (this is real, accurate data — use exact numbers when asked, never guess or make up a number):
- Region: {context['region_name']} (Level {context['level']})
- XP: {context['xp']} / 30 (per-region cap)
- Streak: {context['streak']} days
- Water today: {context['water_ml']}ml / {MAX_DAILY_WATER_ML}ml
- Current weight: {weight_line}
- Target weight: {target_line}
- Estimated maintenance calories: {calorie_line}
- Fitness plan: {context['goal_plan']}
- Boss available: {context['boss_available']}
- Today's daily missions completed: {context['challenge_progress']}%

RULES, IN ORDER OF PRIORITY:
1. Always answer the player's actual question directly and accurately first, using the real numbers above — never invent or estimate a stat that's given here.
2. If a stat is "not set" or "not calculated yet", tell them that honestly and suggest completing their profile — don't make up a placeholder number.
3. Only after directly answering, add warrior-themed encouragement or tie it back to training — persona is a garnish, not a replacement for the answer.
4. You can discuss ANY topic they bring up. Never refuse or deflect a genuine question.
5. Keep the whole reply short: 2-4 sentences, mobile-friendly.
6. Never give specific medical diagnoses, injury treatment, or extreme diet/dosage advice — for those, tell them to see a doctor or professional.
"""


def get_gemini_mentor_reply(user_message, context, history):
    system_prompt = build_mentor_system_prompt(context)

    contents = []
    for entry in history[-6:]:
        role = "user" if entry.get("sender") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": entry.get("text", "")}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
    }

    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=12)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        return None
    except requests.exceptions.RequestException:
        return None


def get_ai_message(
    streak,
    evolution,
    boss_available,
    region_name,
    xp_percent,
    water_ml=None,
    water_limit_reached=False,
    challenge_progress=None,
    goal_plan=None,
):

    if boss_available:
        return (
            f"⚔ Warrior, the guardian of {region_name} "
            "has awakened. Victory is the only path forward."
        )

    if challenge_progress is not None and challenge_progress < 100:
        return (
            "🎯 Your daily mission is still active. "
            "Finish the challenge before tonight and own it."
        )

    if streak >= 30:
        return "🔥 Thirty days of discipline. Most people quit. You didn't."

    if streak >= 7:
        return "💪 Consistency is becoming your identity."

    if xp_percent >= 90:
        return "⚡ One final push remains before evolution."

    if evolution == "💪 WARRIOR":
        return "A warrior is not born strong. He becomes strong through repetition."

    if goal_plan == "Fat Loss Program":
        return "🥗 Stay sharp with clean choices. Your body is adapting faster than you think."

    if goal_plan == "Muscle Gain Program":
        return "🍗 Fuel hard, recover harder. Every meal matters for strength."

    return "Every strong body starts as an unfinished one. Keep building."

def get_users_needing_reminder():
    today = date.today()
    all_users = User.query.all()
    needs_reminder = []

    print("========== REMINDER CHECK ==========")

    for user in all_users:
        completed_count = DailyMission.query.filter_by(
            user_id=user.id,
            mission_date=today,
            completed=True
        ).count()

        print(
            f"User {user.id} ({user.username}) completed {completed_count} missions today"
        )

        if completed_count < 3:
            print(" -> Reminder will be sent")
            needs_reminder.append(user.id)
        else:
            print(" -> No reminder")

    print("Users needing reminder:", needs_reminder)
    print("===================================")

    return needs_reminder

def get_activity_factor(activity_level):
    return {
        "Sedentary": 1.2,
        "Light": 1.375,
        "Moderate": 1.55,
        "Active": 1.725,
        "Very Active": 1.9,
    }.get(activity_level, 1.2)


def get_calorie_mission(profile):
    if not profile or not all(
        (profile.gender, profile.weight, profile.height, profile.age)
    ):
        return None

    bmr = 10 * profile.weight + 6.25 * profile.height - 5 * profile.age
    bmr += 5 if profile.gender == "Male" else -161
    maintenance = round(bmr * get_activity_factor(profile.activity_level))
    bmi = profile.weight / ((profile.height / 100) ** 2)

    if 25 <= bmi < 30:
        return f"Stay under {maintenance - 500} kcal"
    if bmi < 18.5:
        return f"Reach {maintenance + 300} kcal"
    return f"Stay near {maintenance} kcal"


def get_evolution_label(level):
    if level >= 5:
        return "✨ CELESTIAL"
    if level >= 4:
        return "👑 GOD"
    if level >= 3:
        return "🔥 DEMIGOD"
    if level >= 2:
        return "⚔ WARRIOR"
    return "⚫ MORTAL"


def get_mentor_response(
    user_message,
    streak,
    evolution,
    boss_available,
    region_name,
    xp_percent,
    water_ml,
    water_limit_reached,
    goal_plan,
    challenge_progress,
):
    text = user_message.lower().strip()

    if any(
        phrase in text
        for phrase in ["hurt myself", "self harm", "suicide", "end my life"]
    ):
        return (
            "I'm really sorry you're carrying this. Please pause the workout and contact local "
            "emergency services or a trusted person who can stay with you now. You deserve human support."
        )

    # Quick emotional checks
    if "insecure" in text:
        return (
            "Every strong physique began as an unfinished one. "
            "Do not judge your beginning against someone else's peak."
        )

    # Greetings quick-reply (include common typos like 'hy')
    greetings = [
        "hi",
        "hy",
        "hello",
        "hey",
        "hiya",
        "yo",
        "good morning",
        "good afternoon",
        "good evening",
    ]
    if any(text == g or text.startswith(g + " ") for g in greetings):
        return "Hi — how could I help you?"

    if not text:
        return get_ai_message(
            streak,
            evolution,
            boss_available,
            region_name,
            xp_percent,
            water_ml=water_ml,
            water_limit_reached=water_limit_reached,
            challenge_progress=challenge_progress,
            goal_plan=goal_plan,
        )

    if any(word in text for word in ["water", "hydrate", "hydration"]):
        if water_limit_reached:
            return (
                "💧 You hit the limit for today. "
                "Keep that discipline and rest easy knowing hydration is handled."
            )
        return (
            "💧 Keep drinking. Every 250ml counts toward your recovery and energy. "
            "Aim for the next goal and stay consistent."
        )

    if any(word in text for word in ["meal", "eat", "food", "nutrition", "diet"]):
        if goal_plan == "Fat Loss Program":
            return (
                "🥗 Stick to lean proteins, veggies, and smart portions. "
                "Your fuel should help you stay strong without extra calories."
            )
        if goal_plan == "Muscle Gain Program":
            return (
                "🍗 Choose calorie-dense quality foods and recover with protein. "
                "This is how muscle builds after the grind."
            )
        return (
            "🍎 Keep your meals balanced and consistent. "
            "Nutrition is the silent partner to every workout."
        )

    if any(
        word in text for word in ["boss", "battle", "challenge", "guardian", "region"]
    ):
        if boss_available:
            return (
                f"⚔ Your region is cleared and {region_name}'s boss is waiting. "
                "Step into the arena and claim your reward."
            )
        return f"👊 Focus on today's mission first. The boss becomes real when the path is complete."

    if any(
        word in text
        for word in ["progress", "xp", "streak", "weight", "goal", "lost", "gain"]
    ):
        return (
            "📈 Progress is a collection of small wins. "   
            "Keep stacking them with consistency and the results will follow."
        )

    if any(
        word in text for word in ["tired", "weak", "give up", "can't", "cant", "fail"]
    ):
        return (
            "🛡 Every strong body has a tired day. Rest if you need it, then return with focus. "
            "You are stronger than the urge to quit."
        )

    if any(word in text for word in ["help", "advice", "what", "how", "when", "why"]):
        return get_ai_message(
            streak,
            evolution,
            boss_available,
            region_name,
            xp_percent,
            water_ml=water_ml,
            water_limit_reached=water_limit_reached,
            challenge_progress=challenge_progress,
            goal_plan=goal_plan,
        )

    return (
        "⚡ I hear you. Stay locked in with the mission ahead and keep moving forward. "
        "Small actions add up to legendary change."
    )


@app.route("/")
def home():

    return render_template("index.html")


@app.route("/start")
def start():

    if "user" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            return "Username already exists"

        new_user = User(username=username, password=generate_password_hash(password))

        db.session.add(new_user)
        db.session.commit()

        progress = UserProgress(user_id=new_user.id)

        db.session.add(progress)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            session["user"] = user.id

            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid Username or Password")

    return render_template("login.html")

@app.route("/api/register-device", methods=["POST"])
@jwt_required()
@csrf.exempt
def register_device():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    token = data.get("fcm_token")

    if not token:
        return jsonify({"error": "Missing fcm_token"}), 400

    existing = DeviceToken.query.filter_by(fcm_token=token).first()
    if existing:
        existing.user_id = user_id
    else:
        db.session.add(DeviceToken(user_id=user_id, fcm_token=token))

    db.session.commit()
    return jsonify({"success": True})

@app.route("/api/test-push", methods=["POST"])
@jwt_required()
@csrf.exempt
def test_push():
    user_id = int(get_jwt_identity())
    results = send_push_to_user(user_id, "Rise Back", "This is a real test push from your Flask backend!")
    return jsonify({"results": results})

@app.route("/api/login", methods=["POST"])
@csrf.exempt
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        token = create_access_token(identity=str(user.id))
        return jsonify({"token": token, "user_id": user.id, "username": user.username})

    return jsonify({"error": "Invalid username or password"}), 401

@app.route("/api/dashboard", methods=["GET"])
@jwt_required()
def api_dashboard():
    user_id = int(get_jwt_identity())

    progress = UserProgress.query.filter_by(user_id=user_id).first()
    if not progress:
        return jsonify({"error": "No progress found"}), 404

    region = REGIONS.get(progress.level, {})
    badges = get_badges(progress.level)
    evolution = get_evolution_label(progress.level)

    return jsonify({
        "level": progress.level,
        "xp": progress.xp,
        "region_name": region.get("name", "Unknown"),
        "evolution": evolution,
        "badges": badges,
    })
    
@app.route("/api/send-reminders", methods=["POST"])
@csrf.exempt
def send_reminders():
    provided_secret = request.headers.get("X-Cron-Secret")
    if provided_secret != CRON_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    user_ids = get_users_needing_reminder()
    sent = 0

    for user_id in user_ids:
        results = send_push_to_user(
            user_id,
            "Rise Back",
            "You haven't finished today's missions yet — don't break your streak, warrior."
        )
        if any(r["success"] for r in results):
            sent += 1

    return jsonify({"users_checked": len(user_ids), "notifications_sent": sent})

@app.route("/api/workouts", methods=["GET"])
@jwt_required()
def api_workouts_get():
    user_id = int(get_jwt_identity())
    today = date.today()
    weekday = today.weekday()
    todays_plan = WORKOUT_SCHEDULE[weekday]

    start_of_week = today - timedelta(days=weekday)
    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]

    logs_this_week = WorkoutLog.query.filter(
        WorkoutLog.user_id == user_id,
        WorkoutLog.workout_date >= start_of_week,
        WorkoutLog.workout_date <= week_dates[-1],
    ).all()

    logged_dates = {log.workout_date for log in logs_this_week}

    total_logged = WorkoutLog.query.filter_by(user_id=user_id).count()
    total_calories_week = sum(l.calories_burned or 0 for l in logs_this_week)
    total_minutes_week = sum(l.duration_minutes or 0 for l in logs_this_week)

    recent_logs = (
        WorkoutLog.query.filter_by(user_id=user_id)
        .order_by(WorkoutLog.id.desc())
        .limit(10)
        .all()
    )

    week_strip = []
    for i, d in enumerate(week_dates):
        week_strip.append({
            "label": WORKOUT_SCHEDULE[i]["day"][:3],
            "date": d.isoformat(),
            "icon": WORKOUT_SCHEDULE[i]["icon"],
            "focus": WORKOUT_SCHEDULE[i]["focus"],
            "is_today": d == today,
            "logged": d in logged_dates,
            "is_future": d > today,
        })

    recent_logs_json = [{
        "id": log.id,
        "exercise_name": log.exercise_name,
        "category": log.category,
        "sets": log.sets,
        "reps": log.reps,
        "weight_kg": log.weight_kg,
        "duration_minutes": log.duration_minutes,
        "calories_burned": log.calories_burned,
        "notes": log.notes,
        "workout_date": log.workout_date.isoformat(),
    } for log in recent_logs]

    return jsonify({
        "todays_plan": todays_plan,
        "week_strip": week_strip,
        "recent_logs": recent_logs_json,
        "total_logged": total_logged,
        "total_calories_week": total_calories_week,
        "total_minutes_week": total_minutes_week,
        "logs_this_week_count": len(logs_this_week),
    })


@app.route("/api/workouts", methods=["POST"])
@jwt_required()
@csrf.exempt
def api_workouts_post():
    user_id = int(get_jwt_identity())
    today = date.today()
    weekday = today.weekday()
    todays_plan = WORKOUT_SCHEDULE[weekday]

    data = request.get_json(silent=True) or {}
    exercise_name = (data.get("exercise_name") or "").strip()
    sets = data.get("sets")
    reps = data.get("reps")
    weight_kg = data.get("weight_kg")
    duration = data.get("duration_minutes")
    notes = (data.get("notes") or "").strip()

    if not exercise_name:
        return jsonify({"error": "exercise_name is required"}), 400

    duration_val = int(duration) if duration else 0
    cal_rate = CATEGORY_CALORIES_PER_MIN.get(todays_plan["focus"], 6)
    calories = round(duration_val * cal_rate) if duration_val else None

    log = WorkoutLog(
        user_id=user_id,
        workout_date=today,
        exercise_name=exercise_name,
        category=todays_plan["focus"],
        sets=int(sets) if sets else None,
        reps=int(reps) if reps else None,
        weight_kg=float(weight_kg) if weight_kg else None,
        duration_minutes=duration_val if duration_val else None,
        calories_burned=calories,
        notes=notes or None,
    )
    db.session.add(log)

    logs_today_count = WorkoutLog.query.filter_by(user_id=user_id, workout_date=today).count()
    progress = UserProgress.query.filter_by(user_id=user_id).first()

    if progress and logs_today_count < 3:
        progress.xp += 5
        award_region_progress(progress, 1)

    first_workout = Achievement.query.filter_by(user_id=user_id, achievement_name="Iron Will").first()
    new_achievement = None
    if not first_workout:
        db.session.add(Achievement(user_id=user_id, achievement_name="Iron Will"))
        new_achievement = {"title": "Iron Will", "description": "Logged your first workout"}

    db.session.commit()

    return jsonify({"success": True, "new_achievement": new_achievement})

@app.route("/api/challenges/<int:level>", methods=["GET"])
@jwt_required()
def api_challenges(level):
    user_id = int(get_jwt_identity())
    progress = UserProgress.query.filter_by(user_id=user_id).first()

    if not progress or level > progress.level:
        return jsonify({"error": "Region locked"}), 403

    data = get_region_challenges(level)
    region = REGION_CONFIG.get(level, REGION_CONFIG[1])

    return jsonify({
        "challenges": data,
        "level": level,
        "region_name": region["name"],
        "weeks": region["weeks"],
        "target_progress": region["target_progress"],
    })


@app.route("/api/complete/<int:level>", methods=["POST"])
@jwt_required()
@csrf.exempt
def api_complete(level):
    user_id = int(get_jwt_identity())
    progress = UserProgress.query.filter_by(user_id=user_id).first()

    if not progress or level != progress.level:
        return jsonify({"error": "Level mismatch"}), 403

    today = date.today()
    new_achievements = []

    streak = UserStreak.query.filter_by(user_id=user_id).first()
    if not streak:
        streak = UserStreak(user_id=user_id, streak_count=1, last_active=today)
        db.session.add(streak)
    else:
        days_gap = (today - streak.last_active).days
        if days_gap == 1:
            streak.streak_count += 1
        elif days_gap > 1:
            streak.streak_count = 1
        streak.last_active = today

    challenge_reward = DailyMission.query.filter_by(
        user_id=user_id, mission_name="Challenge XP Reward", mission_date=today
    ).first()
    if not challenge_reward:
        progress.xp += 3
        award_region_progress(progress, 1)
        db.session.add(DailyMission(
            user_id=user_id, mission_name="Challenge XP Reward",
            mission_date=today, completed=True,
        ))

    first_blood = Achievement.query.filter_by(user_id=user_id, achievement_name="First Blood").first()
    if not first_blood:
        db.session.add(Achievement(user_id=user_id, achievement_name="First Blood"))
        new_achievements.append({"title": "First Blood", "description": "Completed your first challenge"})

    if streak.streak_count >= 7:
        iron = Achievement.query.filter_by(user_id=user_id, achievement_name="Iron Streak").first()
        if not iron:
            db.session.add(Achievement(user_id=user_id, achievement_name="Iron Streak"))
            new_achievements.append({"title": "Iron Streak", "description": "7-day streak reached"})

    existing = DailyMission.query.filter_by(
        user_id=user_id, mission_name="Complete Today's Challenge", mission_date=today
    ).first()
    if not existing:
        progress.xp += 20
        db.session.add(DailyMission(
            user_id=user_id, mission_name="Complete Today's Challenge",
            mission_date=today, completed=True,
        ))

    db.session.commit()

    return jsonify({
        "success": True,
        "streak_count": streak.streak_count,
        "xp": progress.xp,
        "new_achievements": new_achievements,
    })
    
@app.route("/api/mentor-chat", methods=["POST"])
@jwt_required()
@csrf.exempt
def api_mentor_chat():
    user_id = int(get_jwt_identity())
    progress = UserProgress.query.filter_by(user_id=user_id).first()

    if not progress:
        return jsonify({"response": "Set up your warrior profile first, then your mentor will be ready.", "history": []})

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()[:500]
    client_history = data.get("history", [])

    water = WaterTracker.query.filter_by(user_id=user_id, water_date=date.today()).first()
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    streak = UserStreak.query.filter_by(user_id=user_id).first()

    if not streak:
        streak = UserStreak(user_id=user_id, streak_count=0)

    goal_plan = None
    if profile and profile.height and profile.weight:
        height_m = profile.height / 100
        bmi = round(profile.weight / (height_m * height_m), 1)
        if bmi < 18.5:
            goal_plan = "Muscle Gain Program"
        elif bmi < 25:
            goal_plan = "Maintenance Program"
        elif bmi < 30:
            goal_plan = "Fat Loss Program"
        else:
            goal_plan = "Aggressive Fat Loss Program"

    today = date.today()
    water_done = DailyMission.query.filter_by(user_id=user_id, mission_name="Drink 2500ml Water", mission_date=today).first()

    activity_factor = get_activity_factor(profile.activity_level) if profile else 1.2
    calorie_target = 0
    if profile and all((profile.gender, profile.weight, profile.height, profile.age)):
        bmr = (10 * profile.weight + 6.25 * profile.height - 5 * profile.age + (5 if profile.gender == "Male" else -161))
        calorie_target = round(bmr * activity_factor)

    if goal_plan == "Fat Loss Program":
        calorie_text = f"Stay under {calorie_target - 500:.0f} kcal"
    elif goal_plan == "Muscle Gain Program":
        calorie_text = f"Reach {calorie_target + 300:.0f} kcal"
    else:
        calorie_text = f"Stay near {calorie_target:.0f} kcal"

    calorie_done = DailyMission.query.filter_by(user_id=user_id, mission_name=calorie_text, mission_date=today).first()
    challenge_done = DailyMission.query.filter_by(user_id=user_id, mission_name="Complete Today's Challenge", mission_date=today).first()

    completed_missions = sum([bool(water_done), bool(calorie_done), bool(challenge_done)])
    challenge_progress = round((completed_missions / 3) * 100, 1)

    current_region = REGIONS.get(progress.level, REGIONS[1])
    region_name = current_region["name"]
    xp_percent = min((progress.xp / 30) * 100, 100)
    boss_defeated = BossBattle.query.filter_by(user_id=user_id, boss_level=progress.level).first()
    boss_available = (completed_missions == 3) and not boss_defeated
    water_ml = water.water_ml if water else 0
    water_limit_reached = water_ml >= 3000

    if check_self_harm(user_message):
        response = get_mentor_response(
            user_message, streak.streak_count if streak else 0, get_evolution_label(progress.level),
            boss_available, region_name, xp_percent, water_ml, water_limit_reached, goal_plan, challenge_progress,
        )
    else:
        mentor_context = {
            "region_name": region_name, "level": progress.level, "xp": progress.xp,
            "streak": streak.streak_count if streak else 0, "water_ml": water_ml,
            "goal_plan": goal_plan or "Not set", "boss_available": boss_available,
            "challenge_progress": challenge_progress, "weight": profile.weight if profile else None,
            "target_weight": profile.target_weight if profile else None,
            "calorie_target": calorie_target if calorie_target else None,
        }
        gemini_reply = get_gemini_mentor_reply(user_message, mentor_context, client_history)

        if gemini_reply:
            response = gemini_reply
        else:
            response = get_mentor_response(
                user_message, streak.streak_count if streak else 0, get_evolution_label(progress.level),
                boss_available, region_name, xp_percent, water_ml, water_limit_reached, goal_plan, challenge_progress,
            )

    updated_history = list(client_history)
    if user_message:
        updated_history.append({"sender": "user", "text": user_message})
    updated_history.append({"sender": "mentor", "text": response})
    updated_history = updated_history[-6:]

    return jsonify({"response": response, "history": updated_history})

@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user"]
    today = date.today()

    water = WaterTracker.query.filter_by(user_id=user_id, water_date=today).first()

    water_limit_reached = False

    if water and water.water_ml >= 3000:
        water_limit_reached = True

    if not water:

        water = WaterTracker(user_id=user_id, water_ml=0, water_date=today)

        db.session.add(water)
        db.session.commit()

    progress = UserProgress.query.filter_by(user_id=user_id).first()

    bmi = None

    profile = UserProfile.query.filter_by(user_id=user_id).first()

    maintenance_calories = None
    fat_loss_calories = None
    muscle_gain_calories = None
    if profile and all((profile.gender, profile.weight, profile.height, profile.age)):

        if profile.gender == "Male":

            bmr = 10 * profile.weight + 6.25 * profile.height - 5 * profile.age + 5

        else:

            bmr = 10 * profile.weight + 6.25 * profile.height - 5 * profile.age - 161

        activity_factor = {
            "Sedentary": 1.2,
            "Light": 1.375,
            "Moderate": 1.55,
            "Active": 1.725,
            "Very Active": 1.9,
        }.get(profile.activity_level, 1.2)
        maintenance_calories = round(bmr * activity_factor)

        fat_loss_calories = round(maintenance_calories - 500)

        muscle_gain_calories = round(maintenance_calories + 300)

    logs = WeightLog.query.filter_by(user_id=user_id).order_by(WeightLog.id.asc()).all()

    chart_labels = []
    chart_weights = []

    for log in logs:

        if log.log_date:
            chart_labels.append(log.log_date.strftime("%d-%b"))
        else:
            chart_labels.append("Unknown")

        chart_weights.append(log.weight)

    starting_weight = None
    current_weight = None
    weight_lost = None

    goal_percent = 0

    if logs:
        starting_weight = logs[0].weight

        current_weight = logs[-1].weight

        weight_lost = round(starting_weight - current_weight, 1)

        if profile and profile.target_weight:
            total_needed = starting_weight - profile.target_weight

            achieved = starting_weight - current_weight

            if total_needed > 0:
                goal_percent = round((achieved / total_needed) * 100, 1)

                goal_percent = max(0, min(goal_percent, 100))

    bmi = None

    if profile and profile.height and profile.weight:

        height_m = profile.height / 100

        bmi = round(profile.weight / (height_m * height_m), 1)

    bmi_status = None

    if bmi:

        if bmi < 18.5:
            bmi_status = "Underweight"

        elif bmi < 25:
            bmi_status = "Healthy"

        elif bmi < 30:
            bmi_status = "Overweight"

        else:
            bmi_status = "Obese"

    goal_plan = None

    if bmi is not None:

        if bmi < 18.5:
            goal_plan = "Muscle Gain Program"

        elif bmi < 25:
            goal_plan = "Maintenance Program"

        elif bmi < 30:
            goal_plan = "Fat Loss Program"

        else:
            goal_plan = "Aggressive Fat Loss Program"

    meal_plan = []

    if goal_plan == "Fat Loss Program":
        meal_plan = [
            "🥣 Oats",
            "🥚 Egg Whites",
            "🍗 Chicken Breast",
            "🥗 Salad",
            "🍎 Apple",
        ]
    elif goal_plan == "Muscle Gain Program":
        meal_plan = [
            "🥚 Whole Eggs",
            "🥜 Peanut Butter",
            "🍌 Banana",
            "🍗 Chicken",
            "🍚 Rice",
        ]
    elif goal_plan == "Maintenance Program":

        meal_plan = [
            "🍳 Eggs",
            "🍚 Brown Rice",
            "🥗 Mixed Vegetables",
            "🍎 Apple",
            "🥛 Milk",
        ]

    missions = []

    completed_today = {
        mission.mission_name
        for mission in DailyMission.query.filter_by(
            user_id=user_id, mission_date=today
        ).all()
    }
    water_done = "Drink 2500ml Water" in completed_today

    missions.append(
        {
            "title": "Drink 2500ml Water",
            "reward": 5,
            "completed": water_done,
        }
    )

    if goal_plan == "Fat Loss Program":
        calorie_done = f"Stay under {fat_loss_calories} kcal" in completed_today
        missions.append(
            {
                "title": f"Stay under {fat_loss_calories} kcal",
                "reward": 10,
                "completed": calorie_done,
            }
        )

    elif goal_plan == "Muscle Gain Program":
        calorie_done = f"Reach {muscle_gain_calories} kcal" in completed_today
        missions.append(
            {
                "title": f"Reach {muscle_gain_calories} kcal",
                "reward": 10,
                "completed": calorie_done,
            }
        )

    else:
        calorie_done = f"Stay near {maintenance_calories} kcal" in completed_today
        missions.append(
            {
                "title": f"Stay near {maintenance_calories} kcal",
                "reward": 10,
                "completed": calorie_done,
            }
        )

    challenge_done = "Complete Today's Challenge" in completed_today

    missions.append(
        {
            "title": "Complete Today's Challenge",
            "reward": 20,
            "completed": challenge_done,
        }
    )

    streak = UserStreak.query.filter_by(user_id=user_id).first()
    if not streak:

        streak = UserStreak(streak_count=0)

    quote = random.choice(QUOTES)

    unlocked_level = progress.level

    current_region = REGIONS.get(unlocked_level, REGIONS[1])

    current_boss = BOSSES.get(progress.level)

    boss_defeated = BossBattle.query.filter_by(
        user_id=user_id, boss_level=progress.level
    ).first()

    region_name = current_region["name"]

    next_region = current_region["next"]

    region_target = get_region_target(progress.level)
    region_weeks = get_region_weeks(progress.level)
    region_progress = round((progress.completed / region_target) * 100, 1)
    region_progress = min(region_progress, 100)

    xp_percent = min((progress.xp / 30) * 100, 100)

    badges = get_badges(progress.level)

    warrior_title = "Recruit"

    if progress.xp >= 15:
        warrior_title = "Warrior"

    if progress.xp >= 30:
        warrior_title = "Champion"

    if progress.xp >= 50:
        warrior_title = "ACE"

    if progress.xp >= 75:
        warrior_title = "LEGEND"

        legend = Achievement.query.filter_by(
            user_id=user_id, achievement_name="Rise Back Legend"
        ).first()

        if not legend:

            db.session.add(
                Achievement(user_id=user_id, achievement_name="Rise Back Legend")
            )

            db.session.commit()
    achievements = Achievement.query.filter_by(user_id=user_id).all()

    achievement_popup = session.pop("achievement_popup", None)

    reward_popup = session.pop("reward_popup", None)

    rewards = RewardChest.query.filter_by(user_id=user_id).all()

    regions = [
        {"level": 1, "name": "🏕 Foundation Camp"},
        {"level": 2, "name": "⚔ Combat Valley"},
        {"level": 3, "name": "🏛 Elite Arena"},
        {"level": 4, "name": "👑 Legend Citadel"},
        {"level": 5, "name": "🔥 Legacy Throne"},
    ]

    if progress.level >= 5:

        evolution = "✨ CELESTIAL"

    elif progress.level >= 4:

        evolution = "👑 GOD"

    elif progress.level >= 3:

        evolution = "🔥 DEMIGOD"

    elif progress.level >= 2:

        evolution = "⚔ WARRIOR"

    else:

        evolution = "⚫ MORTAL"

    evolution_rate = min(round((progress.level / 5) * 100), 100)

    shadow_boss = None

    if evolution == "✨ CELESTIAL":

        shadow_boss = ShadowBoss.query.filter_by(user_id=user_id).first()

    boss_names = {
        1: "Foundation Guardian",
        2: "Combat Warlord",
        3: "Arena Destroyer",
        4: "Legend Emperor",
        5: "Legacy Throne Guardian",
    }

    defeated_bosses = BossBattle.query.filter_by(user_id=user_id).all()

    boss_descriptions = {
        1: "The Foundation Guardian tests your discipline.",
        2: "The Combat Warlord tests your endurance.",
        3: "The Arena Destroyer tests your consistency.",
        4: "The Legend Emperor tests your mastery.",
        5: "The Legacy Guardian tests your transformation.",
    }

    boss_description = boss_descriptions.get(
        progress.level, "A powerful guardian stands in your way."
    )

    region_completed = all(mission.get("completed", False) for mission in missions)

    boss_available = region_completed and not boss_defeated

    mentor_reply = get_ai_message(
        streak.streak_count if streak else 0,
        evolution,
        boss_available,
        region_name,
        xp_percent,
        water_ml=water.water_ml if water else 0,
        water_limit_reached=water_limit_reached,
        challenge_progress=region_progress,
        goal_plan=goal_plan,
    )

    mentor_response = session.get("mentor_response", mentor_reply)
    mentor_history = session.get("mentor_history", [])

    ai_message = mentor_reply

    return render_template(
        "dashboard.html",
        progress=progress,
        bmi=bmi,
        bmi_status=bmi_status,
        chart_labels=chart_labels,
        chart_weights=chart_weights,
        starting_weight=starting_weight,
        current_weight=current_weight,
        goal_plan=goal_plan,
        weight_lost=weight_lost,
        quote=quote,
        unlocked_level=unlocked_level,
        region_name=region_name,
        next_region=next_region,
        region_progress=region_progress,
        region_target=region_target,
        region_weeks=region_weeks,
        xp_percent=xp_percent,
        badges=badges,
        profile=profile,
        goal_percent=goal_percent,
        water=water,
        maintenance_calories=maintenance_calories,
        fat_loss_calories=fat_loss_calories,
        muscle_gain_calories=muscle_gain_calories,
        meal_plan=meal_plan,
        missions=missions,
        water_limit_reached=water_limit_reached,
        streak=streak,
        warrior_title=warrior_title,
        regions=regions,
        current_boss=current_boss,
        boss_defeated=boss_defeated,
        achievements=achievements,
        achievement_popup=achievement_popup,
        reward_popup=reward_popup,
        rewards=rewards,
        evolution=evolution,
        evolution_rate=evolution_rate,
        shadow_boss=shadow_boss,
        boss_names=boss_names,
        defeated_bosses=defeated_bosses,
        boss_description=boss_description,
        boss_available=boss_available,
        ai_message=ai_message,
        mentor_response=mentor_response,
        mentor_history=mentor_history,
    )


@app.route("/workouts", methods=["GET", "POST"])
@login_required
def workouts():
    user_id = session["user"]

    today = date.today()

    weekday = today.weekday()

    todays_plan = WORKOUT_SCHEDULE[weekday]

    if request.method == "POST":

        exercise_name = request.form.get("exercise_name", "").strip()

        sets = request.form.get("sets") or None
        reps = request.form.get("reps") or None
        weight_kg = request.form.get("weight_kg") or None
        duration = request.form.get("duration_minutes") or None
        notes = request.form.get("notes", "").strip()

        if exercise_name:

            duration_val = int(duration) if duration else 0

            cal_rate = CATEGORY_CALORIES_PER_MIN.get(todays_plan["focus"], 6)

            calories = round(duration_val * cal_rate) if duration_val else None

            log = WorkoutLog(
                user_id=user_id,
                workout_date=today,
                exercise_name=exercise_name,
                category=todays_plan["focus"],
                sets=int(sets) if sets else None,
                reps=int(reps) if reps else None,
                weight_kg=float(weight_kg) if weight_kg else None,
                duration_minutes=duration_val if duration_val else None,
                calories_burned=calories,
                notes=notes or None,
            )

            db.session.add(log)

            # Reward XP for logging — capped at 3 rewarded logs per day to discourage spam
            logs_today_count = WorkoutLog.query.filter_by(
                user_id=user_id, workout_date=today
            ).count()

            progress = UserProgress.query.filter_by(user_id=user_id).first()

            if progress and logs_today_count < 3:
                progress.xp += 5
                award_region_progress(progress, 1)

            first_workout = Achievement.query.filter_by(
                user_id=user_id, achievement_name="Iron Will"
            ).first()

            if not first_workout:

                db.session.add(
                    Achievement(user_id=user_id, achievement_name="Iron Will")
                )

                session["achievement_popup"] = {
                    "title": "Iron Will",
                    "description": "Logged your first workout",
                }

            db.session.commit()

        return redirect(url_for("workouts"))

    start_of_week = today - timedelta(days=weekday)

    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]

    logs_this_week = WorkoutLog.query.filter(
        WorkoutLog.user_id == user_id,
        WorkoutLog.workout_date >= start_of_week,
        WorkoutLog.workout_date <= week_dates[-1],
    ).all()

    logged_dates = {log.workout_date for log in logs_this_week}

    total_logged = WorkoutLog.query.filter_by(user_id=user_id).count()

    total_calories_week = sum(l.calories_burned or 0 for l in logs_this_week)

    total_minutes_week = sum(l.duration_minutes or 0 for l in logs_this_week)

    recent_logs = (
        WorkoutLog.query.filter_by(user_id=user_id)
        .order_by(WorkoutLog.id.desc())
        .limit(10)
        .all()
    )

    week_strip = []

    for i, d in enumerate(week_dates):

        week_strip.append(
            {
                "label": WORKOUT_SCHEDULE[i]["day"][:3],
                "date": d,
                "icon": WORKOUT_SCHEDULE[i]["icon"],
                "focus": WORKOUT_SCHEDULE[i]["focus"],
                "is_today": d == today,
                "logged": d in logged_dates,
                "is_future": d > today,
            }
        )

    return render_template(
        "workouts.html",
        todays_plan=todays_plan,
        week_strip=week_strip,
        recent_logs=recent_logs,
        total_logged=total_logged,
        total_calories_week=total_calories_week,
        total_minutes_week=total_minutes_week,
        logs_this_week_count=len(logs_this_week),
    )


@app.route("/challenges/<int:level>")
@login_required
def challenges(level):

    progress = UserProgress.query.filter_by(user_id=session["user"]).first()
    if not progress or level > progress.level:
        return redirect(url_for("dashboard"))

    data = get_region_challenges(level)
    region = REGION_CONFIG.get(level, REGION_CONFIG[1])

    return render_template(
        "challenges.html",
        challenges=data,
        level=level,
        region_name=region["name"],
        weeks=region["weeks"],
        target_progress=region["target_progress"],
    )


@app.route("/complete/<int:level>", methods=["POST"])
@login_required
def complete(level):

    user_id = session["user"]
    progress = UserProgress.query.filter_by(user_id=user_id).first()

    if not progress or level != progress.level:
        return redirect(url_for("dashboard"))

    today = date.today()

    streak = UserStreak.query.filter_by(user_id=user_id).first()

    if not streak:

        streak = UserStreak(user_id=user_id, streak_count=1, last_active=today)

        db.session.add(streak)

    else:

        days_gap = (today - streak.last_active).days

        if days_gap == 1:

            streak.streak_count += 1

        elif days_gap > 1:

            streak.streak_count = 1

        streak.last_active = today

    challenge_reward = DailyMission.query.filter_by(
        user_id=user_id, mission_name="Challenge XP Reward", mission_date=today
    ).first()

    if not challenge_reward:

        progress.xp += 3
        award_region_progress(progress, 1)

        db.session.add(
            DailyMission(
                user_id=user_id,
                mission_name="Challenge XP Reward",
                mission_date=today,
                completed=True,
            )
        )

    first_blood = Achievement.query.filter_by(
        user_id=user_id, achievement_name="First Blood"
    ).first()

    if not first_blood:

        db.session.add(Achievement(user_id=user_id, achievement_name="First Blood"))

        # Streak Bonus Rewards

    if streak.streak_count >= 7:

        iron = Achievement.query.filter_by(
            user_id=user_id, achievement_name="Iron Streak"
        ).first()

        if not iron:

            db.session.add(Achievement(user_id=user_id, achievement_name="Iron Streak"))
    existing = DailyMission.query.filter_by(
        user_id=user_id, mission_name="Complete Today's Challenge", mission_date=today
    ).first()

    if not existing:

        progress.xp += 20

        db.session.add(
            DailyMission(
                user_id=user_id,
                mission_name="Complete Today's Challenge",
                mission_date=today,
                completed=True,
            )
        )
    db.session.commit()

    return redirect(url_for("dashboard"))


@app.route("/add-water/<int:amount>", methods=["POST"])
@login_required
def add_water(amount):
    user_id = session["user"]
    today = date.today()

    if amount not in (250, 500):
        return redirect(url_for("dashboard"))

    water = WaterTracker.query.filter_by(user_id=user_id, water_date=today).first()

    if not water:

        water = WaterTracker(user_id=user_id, water_ml=0, water_date=today)

        db.session.add(water)

    # Stop adding if already at limit
    if water.water_ml >= MAX_DAILY_WATER_ML:
        flash("Daily water limit reached.", "warning")
        return redirect(url_for("dashboard"))

    # Add water but never exceed limit
    water.water_ml = min(water.water_ml + amount, MAX_DAILY_WATER_ML)

    # Auto-complete water mission at 2500 ml
    if water.water_ml >= 2500:
        achievement = Achievement.query.filter_by(
            user_id=user_id, achievement_name="Water Warrior"
        ).first()

        if not achievement:

            db.session.add(
                Achievement(user_id=user_id, achievement_name="Water Warrior")
            )

        existing = DailyMission.query.filter_by(
            user_id=user_id,
            mission_name="Drink 2500ml Water",
            mission_date=date.today(),
        ).first()

        if not existing:

            progress = UserProgress.query.filter_by(user_id=user_id).first()

            if progress:
                progress.xp += 5

            db.session.add(
                DailyMission(
                    user_id=user_id,
                    mission_name="Drink 2500ml Water",
                    mission_date=date.today(),
                    completed=True,
                )
            )

    db.session.commit()

    return redirect(url_for("dashboard"))


@app.route("/complete-mission", methods=["POST"])
@login_required
def complete_mission():

    user_id = session["user"]

    mission_name = request.form["mission"]

    water = WaterTracker.query.filter_by(
        user_id=user_id, water_date=date.today()
    ).first()

    if mission_name == "Drink 2500ml Water":

        if not water or water.water_ml < 2500:

            return """
            <h3>
            ❌ Drink at least 2500 ml water today
            before completing this mission.
            </h3>
            """

    profile = UserProfile.query.filter_by(user_id=user_id).first()
    calorie_mission = get_calorie_mission(profile)
    allowed_rewards = {
        "Drink 2500ml Water": 5,
        "Complete Today's Challenge": 20,
    }
    if calorie_mission:
        allowed_rewards[calorie_mission] = 10
    mission_name = mission_name.strip()
    xp = allowed_rewards.get(mission_name)
    if xp is None:
        return redirect(url_for("dashboard"))

    today = date.today()

    existing = DailyMission.query.filter_by(
        user_id=user_id, mission_name=mission_name, mission_date=today
    ).first()

    if existing:

        return redirect(url_for("dashboard"))

    progress = UserProgress.query.filter_by(user_id=user_id).first()

    progress.xp += xp
    award_region_progress(progress, 1)

    db.session.add(
        DailyMission(
            user_id=user_id,
            mission_name=mission_name,
            mission_date=today,
            completed=True,
        )
    )

    db.session.commit()

    return redirect(url_for("dashboard"))


@app.route("/boss-battle", methods=["POST"])
@login_required
def boss_battle():

    user_id = session["user"]

    progress = UserProgress.query.filter_by(user_id=user_id).first()

    completed_names = {
        mission.mission_name
        for mission in DailyMission.query.filter_by(
            user_id=user_id, mission_date=date.today()
        ).all()
    }
    calorie_complete = any(
        name.startswith(("Stay under ", "Reach ", "Stay near "))
        for name in completed_names
    )
    if (
        not {
            "Drink 2500ml Water",
            "Complete Today's Challenge",
        }.issubset(completed_names)
        or not calorie_complete
    ):
        flash("Complete today's missions before entering the boss battle.", "warning")
        return redirect(url_for("dashboard"))

    existing = BossBattle.query.filter_by(
        user_id=user_id, boss_level=progress.level
    ).first()

    if existing:

        return """
        <h2>
        ⚔ Boss already defeated
        </h2>

        <a href='/dashboard'>
        Return
        </a>
        """

    boss = BOSSES.get(progress.level)

    progress.xp += boss["reward"]

    reward = REWARDS.get(progress.level)

    db.session.add(
        RewardChest(
            user_id=user_id,
            reward_name=reward["name"],
            reward_description=reward["description"],
        )
    )

    session["reward_popup"] = reward

    db.session.add(
        BossBattle(user_id=user_id, boss_level=progress.level, defeated=True)
    )

    db.session.commit()

    boss_slayer = Achievement.query.filter_by(
        user_id=user_id, achievement_name="Boss Slayer"
    ).first()

    if not boss_slayer:

        db.session.add(Achievement(user_id=user_id, achievement_name="Boss Slayer"))

        session["achievement_popup"] = {
            "title": "Boss Slayer",
            "description": "Defeat your first Region Boss",
        }

        db.session.commit()

    return """
    <h1>
    👹 BOSS DEFEATED
    </h1>

    <h3>
    REWARD CLAIMED
    </h3>

    <a href='/dashboard'>
    Return To Kingdom
    </a>
    """


@app.route("/shadow-boss", methods=["POST"])
@login_required
def shadow_boss_battle():

    user_id = session["user"]

    existing = ShadowBoss.query.filter_by(user_id=user_id).first()

    if existing:

        return """
        <h2>
        👑 Destiny Already Fulfilled
        </h2>

        <a href='/dashboard'>
        Return
        </a>
        """

    db.session.add(ShadowBoss(user_id=user_id, defeated=True))

    db.session.commit()

    return """
    <h1>
    ⚔ THE OLD YOU HAS FALLEN
    </h1>

    <h2>
    👑 TITLE UNLOCKED
    </h2>

    <h1>
    RISE BACK LEGEND
    </h1>

    <a href='/dashboard'>
    Return To Kingdom
    </a>
    """


@app.route("/mentor-chat", methods=["POST"])
@login_required
def mentor_chat():
    user_id = session["user"]
    progress = UserProgress.query.filter_by(user_id=user_id).first()

    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json
    )

    if not progress:
        if is_ajax:
            return jsonify(
                {
                    "response": "Set up your warrior profile first, then your mentor will be ready.",
                    "history": [],
                }
            )
        return redirect(url_for("dashboard"))

    user_message = request.form.get("message", "").strip()[:500]

    progress = UserProgress.query.filter_by(user_id=user_id).first()
    water = WaterTracker.query.filter_by(
        user_id=user_id, water_date=date.today()
    ).first()
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    streak = UserStreak.query.filter_by(user_id=user_id).first()

    if not progress:
        return redirect(url_for("dashboard"))

    if not streak:
        streak = UserStreak(user_id=user_id, streak_count=0)

    goal_plan = None
    if profile and profile.height and profile.weight:
        height_m = profile.height / 100
        bmi = round(profile.weight / (height_m * height_m), 1)
        if bmi < 18.5:
            goal_plan = "Muscle Gain Program"
        elif bmi < 25:
            goal_plan = "Maintenance Program"
        elif bmi < 30:
            goal_plan = "Fat Loss Program"
        else:
            goal_plan = "Aggressive Fat Loss Program"

    today = date.today()
    water_done = DailyMission.query.filter_by(
        user_id=user_id, mission_name="Drink 2500ml Water", mission_date=today
    ).first()

    activity_factor = get_activity_factor(profile.activity_level) if profile else 1.2
    calorie_target = 0

    if profile and all((profile.gender, profile.weight, profile.height, profile.age)):
        bmr = (
            10 * profile.weight
            + 6.25 * profile.height
            - 5 * profile.age
            + (5 if profile.gender == "Male" else -161)
        )
        calorie_target = round(bmr * activity_factor)

    if goal_plan == "Fat Loss Program":
        calorie_text = f"Stay under {calorie_target - 500:.0f} kcal"
    elif goal_plan == "Muscle Gain Program":
        calorie_text = f"Reach {calorie_target + 300:.0f} kcal"
    else:
        calorie_text = f"Stay near {calorie_target:.0f} kcal"

    calorie_done = DailyMission.query.filter_by(
        user_id=user_id, mission_name=calorie_text, mission_date=today
    ).first()

    challenge_done = DailyMission.query.filter_by(
        user_id=user_id, mission_name="Complete Today's Challenge", mission_date=today
    ).first()

    completed_missions = 0
    completed_missions += 1 if water_done else 0
    completed_missions += 1 if calorie_done else 0
    completed_missions += 1 if challenge_done else 0
    challenge_progress = round((completed_missions / 3) * 100, 1)

    current_region = REGIONS.get(progress.level, REGIONS[1])
    region_name = current_region["name"]
    xp_percent = min((progress.xp / 30) * 100, 100)
    boss_defeated = BossBattle.query.filter_by(
        user_id=user_id, boss_level=progress.level
    ).first()
    region_completed = completed_missions == 3
    boss_available = region_completed and not boss_defeated
    water_ml = water.water_ml if water else 0
    water_limit_reached = water_ml >= 3000

    if check_self_harm(user_message):
        response = get_mentor_response(
            user_message,
            streak.streak_count if streak else 0,
            get_evolution_label(progress.level),
            boss_available,
            region_name,
            xp_percent,
            water_ml,
            water_limit_reached,
            goal_plan,
            challenge_progress,
        )
    else:
        mentor_context = {
            "region_name": region_name,
            "level": progress.level,
            "xp": progress.xp,
            "streak": streak.streak_count if streak else 0,
            "water_ml": water_ml,
            "goal_plan": goal_plan or "Not set",
            "boss_available": boss_available,
            "challenge_progress": challenge_progress,
            "weight": profile.weight if profile else None,
            "target_weight": profile.target_weight if profile else None,
            "calorie_target": calorie_target if calorie_target else None,
        }
        gemini_reply = get_gemini_mentor_reply(
            user_message, mentor_context, session.get("mentor_history", [])
        )

        if gemini_reply:
            response = gemini_reply
        else:
            response = get_mentor_response(
                user_message,
                streak.streak_count if streak else 0,
                get_evolution_label(progress.level),
                boss_available,
                region_name,
                xp_percent,
                water_ml,
                water_limit_reached,
                goal_plan,
                challenge_progress,
            )

    # maintain simple conversation history in session
    history = session.get("mentor_history", [])
    if user_message:
        history.append({"sender": "user", "text": user_message})
    history.append({"sender": "mentor", "text": response})
    # Flask's default session is cookie-backed; keep a small context window.
    session["mentor_history"] = history[-6:]
    session["mentor_response"] = response

    # If this is an AJAX request, return JSON so the frontend can update without reload
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify(
            {"response": response, "history": session.get("mentor_history", [])}
        )

    return redirect(url_for("dashboard"))


@app.route("/logout", methods=["POST"])
@login_required
def logout():

    session.pop("user", None)

    return redirect(url_for("home"))


@app.route("/healthz")
def healthcheck():
    return {"status": "ok"}


with app.app_context():
    db.create_all()
    migrate_legacy_schema()


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session["user"]

    existing_profile = UserProfile.query.filter_by(user_id=user_id).first()

    if request.method == "POST":

        if not existing_profile:

            profile = UserProfile(
                user_id=user_id,
                age=request.form["age"],
                gender=request.form["gender"],
                height=request.form["height"],
                weight=request.form["weight"],
                fitness_goal=request.form["fitness_goal"],
                activity_level=request.form["activity_level"],
                target_weight=request.form["target_weight"],
            )

            db.session.add(profile)

        else:

            existing_profile.age = request.form["age"]
            existing_profile.gender = request.form["gender"]
            existing_profile.height = request.form["height"]
            existing_profile.weight = request.form["weight"]
            existing_profile.fitness_goal = request.form["fitness_goal"]
            existing_profile.activity_level = request.form["activity_level"]
            existing_profile.target_weight = request.form["target_weight"]

        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("profile.html", profile=existing_profile)


@app.route("/weight", methods=["GET", "POST"])
@login_required
def weight():
    user_id = session["user"]

    if request.method == "POST":

        weight = request.form["weight"]

        log = WeightLog(user_id=user_id, weight=weight, log_date=date.today())

        db.session.add(log)
        db.session.commit()

        return redirect(url_for("dashboard"))

    logs = (
        WeightLog.query.filter_by(user_id=user_id)
        .order_by(WeightLog.log_date.desc())
        .all()
    )

    return render_template("weight.html", logs=logs)


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
