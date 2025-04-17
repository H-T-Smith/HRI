# Word Puzzle Experiment

This project is a controlled human-subject experiment designed to study how AI-simulated emotional tones affect problem-solving and user perception. Participants solve a series of word puzzles while receiving AI-generated hints in one of three emotional tones: **Enthusiastic**, **Neutral**, or **Frustrated**.

## 📋 Overview

- Participants complete **three puzzles**, each with a randomly assigned emotional tone.
- After each incorrect guess, the AI gives one hint per attempt (up to 6 total).
- Guesses must be valid 5-letter words from a Wordle-compatible dictionary.
- A final survey is completed after all three puzzles.

## 🚀 How to Run

1. Clone or download the repository.
2. Ensure `wordlist.txt` (a list of 5-letter uppercase words) is present in the same folder.
3. Install Python 3 and required libraries (from `requirements.txt`):

```bash
pip install -r requirements.txt
```

4. Set your OpenAI API key in your environment:

```bash
export OPENAI_API_KEY=your-key-here
```

5. Run the experiment:

```bash
python word_puzzle.py
```

## 🧠 Files

| File | Purpose |
|------|---------|
| `word_puzzle.py` | The main experiment GUI |
| `wordlist.txt`   | Valid 5-letter English words |
| `experiment_data.csv` | Output data (created automatically) |
| `stats_word_puzzle.py` | Script for analyzing and visualizing results |
| `A_flowchart...png` | Flowchart of the participant flow |

## 🧾 Data Format

Each row in `experiment_data.csv` includes:

- ParticipantID, Age, Gender
- Puzzle index and assigned tone
- Whether the puzzle was solved and how long it took
- How many hints were used
- All hints given (joined as a string)

Example:
```
P01, 20, F, 1, Neutral, APPLE, 4, TRUE, 51.2, "Hint 1 text | Hint 2 text | ..."
```

## 📊 Analysis

Run:

```bash
python stats_word_puzzle.py
```

This will print summary stats and generate:
- Performance metrics grouped by tone
- Survey averages grouped by tone
- Correlation heatmaps
- Distribution histograms and boxplots

## 🧪 Emotional Tone Definitions

The AI will use slightly different phrasing based on tone:
- **Enthusiastic**: Cheerful, motivational (e.g., “Great job! Keep going!”)
- **Neutral**: Factual and direct
- **Frustrated**: Sarcastic or impatient, but still helpful

## 📄 License

MIT License — for academic use only.

## 🙏 Acknowledgments

Project developed for a Human-Robot Interaction research study at Mississippi State University.
