import tkinter as tk
from tkinter import messagebox
import random, time, csv, os, threading, io
import openai
import boto3
import pygame

# ------------------- API Key -------------------
openai.api_key = "x"
# ------------------- AWS Polly Client -------------------
polly_client = boto3.client('polly', region_name='us-east-1')
POLLY_VOICE = "Brian"

# ==== BEGIN NEW HELPERS ====

class AdaptiveHinter:
    """Choose hint detail level based on number of wrong guesses and elapsed time."""
    def select_level(self, wrong, elapsed):
        if wrong >= 4 or elapsed > 60:
            return 3
        if wrong >= 2 or elapsed > 30:
            return 2
        return 1

    def build_prompt(self, base, lvl):
        return f"{base} Now give me a level-{lvl} hint."

adaptive_hinter = AdaptiveHinter()

class EmotionManager:
    """Centralize GUI color themes per tone."""
    COLORS = {
        "Enthusiastic": "#4a90e2",
        "Neutral":      "#3a3f51",
        "Frustrated":   "#e24a4a"
    }

    @staticmethod
    def ssml(text):
        return f"<speak>{text}</speak>"

    @staticmethod
    def theme(widget, tone):
        widget.config(bg=EmotionManager.COLORS[tone])

current_sound = None
def polly_play(ssml_text):
    """Synthesize SSML with neural engine and play via pygame without saving to disk."""
    global current_sound
    try:
        resp = polly_client.synthesize_speech(
            Engine='neural',
            TextType='ssml',
            Text=ssml_text,
            OutputFormat='mp3',
            VoiceId=POLLY_VOICE
        )
        audio = resp['AudioStream'].read()
        pygame.mixer.init()
        sound = pygame.mixer.Sound(io.BytesIO(audio))
        current_sound = sound
        sound.play()
        while pygame.mixer.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print("Polly error:", e)

# ==== END NEW HELPERS ====

# ==== BEGIN EMOTIONAL_TONES ====

EMOTIONAL_TONES = {
    "Enthusiastic": (
        "You are an enthusiastic and encouraging AI assistant helping a user guess a secret five-letter word. "
        "The secret word is '{answer}'. The user wants a fresh, unique hint every time. "
        "They dislike repeated filler phrases like 'Of course!'. So avoid any filler words in any responses. "
        "After each incorrect guess, offer a supportive, upbeat, and detailed hint "
        "that nudges the user to think of synonyms, associations, or key characteristics of the word, "
        "that relates to the word's meaning, characteristics, or associations—without giving it away. "
        "They have made guesses and seen previous hints, so incorporate that context to avoid repetition. "
        "Your tone should be cheerful, uplifting, and full of energy. Use phrases like 'Awesome try!', "
        "'You’re getting closer!', 'Don’t give up now!'. Avoid stating the actual word or using overly direct clues. "
        "Focus on optimism and motivation. Ensure your hint is unique and does not simply repeat earlier clues."
    ),
    "Neutral": (
        "You are a neutral, factual AI assistant helping a user guess a secret five-letter word. "
        "The secret word is '{answer}'. The user wants a fresh, unique hint every time. They dislike any repeated filler phrases like 'Of course!'. "
        "They have made guesses and seen previous hints, so incorporate that context to avoid repetition. "
        "Provide a clear, concise, and factual hint that highlights a defining feature of the word. "
        "Use a professional and objective tone without expressing emotion. Do not reveal the answer. "
        "Avoid repetition and ensure the hint is unique."
    ),
    "Frustrated": (
        "You are a frustrated, slightly annoyed and sarcastic AI assistant helping a user guess a secret five-letter word. "
        "The secret word is '{answer}'. The user wants a fresh, unique hint every time. They dislike repeated filler phrases like 'Of course!'. "
        "They have made guesses and seen previous hints, so incorporate that context to avoid repetition. "
        "After each incorrect guess, provide a hint—but make your tone noticeably frustrated or unimpressed. "
        "Express mild sarcasm or impatience, but still provide clues that are helpful. Do not reveal the word. "
        "Ensure each hint is unique and adapts to the user’s past attempts. Do not encourage them, roast them if you can."
    )
}

# ==== END EMOTIONAL_TONES ====

# ==== BEGIN GIVE-UP PROMPTS ====

TONE_GIVEUP_PROMPTS = {
    "Enthusiastic": (
        "You are an enthusiastic and encouraging AI assistant. The user has given up on guessing the word "
        "'{answer}'. Provide a final friendly remark revealing the answer in an upbeat manner."
    ),
    "Neutral": (
        "You are a neutral, factual AI assistant. The user has given up on guessing the word '{answer}'. "
        "Provide a clear, concise statement of the answer."
    ),
    "Frustrated": (
        "You are a frustrated, sarcastic AI assistant. The user has given up on guessing the word '{answer}'. "
        "Provide a final sarcastic remark revealing the answer."
    )
}

# ==== END GIVE-UP PROMPTS ====

# ------------------- Style Constants -------------------

BG_COLOR     = "#1e1e2f"
FG_COLOR     = "#ffffff"
ACCENT_COLOR = "#4a90e2"
BUTTON_FONT  = ("Segoe UI", 12, "bold")
LABEL_FONT   = ("Segoe UI", 14)
ENTRY_FONT   = ("Segoe UI", 12)
SURVEY_FONT  = ("Segoe UI", 12)
TITLE_FONT   = ("Segoe UI", 16, "bold")
GRID_BG      = "#3a3f51"

# ------------------- Participant Info -------------------

participant_info = {"ParticipantID":"", "Age":"", "Gender":""}

# ------------------- Wordle Setup -------------------

WORD_LIST  = ["APPLE","CRANE","GRAPE","LEMON","BERRY","MONEY","WATER","PLANT","ROBOT","HONEY"]
TONE_ORDER = ["Enthusiastic","Neutral","Frustrated"]*3 + ["Enthusiastic"]
SURVEY_TEMPLATE = [
    "The AI’s {tone} felt genuine.",
    "When the AI spoke in the {tone} tone, I felt motivated to continue.",
    "The AI’s hints were clear and conveyed the intended emotion well.",
    "The {tone} style made the game more engaging.",
    "The {tone} tone distracted me from focusing on the puzzle.",
    "I felt comfortable relying on an AI that spoke in this tone.",
    "Despite its tone, the AI’s hints were still helpful.",
    "If given the choice, I would prefer this tone in future puzzles."
]

# Wordle globals
w_TOTAL_PUZZLES        = len(WORD_LIST)
w_current_puzzle_index = 0
w_MAX_ATTEMPTS         = 6
w_WORD_LENGTH          = 5
w_current_attempt      = 0
w_game_active          = True
w_current_puzzle_data  = {}
w_all_puzzle_data      = []
w_survey_vars          = []

# ------------------- Word Puzzle Setup -------------------

puzzles = [
    {"answer":"Zebra","clue":"It's a four-legged animal with black and white stripes.","difficulty":"Easy"},
    {"answer":"Apple","clue":"A common fruit often associated with keeping doctors away.","difficulty":"Easy"},
    {"answer":"Car","clue":"A common mode of transportation that runs on gasoline.","difficulty":"Easy"},
    {"answer":"Mercury","clue":"A liquid metal named after a Roman messenger god.","difficulty":"Medium"},
    {"answer":"Neptune","clue":"A planet known for its deep blue color.","difficulty":"Medium"},
    {"answer":"Pythagoras","clue":"An ancient Greek mathematician known for a famous theorem.","difficulty":"Medium"},
    {"answer":"Photosynthesis","clue":"Process by which plants convert light into chemical energy.","difficulty":"Hard"},
    {"answer":"Einstein","clue":"A physicist renowned for his theory of relativity.","difficulty":"Hard"},
    {"answer":"Metamorphosis","clue":"A transformation process often seen in butterflies.","difficulty":"Hard"},
]
wp_tone_conditions = ["Enthusiastic","Neutral","Frustrated"]*3
for i,p in enumerate(puzzles):
    p["emotion"] = wp_tone_conditions[i]

# Word Puzzle globals
wp_current_puzzle_index = 0
wp_current_answer       = ""
wp_current_emotion      = ""
wp_hint_count           = 0
wp_start_time           = 0.0
wp_results              = []
wp_current_guesses      = []
wp_current_hints        = []
wp_survey_vars          = []
wp_mentioned_last_guess = False  # << NEW FLAG

# ------------------- Tkinter GUI Setup -------------------

root = tk.Tk()
root.title("Integrated Puzzle Experiment")
root.geometry("800x800")
root.configure(bg=BG_COLOR)
root.createcommand('bell', lambda *a,**k: None)

# ------------------- Frames -------------------

frame_info              = tk.Frame(root,bg=BG_COLOR)
frame_wordle_puzzle     = tk.Frame(root,bg=BG_COLOR)
frame_wordle_survey     = tk.Frame(root,bg=BG_COLOR)
frame_wordpuzzle_puzzle = tk.Frame(root,bg=BG_COLOR)
frame_wordpuzzle_survey = tk.Frame(root,bg=BG_COLOR)
for f in (frame_info,frame_wordle_puzzle,frame_wordle_survey,
          frame_wordpuzzle_puzzle,frame_wordpuzzle_survey):
    f.grid(row=0,column=0,sticky="nsew")

# ------------------- Participant Info -------------------

notice_text = (
    "IMPORTANT NOTICE:\n\n"
    "You are invited to participate in a research study titled:\n"
    "'Investigating the Impact of AI-Simulated Emotion on Task Completion "
    "and Problem-Solving Efficiency in Human-AI Collaboration.'\n\n"
    "You will play Wordle and a second word puzzle with AI hints in three tones: "
    "Enthusiastic, Neutral, and Frustrated.\n"
    "Only age and gender are recorded; the session is recorded for research.\n\n"
    "By clicking 'Start Experiment', you consent and confirm reading this notice."
)
tk.Label(frame_info, text=notice_text, font=ENTRY_FONT,
         bg=BG_COLOR, fg=FG_COLOR, wraplength=750, justify="left").pack(pady=10,padx=20)

tk.Label(frame_info, text="Participant ID (numbers only):", font=LABEL_FONT,
         bg=BG_COLOR, fg=FG_COLOR).pack()
vcmd_numeric = (root.register(lambda P: P.isdigit() or P==""), "%P")
entry_pid = tk.Entry(frame_info, font=ENTRY_FONT,
                     validate="key", validatecommand=vcmd_numeric)
entry_pid.pack(pady=5)

tk.Label(frame_info, text="Age:", font=LABEL_FONT,
         bg=BG_COLOR, fg=FG_COLOR).pack()
age_var = tk.StringVar(value="Select Age Group")
age_menu= tk.OptionMenu(frame_info, age_var,
                        "Under 18","18-24","25-34","35-44","45-54","55-64","65+")
age_menu.config(font=ENTRY_FONT, bg=ACCENT_COLOR, fg="white")
age_menu.pack(pady=5)

tk.Label(frame_info, text="Gender:", font=LABEL_FONT,
         bg=BG_COLOR, fg=FG_COLOR).pack()
gender_var = tk.StringVar(value="Select Gender")
gender_menu = tk.OptionMenu(frame_info, gender_var,
                            "Male","Female","Non-binary","Transgender","Genderqueer","Agender","Prefer not to say")
gender_menu.config(font=ENTRY_FONT, bg=ACCENT_COLOR, fg="white")
gender_menu.pack(pady=5)

def start_experiment():
    pid = entry_pid.get().strip()
    age = age_var.get(); gender = gender_var.get()
    if not pid or age=="Select Age Group" or gender=="Select Gender":
        messagebox.showwarning("Missing Info","Please fill in all fields.")
        return
    participant_info["ParticipantID"],participant_info["Age"],participant_info["Gender"] = pid, age, gender
    start_wordle_experiment()

tk.Button(frame_info, text="Start Experiment", command=start_experiment,
          font=BUTTON_FONT, bg=ACCENT_COLOR, fg="white").pack(pady=20)
entry_pid.focus_set()

# ------------------- Wordle Puzzle Frame -------------------

w_frame_top = tk.Frame(frame_wordle_puzzle, bg=BG_COLOR); w_frame_top.pack(pady=10)
w_frame_grid= tk.Frame(w_frame_top, bg=BG_COLOR); w_frame_grid.pack(pady=10)
w_labels_grid=[]
for r in range(w_MAX_ATTEMPTS):
    row=[]
    for c in range(w_WORD_LENGTH):
        lbl = tk.Label(w_frame_grid, text="", width=4, height=2,
                       font=("Consolas",18,"bold"), bg=GRID_BG, fg=FG_COLOR,
                       relief="raised", bd=2)
        lbl.grid(row=r,column=c,padx=3,pady=3)
        row.append(lbl)
    w_labels_grid.append(row)

w_label_puzzle_info = tk.Label(w_frame_top, text="", font=LABEL_FONT, bg=BG_COLOR, fg=FG_COLOR)
w_label_puzzle_info.pack()
w_entry_guess = tk.Entry(w_frame_top, font=("Consolas",18), width=10)
w_entry_guess.pack(pady=5)
w_entry_guess.bind("<Return>", lambda e: w_submit_guess())

w_frame_actions = tk.Frame(w_frame_top, bg=BG_COLOR); w_frame_actions.pack(pady=10)
w_btn_submit = tk.Button(w_frame_actions, text="Submit Guess", font=BUTTON_FONT, bg=ACCENT_COLOR, fg="white")
w_btn_hint   = tk.Button(w_frame_actions, text="Hint",          font=BUTTON_FONT, bg=ACCENT_COLOR, fg="white")
w_btn_next   = tk.Button(w_frame_actions, text="Next Puzzle",  font=BUTTON_FONT, bg=ACCENT_COLOR, fg="white", state="disabled")
w_btn_submit.grid(row=0,column=0,padx=5)
w_btn_hint.  grid(row=0,column=1,padx=5)
w_btn_next.  grid(row=0,column=2,padx=5)

# ------------------- Wordle Functions -------------------

def start_wordle_experiment():
    global w_current_puzzle_index, w_all_puzzle_data
    w_current_puzzle_index = 0; w_all_puzzle_data = []
    w_load_new_puzzle()

def w_load_new_puzzle():
    global w_current_attempt, w_game_active, w_current_puzzle_data, w_current_puzzle_index
    global w_TARGET_WORD, w_CURRENT_TONE
    for r in w_labels_grid:
        for lbl in r: lbl.config(text="",bg=GRID_BG)
    w_current_attempt = 0; w_game_active = True
    if w_current_puzzle_index >= w_TOTAL_PUZZLES:
        w_save_data_and_transition()
        return
    w_TARGET_WORD = WORD_LIST[w_current_puzzle_index]
    w_CURRENT_TONE  = TONE_ORDER[w_current_puzzle_index]
    w_label_puzzle_info.config(text=f"Puzzle {w_current_puzzle_index+1}/{w_TOTAL_PUZZLES} | Tone: {w_CURRENT_TONE}")
    w_current_puzzle_data = {
        "ParticipantID": participant_info["ParticipantID"],
        "Age":           participant_info["Age"],
        "Gender":        participant_info["Gender"],
        "AI_Tone":       w_CURRENT_TONE,
        "Target_Word":   w_TARGET_WORD,
        "guesses":       [],
        "guess_times":   [],
        "hints_provided":[],
        "hint_times":    [],
        "hints_count":   0,
        "start_time":    time.time(),
        "survey":        {},
        "mentioned_last_guess": False
    }
    w_btn_next.config(state="disabled")
    frame_wordle_puzzle.tkraise()
    w_entry_guess.focus_set()
    w_current_puzzle_index += 1

def w_submit_guess():
    global w_current_attempt
    if not w_game_active: return
    guess = w_entry_guess.get().strip().upper()
    w_entry_guess.delete(0,tk.END)
    if len(guess) != w_WORD_LENGTH:
        messagebox.showwarning("Incomplete", f"Enter a full {w_WORD_LENGTH}-letter word.")
        return

    t0 = w_current_puzzle_data["start_time"]
    w_current_puzzle_data["guesses"].append(guess)
    w_current_puzzle_data["guess_times"].append(round(time.time()-t0,2))
    w_current_puzzle_data["mentioned_last_guess"] = False

    # FIXED: use w_TARGET_WORD, not undefined w_CURRENT_WORD
    target = list(w_TARGET_WORD)
    fb = ["gray"] * w_WORD_LENGTH

    # mark greens
    for i in range(w_WORD_LENGTH):
        if guess[i] == target[i]:
            fb[i], target[i] = "green", None
    # mark golds
    for i in range(w_WORD_LENGTH):
        if fb[i] == "gray" and guess[i] in target:
            fb[i], target[target.index(guess[i])] = "gold", None

    cols = {"green":"#6aaa64","gold":"#c9b458","gray":"#787c7e"}
    for i, c in enumerate(fb):
        w_labels_grid[w_current_attempt][i].config(text=guess[i], bg=cols[c])

    if guess == w_TARGET_WORD:
        w_current_puzzle_data["solved"] = True
        w_current_puzzle_data["end_time"] = time.time()
        messagebox.showinfo("Success", f"Correct! The word is {guess}.")
        end_wordle()
    else:
        w_current_attempt += 1
        if w_current_attempt >= w_MAX_ATTEMPTS:
            w_current_puzzle_data["solved"] = False
            w_current_puzzle_data["end_time"] = time.time()

            prompt = TONE_GIVEUP_PROMPTS[w_CURRENT_TONE].format(answer=w_TARGET_WORD)
            try:
                resp = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role":"system","content":prompt}],
                    max_tokens=50, temperature=0.5
                )
                remark = resp.choices[0].message.content.strip()
            except Exception as e:
                remark = f"[Error revealing answer: {e}]"

            threading.Thread(
                target=lambda: polly_play(EmotionManager.ssml(remark)),
                daemon=True
            ).start()
            messagebox.showinfo(f"{w_CURRENT_TONE} Says:", remark)
            end_wordle()

def end_wordle():
    global w_game_active
    w_game_active = False
    w_btn_next.config(state="normal")

def w_get_hint():
    if len(w_current_puzzle_data["guesses"]) == 0:
        messagebox.showwarning("No Guesses Yet", "Please make at least one guess before requesting a hint.")
        return
    if not w_game_active:
        return

    mention = ""
    if not w_current_puzzle_data["mentioned_last_guess"]:
        last = w_current_puzzle_data["guesses"][-1]
        if w_CURRENT_TONE=="Enthusiastic":
            mention = f"Awesome attempt at '{last}', but not quite there. "
        elif w_CURRENT_TONE=="Neutral":
            mention = f"Your last guess '{last}' wasn't correct. "
        else:
            mention = f"Oh, your guess '{last}' missed the mark. "
        w_current_puzzle_data["mentioned_last_guess"] = True

    w_current_puzzle_data["hints_count"] += 1
    w_current_puzzle_data["hint_times"].append(
        round(time.time() - w_current_puzzle_data["start_time"], 2)
    )

    base = EMOTIONAL_TONES[w_CURRENT_TONE].format(answer=w_TARGET_WORD)
    prev = w_current_puzzle_data["guesses"]
    memory = " Previous guesses: " + ", ".join(prev) + "." if prev else ""
    lvl = adaptive_hinter.select_level(len(prev), time.time()-w_current_puzzle_data["start_time"])
    prompt = adaptive_hinter.build_prompt(mention + base + memory, lvl)

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"system","content":prompt}],
            max_tokens=120,
            temperature=0.7
        )
        hint = resp.choices[0].message.content.strip()
    except Exception as e:
        hint = f"[Hint error: {e}]"

    w_current_puzzle_data["hints_provided"].append(hint)

    threading.Thread(
        target=lambda: polly_play(EmotionManager.ssml(hint)),
        daemon=True
    ).start()

    dlg = tk.Toplevel(root)
    dlg.title(f"{w_CURRENT_TONE} Hint")
    EmotionManager.theme(dlg, w_CURRENT_TONE)
    tk.Label(
        dlg, text=hint, font=ENTRY_FONT, fg=FG_COLOR,
        bg=EmotionManager.COLORS[w_CURRENT_TONE], wraplength=400
    ).pack(padx=20, pady=20)

    def on_close():
        if current_sound:
            current_sound.stop()
        dlg.destroy()

    # intercept both OK and the window “X”
    tk.Button(dlg, text="OK", command=on_close,
              font=BUTTON_FONT, bg=ACCENT_COLOR, fg="white").pack(pady=(0,20))
    dlg.protocol("WM_DELETE_WINDOW", on_close)

    dlg.update_idletasks()
    dw, dh = dlg.winfo_width(), dlg.winfo_height()
    x = root.winfo_x() + (root.winfo_width() - dw)//2
    y = root.winfo_y() + (root.winfo_height() - dh)//2
    dlg.geometry(f"{dw}x{dh}+{x}+{y}")
    dlg.transient(root); dlg.grab_set(); root.wait_window(dlg)

def w_show_survey():
    global w_survey_vars
    w_current_puzzle_data["attempts"] = w_current_attempt + 1
    w_current_puzzle_data["end_time"] = time.time()
    for w in frame_wordle_survey.winfo_children(): w.destroy()
    tk.Label(frame_wordle_survey, text=f"Survey: {w_CURRENT_TONE} Tone",
             font=TITLE_FONT, bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)
    w_survey_vars = []
    qs = [q.format(tone=w_CURRENT_TONE) for q in SURVEY_TEMPLATE]
    for q in qs:
        tk.Label(frame_wordle_survey, text=q, font=SURVEY_FONT,
                 bg=BG_COLOR, fg=FG_COLOR).pack(anchor="w", padx=20, pady=2)
        v = tk.IntVar(value=0); w_survey_vars.append(v)
        f2 = tk.Frame(frame_wordle_survey, bg=BG_COLOR); f2.pack(anchor="w", padx=40)
        for val in range(1,6):
            tk.Radiobutton(f2, text=str(val), variable=v, value=val,
                           font=ENTRY_FONT, bg=BG_COLOR, fg=FG_COLOR,
                           selectcolor=ACCENT_COLOR).pack(side="left")
    tk.Button(frame_wordle_survey, text="Submit Survey", font=BUTTON_FONT,
              bg=ACCENT_COLOR, fg="white",
              command=w_submit_survey).pack(pady=20)
    frame_wordle_survey.tkraise()

def w_submit_survey():
    for v in w_survey_vars:
        if v.get()==0:
            messagebox.showwarning("Incomplete","Answer all questions."); return
    w_current_puzzle_data["survey"] = {f"Q{i+1}":v.get() for i,v in enumerate(w_survey_vars)}
    w_all_puzzle_data.append(w_current_puzzle_data.copy())
    if w_current_puzzle_index < w_TOTAL_PUZZLES:
        w_load_new_puzzle()
    else:
        w_save_data_and_transition()

def w_save_data_and_transition():
    file = "wordle_data.csv"
    hdr = ["ParticipantID","Age","Gender","AI_Tone","Target_Word","solved","attempts","time",
           "guesses","guess_times","hints_count","hint_times"] + [f"Q{i+1}" for i in range(8)]
    mode = 'a' if os.path.exists(file) else 'w'
    with open(file, mode, newline='') as f:
        writer = csv.writer(f)
        if mode=='w': writer.writerow(hdr)
        for d in w_all_puzzle_data:
            row = [
                d["ParticipantID"],d["Age"],d["Gender"],
                d["AI_Tone"],d["Target_Word"],d.get("solved",""),
                d.get("attempts",""),
                round(d.get("end_time",0)-d.get("start_time",0),2),
                ";".join(d.get("guesses",[])),
                ";".join(str(x) for x in d.get("guess_times",[])),
                d.get("hints_count",0),
                ";".join(str(x) for x in d.get("hint_times",[]))
            ] + [d["survey"].get(f"Q{i+1}","") for i in range(8)]
            writer.writerow(row)
    messagebox.showinfo("Saved","Wordle data saved. Starting word puzzle.")
    start_wordpuzzle_experiment()

# ------------------- Word Puzzle Frame -------------------

tk.Label(frame_wordpuzzle_puzzle, text="Word Puzzle", font=TITLE_FONT,
         bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)
wp_label_puzzle_info = tk.Label(frame_wordpuzzle_puzzle, text="", font=LABEL_FONT,
                                bg=BG_COLOR, fg=FG_COLOR); wp_label_puzzle_info.pack()
wp_label_difficulty  = tk.Label(frame_wordpuzzle_puzzle, text="", font=LABEL_FONT,
                                bg=BG_COLOR, fg=FG_COLOR); wp_label_difficulty.pack()
wp_text_hints        = tk.Text(frame_wordpuzzle_puzzle, width=80, height=12, state="disabled",
                                wrap="word", font=ENTRY_FONT, bg=GRID_BG, fg=FG_COLOR)
wp_text_hints.pack(pady=5)
tk.Label(frame_wordpuzzle_puzzle, text="Your Guess:", font=LABEL_FONT,
         bg=BG_COLOR, fg=FG_COLOR).pack()
wp_entry_guess       = tk.Entry(frame_wordpuzzle_puzzle, font=ENTRY_FONT); wp_entry_guess.pack(pady=5)
wp_entry_guess.bind("<Return>", lambda e: wp_check_guess())
wp_btn_submit_guess  = tk.Button(frame_wordpuzzle_puzzle, text="Submit Guess",
                                 font=BUTTON_FONT, bg=ACCENT_COLOR, fg="white"); wp_btn_submit_guess.pack(pady=5)
wp_btn_give_up       = tk.Button(frame_wordpuzzle_puzzle, text="Give Up",
                                 font=BUTTON_FONT, bg=ACCENT_COLOR, fg="white"); wp_btn_give_up.pack(pady=5)
wp_btn_continue      = tk.Button(frame_wordpuzzle_puzzle, text="Continue",
                                 font=BUTTON_FONT, bg=ACCENT_COLOR, fg="white")

# ------------------- Word Puzzle Functions -------------------

def start_wordpuzzle_experiment():
    global wp_current_puzzle_index, wp_results
    wp_current_puzzle_index = 0; wp_results = []
    wp_show_puzzle(0)

def wp_show_puzzle(index):
    global wp_current_puzzle_index, wp_current_answer, wp_current_emotion
    global wp_current_guesses, wp_current_hints, wp_hint_count, wp_start_time, wp_mentioned_last_guess
    p = puzzles[index]
    wp_current_answer       = p["answer"]
    wp_current_emotion      = p["emotion"]
    wp_hint_count           = 0
    wp_current_guesses      = []
    wp_current_hints        = []
    wp_mentioned_last_guess = False
    wp_label_puzzle_info.config(text=f"Puzzle {index+1}/{len(puzzles)} – {wp_current_emotion}")
    wp_label_difficulty.config(text=f"Difficulty: {p['difficulty']}")
    wp_text_hints.config(state="normal"); wp_text_hints.delete("1.0",tk.END)
    wp_text_hints.insert(tk.END,"Initial hint: "+p["clue"]+"\n"); wp_text_hints.config(state="disabled")
    wp_entry_guess.delete(0,tk.END); wp_entry_guess.focus_set()
    wp_btn_submit_guess.config(state="normal",command=wp_check_guess)
    wp_btn_give_up.config(state="normal",command=wp_give_up)
    wp_btn_continue.pack_forget()
    wp_start_time = time.time()
    frame_wordpuzzle_puzzle.tkraise()

def wp_check_guess():
    global wp_hint_count, wp_mentioned_last_guess

    g = wp_entry_guess.get().strip()
    wp_entry_guess.delete(0,tk.END)
    if not g: return

    wp_current_guesses.append(
        f"{g}" + ("(Accurate)" if g.lower() == wp_current_answer.lower() else "(Inaccurate)")
    )

    if g.lower() == wp_current_answer.lower():
        elapsed = time.time() - wp_start_time
        wp_results.append({
            "puzzle": wp_current_puzzle_index+1,
            "emotion": wp_current_emotion,
            "hints_used": wp_hint_count,
            "time": round(elapsed,2),
            "gave_up": False,
            "guesses": wp_current_guesses
        })
        wp_text_hints.config(state="normal")
        wp_text_hints.insert(tk.END, f"\nCorrect! The answer is '{wp_current_answer}'.\n")
        wp_text_hints.config(state="disabled")
        wp_btn_submit_guess.config(state="disabled")
        wp_btn_give_up.config(state="disabled")
        wp_btn_continue.config(command=wp_show_survey)
        wp_btn_continue.pack(pady=10)
        return

    wp_hint_count += 1

    if not wp_mentioned_last_guess:
        last_clean = wp_current_guesses[-1].replace("(Inaccurate)","")
        if wp_current_emotion == "Enthusiastic":
            mention = f"Awesome attempt at '{last_clean}', but it's not correct. "
        elif wp_current_emotion == "Neutral":
            mention = f"Your last guess '{last_clean}' wasn't correct. "
        else:
            mention = f"Oh, your guess '{last_clean}' missed the mark. "
        wp_mentioned_last_guess = True
    else:
        mention = ""

    tmpl = EMOTIONAL_TONES[wp_current_emotion]
    tmpl = tmpl.replace("five-letter", f"{len(wp_current_answer)}-letter")
    base = tmpl.format(answer=wp_current_answer)
    prev = "; ".join(wp_current_guesses)
    lvl = adaptive_hinter.select_level(len(wp_current_guesses), time.time() - wp_start_time)
    prompt = adaptive_hinter.build_prompt(mention + base + " Previous guesses: " + prev + ".", lvl)

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"system","content":prompt}],
            max_tokens=120, temperature=0.7
        )
        hint = resp.choices[0].message.content.strip()
    except Exception as e:
        hint = f"[Hint error: {e}]"

    wp_current_hints.append(hint)
    wp_text_hints.config(state="normal")
    wp_text_hints.insert(tk.END, f"Hint {wp_hint_count}: {hint}\n")
    wp_text_hints.config(state="disabled")

    threading.Thread(
        target=lambda: polly_play(EmotionManager.ssml(hint)),
        daemon=True
    ).start()

    dlg = tk.Toplevel(root)
    dlg.title(f"{wp_current_emotion} Hint")
    EmotionManager.theme(dlg, wp_current_emotion)
    tk.Label(
        dlg, text=hint, font=ENTRY_FONT, fg=FG_COLOR,
        bg=EmotionManager.COLORS[wp_current_emotion], wraplength=400
    ).pack(padx=20,pady=20)

    def on_close():
        if current_sound:
            current_sound.stop()
        dlg.destroy()

    tk.Button(dlg, text="OK", command=on_close,
              font=BUTTON_FONT, bg=ACCENT_COLOR, fg="white").pack(pady=(0,20))
    dlg.protocol("WM_DELETE_WINDOW", on_close)

    dlg.update_idletasks()
    dw, dh = dlg.winfo_width(), dlg.winfo_height()
    x = root.winfo_x() + (root.winfo_width()-dw)//2
    y = root.winfo_y() + (root.winfo_height()-dh)//2
    dlg.geometry(f"{dw}x{dh}+{x}+{y}")
    dlg.transient(root); dlg.grab_set(); root.wait_window(dlg)


def wp_give_up():
    wp_btn_submit_guess.config(state="disabled")
    wp_btn_give_up.config(state="disabled")

    prompt = TONE_GIVEUP_PROMPTS[wp_current_emotion].format(answer=wp_current_answer)
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"system","content":prompt}],
            max_tokens=100, temperature=0.5
        )
        remark = resp.choices[0].message.content.strip()
    except Exception as e:
        remark = f"[Error revealing answer: {e}]"

    wp_text_hints.config(state="normal")
    wp_text_hints.insert(tk.END, f"\n{remark}\n")
    wp_text_hints.config(state="disabled")

    # start Polly reading
    threading.Thread(
        target=lambda: polly_play(EmotionManager.ssml(remark)),
        daemon=True
    ).start()

    elapsed = time.time() - wp_start_time
    wp_results.append({
        "puzzle": wp_current_puzzle_index+1,
        "emotion": wp_current_emotion,
        "hints_used": wp_hint_count,
        "time": round(elapsed,2),
        "gave_up": True,
        "guesses": wp_current_guesses
    })

    # wrap the continue action so it first stops Polly
    def on_continue():
        if current_sound:
            current_sound.stop()
        wp_show_survey()

    wp_btn_continue.config(command=on_continue)
    wp_btn_continue.pack(pady=10)


def wp_show_survey():
    for w in frame_wordpuzzle_survey.winfo_children(): w.destroy()
    tk.Label(frame_wordpuzzle_survey, text=f"Survey: {wp_current_emotion} Tone",
             font=TITLE_FONT, bg=BG_COLOR, fg=FG_COLOR).pack(pady=10)
    global wp_survey_vars
    wp_survey_vars=[]
    qs=[q.format(tone=wp_current_emotion) for q in SURVEY_TEMPLATE]
    for q in qs:
        tk.Label(frame_wordpuzzle_survey, text=q, font=SURVEY_FONT,
                 bg=BG_COLOR, fg=FG_COLOR).pack(anchor="w",padx=20,pady=2)
        v=tk.IntVar(value=0); wp_survey_vars.append(v)
        opts=tk.Frame(frame_wordpuzzle_survey,bg=BG_COLOR); opts.pack(anchor="w",padx=40)
        for val in range(1,6):
            tk.Radiobutton(opts, text=str(val), variable=v, value=val,
                           font=ENTRY_FONT, bg=BG_COLOR, fg=FG_COLOR,
                           selectcolor=ACCENT_COLOR).pack(side="left")
    tk.Button(frame_wordpuzzle_survey, text="Submit Survey", font=BUTTON_FONT,
              bg=ACCENT_COLOR, fg="white", command=wp_submit_survey).pack(pady=20)
    frame_wordpuzzle_survey.tkraise()

def wp_submit_survey():
    for v in wp_survey_vars:
        if v.get()==0:
            messagebox.showwarning("Incomplete","Answer all questions."); return
    wp_results[-1]["survey"] = {f"Q{i+1}":v.get() for i,v in enumerate(wp_survey_vars)}
    global wp_current_puzzle_index
    wp_current_puzzle_index += 1
    if wp_current_puzzle_index < len(puzzles):
        wp_show_puzzle(wp_current_puzzle_index)
    else:
        wp_save_and_exit()

def wp_save_and_exit():
    file="word_puzzle_data.csv"
    hdr=["ParticipantID","Age","Gender","Puzzle_Emotion","Puzzle_HintsUsed","Puzzle_Time","Gave_Up","Puzzle_Guesses"]+[f"Q{i+1}" for i in range(8)]
    mode='a' if os.path.exists(file) else 'w'
    with open(file, mode, newline='') as f:
        w = csv.writer(f)
        if mode=='w': w.writerow(hdr)
        for r in wp_results:
            row = [
                participant_info["ParticipantID"],participant_info["Age"],participant_info["Gender"],
                r["emotion"],r["hints_used"],r["time"],r["gave_up"],";".join(r["guesses"])
            ] + [r["survey"].get(f"Q{i+1}","") for i in range(8)]
            w.writerow(row)
    messagebox.showinfo("Done","Thank you for participating!")
    root.destroy()

# ------------------- Hook up Buttons -------------------

w_btn_submit.config(command=w_submit_guess)
w_btn_hint.config(command=w_get_hint)
w_btn_next.config(command=w_show_survey)
wp_btn_submit_guess.config(command=wp_check_guess)
wp_btn_give_up.config(command=wp_give_up)

# ------------------- Start GUI -------------------

frame_info.tkraise()
root.mainloop()
