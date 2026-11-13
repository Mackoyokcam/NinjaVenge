"""Tunable constants. Every magic number in the game should live here."""
import os

TITLE = "Ninjavenge"
SCREEN_W, SCREEN_H = 1500, 800
FPS = 60
MAX_DT = 1 / 20  # clamp long frames (window drags etc.) so physics doesn't explode

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SRC_DIR, "data")
SAVE_PATH = os.path.join(os.path.expanduser("~"), ".ninjavenge", "scores.json")
PROFILE_PATH = os.path.join(os.path.expanduser("~"), ".ninjavenge", "profile.json")

# Lanes: y coordinate of each lane's floor, bottom lane first.
LANE_FLOORS = [700, 550, 400, 250]
LANE_THICKNESS = 14
SPAWN_MARGIN = 90  # enemies spawn / leak this far outside the screen edge

# Colours
BLACK = (0, 0, 0)
WHITE = (240, 240, 240)
RED = (220, 50, 50)
GOLD = (250, 200, 60)
ORANGE = (255, 140, 30)
CYAN = (90, 210, 255)
GREY = (120, 120, 130)
DARK = (14, 14, 24)
UI_ACCENT = (200, 40, 60)

# --- Player -----------------------------------------------------------------
PLAYER_MAX_HEARTS = 5
PLAYER_SPEED = 380          # px/s
PLAYER_ANCHOR = 36          # body centre offset from the sprite's back edge
PLAYER_BODY = (44, 120)     # hitbox w, h
LANE_SWITCH_TIME = 0.32     # seconds for a lane hop
LANE_SWITCH_ARC = 55        # extra hop height in px
SHINOBI_SWITCH_TIME = 0.08  # Shinobi Mode teleport
ATTACK_TIME = 0.36
ATTACK_ACTIVE = (0.25, 0.75)  # fraction of the swing where the blade hurts
SWORD_REACH = (118, 100)    # sword hitbox w, h (in front of the body centre)
THROW_TIME = 0.30
THROW_RELEASE = 0.35        # fraction of the throw animation when the kunai leaves
KUNAI_COOLDOWN = 0.65
KUNAI_SPEED = 950
HURT_TIME = 0.25
INVULN_TIME = 1.2
KNOCKBACK = 140

# --- Enemies ------------------------------------------------------------------
ENEMY_BODY = (60, 125)
COWBOY_SPEED = 120
COWBOY_FIRE_COOLDOWN = (2.2, 3.8)
COWBOY_TELEGRAPH = 0.5
BULLET_SPEED = 520
ROBOT_SPEED = 65
ROBOT_HP = 3
ROBOT_STAGGER = 0.9
JACK_SPEED = 85
JACK_REVIVE_TIME = 3.5
JACK_REVIVE_SPEEDUP = 1.25
BOSS_SPEED = 40
BOSS_BODY = (72, 200)
BOSS_STAGGER = 0.5
BOSS_INTERRUPT_STAGGER = 1.0   # kunai during a boss telegraph
BOSS_LEAK_COST = 3
KNIGHT_ATTACK_TIME = 1.0
KNIGHT_SWING = (0.5, 0.75)     # fraction of the attack animation where the blade hurts
KNIGHT_REACH = (150, 140)      # outranges Ren's katana: interrupt it, dodge it, or hop lanes
KNIGHT_ATTACK_COOLDOWN = (1.6, 2.6)
DINO_SPEED = 45
DINO_CHARGE_COOLDOWN = (3.5, 5.0)
DINO_WINDUP = 0.8
DINO_CHARGE_TIME = 1.1
DINO_CHARGE_SPEED = 420
CORPSE_FADE = 1.2

# --- Scoring --------------------------------------------------------------------
POINTS = {"cowboy": 100, "robot": 200, "jack": 150, "boss": 1500}
SMASH_BONUS = 50
AIR_KILL_BONUS = 50
DEFLECT_BONUS = 10
COMBO_STEP = 5      # kills needed per multiplier level
COMBO_MAX = 5

# --- Currency (ryo) ---------------------------------------------------------------
RYO = {"cowboy": 1, "jack": 2, "robot": 3, "boss": 25}
RYO_PER_WAVE = 2     # clearing wave N pays N * this
RICOCHET_SPEED_MULT = 1.4

# --- Feel -----------------------------------------------------------------------
HITSTOP_HIT = 0.05
HITSTOP_KILL = 0.08
SHAKE_HIT = 6
SHAKE_HURT = 14
