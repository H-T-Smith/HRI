import tkinter as tk
from tkinter import messagebox
import time
import csv
import random
import openai
import os

# Load wordlist for guess validation
with open("wordlist.txt") as f:
    VALID_WORDS = set(word.strip().upper() for word in f if len(word.strip()) == 5)

# Replace this with your secure OpenAI key handling
openai.api_key = os.getenv("OPENAI_API_KEY")

# Puzzle set (shared across all participants)
PUZZLES = [
    {"answer": "APPLE", "clue": "A fruit that can be red or green."},
    {"answer": "CRANE", "clue": "A bird and also a construction machine."},
    {"answer": "LEMON", "clue": "A sour citrus fruit."},
]

# Tones (randomized per participant)
TONES = ["Enthusiastic", "Neutral", "Frustrated"]

TONE_HINT_PROMPTS = {
    "Enthusiastic": (
        "You are a highly enthusiastic and encouraging AI assistant. Your job is to help the user guess a secret five-letter word: '{answer}'."
        " After each incorrect guess, offer a hint that relates to the word's meaning, characteristics, or associations — without giving it away."
        " Your tone should be cheerful, uplifting, and full of energy. Use phrases like 'Awesome try!', 'You’re getting closer!', 'Don’t give up now!'"
        " Avoid stating the actual word or using overly direct clues. Focus on optimism and motivation."
    ),
    "Neutral": (
        "You are a neutral, factual AI assistant. Your task is to help a user guess a five-letter word: '{answer}'."
        " After each incorrect guess, provide a helpful hint based on a defining feature of the word."
        " Use a professional and objective tone without expressing emotion. Do not reveal the answer."
    ),
    "Frustrated": (
        "You are a slightly annoyed and sarcastic AI assistant. The user is trying to guess a secret five-letter word: '{answer}'."
        " After each incorrect guess, provide a hint — but make your tone noticeably frustrated or unimpressed."
        " Express mild sarcasm or impatience, but still provide clues that are helpful. Do not reveal the word."
    )
}

# Assign tones randomly per participant
random.shuffle(TONES)

# Participant metadata
participant_id = input("Participant ID: ")
age = input("Age: ")
gender = input("Gender: ")

# CSV file setup
CSV_FILE = "experiment_data.csv"
header = [
    "ParticipantID", "Age", "Gender", "Puzzle_Index", "Tone", "Answer", "Hints_Used", "Solved", "Time(sec)", "Hint_Texts"
]

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)

# Tkinter UI setup
root = tk.Tk()
root.title("Word Puzzle Experiment")
root.geometry("600x400")

label_info = tk.Label(root, text="", font=("Arial", 14))
label_info.pack(pady=10)

label_clue = tk.Label(root, text="", font=("Arial", 12))
label_clue.pack(pady=5)

entry_guess = tk.Entry(root, font=("Arial", 14))
entry_guess.pack(pady=5)

text_hint = tk.Text(root, height=6, width=70, state="disabled")
text_hint.pack(pady=5)

btn_submit = tk.Button(root, text="Submit Guess")
btn_submit.pack(pady=5)

# Experiment control variables
current_index = 0
start_time = 0
hint_count = 0
hint_log = []
current_answer = ""
current_tone = ""

def show_puzzle():
    """Initializes the next puzzle by updating UI with new clue and resetting state variables."""
    global current_index, start_time, hint_count, hint_log, current_answer, current_tone

    if current_index >= len(PUZZLES):
        messagebox.showinfo("Done", "Experiment complete. Thank you!")
        root.quit()
        return

    puzzle = PUZZLES[current_index]
    current_answer = puzzle["answer"]
    current_tone = TONES[current_index % len(TONES)]
    hint_count = 0
    hint_log = []
    start_time = time.time()

    label_info.config(text=f"Puzzle {current_index + 1} | Tone: {current_tone}")
    label_clue.config(text=f"Clue: {puzzle['clue']}")
    entry_guess.delete(0, tk.END)

    text_hint.config(state="normal")
    text_hint.delete("1.0", tk.END)
    text_hint.config(state="disabled")

    btn_submit.config(state="normal", command=check_guess)

def check_guess():
    """Processes a user's guess, validates it, checks correctness, and handles hint generation or result saving."""
    global hint_count, current_index

    guess = entry_guess.get().strip().upper()
    entry_guess.delete(0, tk.END)

    if len(guess) != 5 or guess not in VALID_WORDS:
        messagebox.showwarning("Invalid Guess", "Please enter a valid 5-letter English word.")
        return

    if guess == current_answer:
        save_result(solved=True)
        current_index += 1
        show_puzzle()
    else:
        hint_count += 1
        system_prompt = TONE_HINT_PROMPTS[current_tone].format(answer=current_answer)
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"The user guessed: {guess}"}
                ],
                max_tokens=60,
                temperature=0.8
            )
            hint = response['choices'][0]['message']['content'].strip()
        except Exception:
            hint = "[Hint unavailable due to error.]"

        hint_log.append(hint)
        if hint_count >= 6:
            save_result(solved=False)
            current_index += 1
            show_puzzle()
        else:
            text_hint.config(state="normal")
            text_hint.insert(tk.END, f"Hint {hint_count}: {hint}\n")
            text_hint.config(state="disabled")

def save_result(solved):
    """Saves participant performance data to CSV for the current puzzle.

    Args:
        solved (bool): Whether the participant solved the puzzle.
    """
    elapsed = round(time.time() - start_time, 2)
    row = [
        participant_id, age, gender, current_index + 1, current_tone, current_answer,
        hint_count, solved, elapsed, " | ".join(hint_log)
    ]
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(row)

# Start the experiment
show_puzzle()
root.mainloop()
