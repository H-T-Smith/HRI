import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ------------------- Load Data -------------------
csv_file = "word_puzzle_data.csv"  # Ensure this file is in the same directory
df = pd.read_csv(csv_file)

print("Data Snapshot:")
print(df.head())

# ------------------- Data Cleaning -------------------
# Convert specific performance columns to numeric
numeric_cols = ["Puzzle_HintsUsed", "Puzzle_Time(sec)"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Convert 'Gave_Up' to boolean if not already
if df["Gave_Up"].dtype != bool:
    df["Gave_Up"] = df["Gave_Up"].astype(bool)

# Convert survey columns to numeric
survey_cols = [col for col in df.columns if col.startswith("Survey_Q")]
for col in survey_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# ------------------- Descriptive Statistics -------------------
print("\nOverall Descriptive Statistics (Performance Metrics):")
print(df[numeric_cols].describe())

# ------------------- Group Analysis by Puzzle Emotion -------------------
group_emotion = df.groupby("Puzzle_Emotion").agg({
    "Puzzle_HintsUsed": ["mean", "std"],
    "Puzzle_Time(sec)": ["mean", "std"]
}).reset_index()
group_emotion.columns = ["Puzzle_Emotion", "Avg_HintsUsed", "Std_HintsUsed", "Avg_Time", "Std_Time"]

print("\nPerformance Metrics by Puzzle Emotion:")
print(group_emotion)

# ------------------- Group Analysis by Participant -------------------
group_participant = df.groupby("ParticipantID").agg({
    "Puzzle_HintsUsed": ["mean", "std"],
    "Puzzle_Time(sec)": ["mean", "std"]
}).reset_index()
group_participant.columns = ["ParticipantID", "Avg_HintsUsed", "Std_HintsUsed", "Avg_Time", "Std_Time"]

print("\nPerformance Metrics by Participant:")
print(group_participant)

# ------------------- Survey Analysis -------------------
survey_summary = df.groupby("Puzzle_Emotion")[survey_cols].mean().reset_index()
print("\nSurvey Summary (Average Ratings by Puzzle Emotion):")
print(survey_summary)

# ------------------- Puzzle Guesses Analysis -------------------
# Here, we assume Puzzle_Guesses is a semicolon-separated string
# Let's compute the average number of guesses per puzzle and proportion of accurate guesses.
def parse_guesses(guess_str):
    if pd.isna(guess_str):
        return []
    return guess_str.split(";")

df["Num_Guesses"] = df["Puzzle_Guesses"].apply(lambda x: len(parse_guesses(x)))
df["Accurate_Ratio"] = df["Puzzle_Guesses"].apply(
    lambda x: np.mean([1 if "Accurate" in g else 0 for g in parse_guesses(x)]) if x and isinstance(x, str) else np.nan
)

print("\nGuess Analysis:")
print(df[["Puzzle_Guesses", "Num_Guesses", "Accurate_Ratio"]].head())

# ------------------- Plotting Functions -------------------
def bar_chart(x, y, title, xlabel, ylabel, color="skyblue"):
    plt.figure()
    plt.bar(x, y, color=color)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.show()

# ------------------- Bar Charts: Performance Metrics by Puzzle Emotion -------------------
bar_chart(group_emotion["Puzzle_Emotion"], group_emotion["Avg_HintsUsed"],
          "Average Hints Used by Puzzle Emotion", "Puzzle Emotion", "Avg Hints Used")
          
bar_chart(group_emotion["Puzzle_Emotion"], group_emotion["Avg_Time"],
          "Average Puzzle Time by Puzzle Emotion", "Puzzle Emotion", "Avg Time (sec)")

# Bar chart: Average Number of Guesses by Puzzle Emotion
group_guesses = df.groupby("Puzzle_Emotion")["Num_Guesses"].mean().reset_index()
bar_chart(group_guesses["Puzzle_Emotion"], group_guesses["Num_Guesses"],
          "Average Number of Guesses by Puzzle Emotion", "Puzzle Emotion", "Avg Number of Guesses", color="lightgreen")

# Bar chart: Average Accurate Ratio by Puzzle Emotion
group_acc = df.groupby("Puzzle_Emotion")["Accurate_Ratio"].mean().reset_index()
bar_chart(group_acc["Puzzle_Emotion"], group_acc["Accurate_Ratio"],
          "Average Ratio of Accurate Guesses by Puzzle Emotion", "Puzzle Emotion", "Accurate Ratio", color="orchid")

# ------------------- Histograms -------------------
plt.figure()
plt.hist(df["Puzzle_HintsUsed"].dropna(), bins=range(0, int(df["Puzzle_HintsUsed"].max())+2), edgecolor="black")
plt.title("Distribution of Puzzle Hints Used")
plt.xlabel("Hints Used")
plt.ylabel("Frequency")
plt.show()

plt.figure()
plt.hist(df["Puzzle_Time(sec)"].dropna(), bins=10, edgecolor="black")
plt.title("Distribution of Puzzle Time")
plt.xlabel("Time (sec)")
plt.ylabel("Frequency")
plt.show()

plt.figure()
plt.hist(df["Num_Guesses"].dropna(), bins=range(1, int(df["Num_Guesses"].max())+2), edgecolor="black")
plt.title("Distribution of Number of Guesses")
plt.xlabel("Number of Guesses")
plt.ylabel("Frequency")
plt.show()

# ------------------- Boxplots by Puzzle Emotion -------------------
unique_emotions = list(df["Puzzle_Emotion"].unique())
plt.figure()
for emotion in unique_emotions:
    data = df[df["Puzzle_Emotion"] == emotion]["Puzzle_HintsUsed"].dropna()
    plt.boxplot(data, positions=[unique_emotions.index(emotion)], widths=0.6)
plt.xticks(range(len(unique_emotions)), unique_emotions)
plt.title("Boxplot of Hints Used by Puzzle Emotion")
plt.xlabel("Puzzle Emotion")
plt.ylabel("Hints Used")
plt.show()

plt.figure()
for emotion in unique_emotions:
    data = df[df["Puzzle_Emotion"] == emotion]["Puzzle_Time(sec)"].dropna()
    plt.boxplot(data, positions=[unique_emotions.index(emotion)], widths=0.6)
plt.xticks(range(len(unique_emotions)), unique_emotions)
plt.title("Boxplot of Puzzle Time by Puzzle Emotion")
plt.xlabel("Puzzle Emotion")
plt.ylabel("Time (sec)")
plt.show()

# ------------------- Survey Bar Charts -------------------
for q in survey_cols:
    tone_avg = df.groupby("Puzzle_Emotion")[q].mean().reset_index()
    plt.figure()
    plt.bar(tone_avg["Puzzle_Emotion"], tone_avg[q], color="salmon")
    plt.title(f"Average {q} Rating by Puzzle Emotion")
    plt.xlabel("Puzzle Emotion")
    plt.ylabel("Average Rating")
    plt.ylim(1, 5)
    plt.show()

# ------------------- Correlation Analysis -------------------
corr_cols = numeric_cols + ["Num_Guesses"] + survey_cols
corr_matrix = df[corr_cols].corr()
print("\nCorrelation Matrix:")
print(corr_matrix)

plt.figure(figsize=(8, 6))
plt.imshow(corr_matrix, cmap="viridis", interpolation="none")
plt.colorbar()
plt.xticks(range(len(corr_cols)), corr_cols, rotation=45, ha="right")
plt.yticks(range(len(corr_cols)), corr_cols)
plt.title("Correlation Matrix Heatmap")
plt.tight_layout()
plt.show()
