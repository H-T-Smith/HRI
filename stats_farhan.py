import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from lifelines import KaplanMeierFitter
from sklearn.cluster import KMeans

# ----------------------------------------------------
# 1. LOAD & PREPROCESS
# ----------------------------------------------------
# Wordle & Puzzle CSVs
wdf = pd.read_csv("Wordle_data.csv")
pdf = pd.read_csv("word_puzzle_data.csv")

# Rename metrics
wdf.rename(columns={"Total_Time": "Total_Time_sec"}, inplace=True)
pdf.rename(columns={
    "Puzzle_HintsUsed": "Hints_Used",
    "Puzzle_Time(sec)": "Puzzle_Time_sec"
}, inplace=True)

# Ensure numeric
for df, cols in [
    (wdf, ["Attempts", "Total_Time_sec", "Hints_Count"]),
    (pdf, ["Hints_Used", "Puzzle_Time_sec"])
]:
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# Identify survey questions
w_survey = [c for c in wdf.columns if c.startswith("Survey_Q")]
p_survey = [c for c in pdf.columns if c.startswith("Survey_Q")]

# Impute missing survey values with median
for df, survey_cols in [(wdf, w_survey), (pdf, p_survey)]:
    for c in survey_cols:
        m = df[c].median(skipna=True)
        if not np.isnan(m):
            df[c].fillna(m, inplace=True)

# ----------------------------------------------------
# 2. DESCRIPTIVE SUMMARIES
# ----------------------------------------------------
def describe_by(df, by, metrics):
    grp = df.groupby(by)[metrics].agg(["mean","std","count"]).round(2)
    print(f"\n=== {metrics} by {by} ===\n{grp}")
    return grp

print("\n--- Wordle Descriptives ---")
w_perf = describe_by(wdf, "AI_Tone", ["Attempts","Total_Time_sec","Hints_Count"])
print("\n--- Puzzle Descriptives ---")
p_perf = describe_by(pdf, "Puzzle_Emotion", ["Hints_Used","Puzzle_Time_sec"])

# ----------------------------------------------------
# 3. SIMPLE ANALYSIS (Original scripts)
# ----------------------------------------------------
# Wordle original: by Tone, by Participant, survey averages, bar charts, histograms, boxplots, correlations
print("\n--- Wordle Original Analysis ---")
# Overall stats
print("\nOverall Descriptive Statistics:")
print(wdf[["Attempts","Total_Time_sec","Hints_Count"]].describe())

# By AI Tone
group_tone = wdf.groupby("AI_Tone").agg({
    "Attempts":["mean","std"],
    "Total_Time_sec":["mean","std"],
    "Hints_Count":["mean","std"]
}).reset_index()
group_tone.columns = ["AI_Tone","Avg_Attempts","Std_Attempts","Avg_Time","Std_Time","Avg_Hints","Std_Hints"]
print("\nPerformance by AI Tone:")
print(group_tone)

# By Participant
group_part_p = wdf.groupby("ParticipantID").agg({
    "Attempts":["mean","std"],
    "Total_Time_sec":["mean","std"],
    "Hints_Count":["mean","std"]
}).reset_index()
group_part_p.columns = ["ParticipantID","Avg_Attempts","Std_Attempts","Avg_Time","Std_Time","Avg_Hints","Std_Hints"]
print("\nPerformance by Participant:")
print(group_part_p)

# Survey summary
survey_cols = w_survey
survey_summary = wdf.groupby("AI_Tone")[survey_cols].mean().reset_index()
print("\nSurvey Summary by AI Tone:")
print(survey_summary)

# Plots
def bar_chart(x,y,title,xl,yl,color="skyblue"):
    plt.figure(); plt.bar(x,y,color=color)
    plt.title(title); plt.xlabel(xl); plt.ylabel(yl)
    plt.show()

bar_chart(group_tone["AI_Tone"],group_tone["Avg_Attempts"],
          "Avg Attempts by Tone","Tone","Attempts")
bar_chart(group_tone["AI_Tone"],group_tone["Avg_Time"],
          "Avg Time by Tone","Tone","Time (sec)")
bar_chart(group_tone["AI_Tone"],group_tone["Avg_Hints"],
          "Avg Hints by Tone","Tone","Hints")

# Histograms
plt.figure(); plt.hist(wdf["Attempts"].dropna(),bins=range(1,int(wdf["Attempts"].max())+2),edgecolor="black")
plt.title("Attempts Distribution"); plt.xlabel("Attempts"); plt.ylabel("Freq"); plt.show()

plt.figure(); plt.hist(wdf["Total_Time_sec"].dropna(),bins=10,edgecolor="black")
plt.title("Total Time Distribution"); plt.xlabel("Time (sec)"); plt.ylabel("Freq"); plt.show()

plt.figure(); plt.hist(wdf["Hints_Count"].dropna(),bins=range(0,int(wdf["Hints_Count"].max())+2),edgecolor="black")
plt.title("Hints Count Distribution"); plt.xlabel("Hints"); plt.ylabel("Freq"); plt.show()

# Boxplots
tones = wdf["AI_Tone"].unique().tolist()
plt.figure()
for i,t in enumerate(tones):
    data = wdf[wdf["AI_Tone"]==t]["Attempts"].dropna()
    plt.boxplot(data, positions=[i], widths=0.6)
plt.xticks(range(len(tones)),tones); plt.title("Attempts by Tone"); plt.show()

plt.figure()
for i,t in enumerate(tones):
    data = wdf[wdf["AI_Tone"]==t]["Total_Time_sec"].dropna()
    plt.boxplot(data, positions=[i], widths=0.6)
plt.xticks(range(len(tones)),tones); plt.title("Time by Tone"); plt.show()

plt.figure()
for i,t in enumerate(tones):
    data = wdf[wdf["AI_Tone"]==t]["Hints_Count"].dropna()
    plt.boxplot(data, positions=[i], widths=0.6)
plt.xticks(range(len(tones)),tones); plt.title("Hints by Tone"); plt.show()

# Correlation heatmap
corr_cols = ["Attempts","Total_Time_sec","Hints_Count"]+survey_cols
cm = wdf[corr_cols].corr()
plt.figure(figsize=(6,5)); plt.imshow(cm, cmap="viridis"); plt.colorbar()
plt.xticks(range(len(corr_cols)),corr_cols,rotation=45,ha="right")
plt.yticks(range(len(corr_cols)),corr_cols); plt.title("Wordle Corr"); plt.tight_layout(); plt.show()

# Puzzle original
print("\n--- Puzzle Original Analysis ---")
# Data cleaning done above
# Descriptives
print("\nOverall Puzzle Stats:")
print(pdf[["Hints_Used","Puzzle_Time_sec"]].describe())

# By Emotion
group_em = pdf.groupby("Puzzle_Emotion").agg({
    "Hints_Used":["mean","std"],
    "Puzzle_Time_sec":["mean","std"]
}).reset_index()
group_em.columns=["Puzzle_Emotion","Avg_Hints","Std_Hints","Avg_Time","Std_Time"]
print("\nPuzzle by Emotion:")
print(group_em)

# By Participant
gp = pdf.groupby("ParticipantID").agg({
    "Hints_Used":["mean","std"],
    "Puzzle_Time_sec":["mean","std"]
}).reset_index()
gp.columns=["ParticipantID","Avg_Hints","Std_Hints","Avg_Time","Std_Time"]
print("\nPuzzle by Participant:")
print(gp)

# Survey summary
survey_summary_p = pdf.groupby("Puzzle_Emotion")[p_survey].mean().reset_index()
print("\nPuzzle Survey by Emotion:")
print(survey_summary_p)

# Guesses analysis
def parse_guesses(s): return [] if pd.isna(s) else s.split(";")
pdf["Num_Guesses"] = pdf["Puzzle_Guesses"].apply(parse_guesses).apply(len)
pdf["Accurate_Ratio"] = pdf["Puzzle_Guesses"].apply(
    lambda s: np.mean([1 if "Accurate" in g else 0 for g in parse_guesses(s)]) if isinstance(s,str) else np.nan)

print("\nGuess Analysis:")
print(pdf[["Puzzle_Guesses","Num_Guesses","Accurate_Ratio"]].head())

# Puzzle plots
bar_chart(group_em["Puzzle_Emotion"], group_em["Avg_Hints"],
          "Avg Hints by Emotion","Emotion","Hints","lightgreen")
bar_chart(group_em["Puzzle_Emotion"], group_em["Avg_Time"],
          "Avg Time by Emotion","Emotion","Time","orange")

plt.figure(); plt.hist(pdf["Hints_Used"].dropna(),bins=range(0,int(pdf["Hints_Used"].max())+2),edgecolor="black")
plt.title("Puzzle Hints Dist"); plt.show()

plt.figure(); plt.hist(pdf["Puzzle_Time_sec"].dropna(),bins=10,edgecolor="black")
plt.title("Puzzle Time Dist"); plt.show()

plt.figure(); plt.hist(pdf["Num_Guesses"].dropna(),bins=range(1,int(pdf["Num_Guesses"].max())+2),edgecolor="black")
plt.title("Num Guesses Dist"); plt.show()

# Boxplots Puzzle
emos = pdf["Puzzle_Emotion"].unique().tolist()
plt.figure()
for i,e in enumerate(emos):
    data = pdf[pdf["Puzzle_Emotion"]==e]["Hints_Used"].dropna()
    plt.boxplot(data, positions=[i], widths=0.6)
plt.xticks(range(len(emos)),emos); plt.title("Puzzle Hints by Emotion"); plt.show()

plt.figure()
for i,e in enumerate(emos):
    data = pdf[pdf["Puzzle_Emotion"]==e]["Puzzle_Time_sec"].dropna()
    plt.boxplot(data, positions=[i], widths=0.6)
plt.xticks(range(len(emos)),emos); plt.title("Puzzle Time by Emotion"); plt.show()

# Correlation heatmap
corr_cols_p = ["Hints_Used","Puzzle_Time_sec","Num_Guesses"]+p_survey
cm2 = pdf[corr_cols_p].corr()
plt.figure(figsize=(6,5)); plt.imshow(cm2, cmap="viridis"); plt.colorbar()
plt.xticks(range(len(corr_cols_p)),corr_cols_p,rotation=45,ha="right")
plt.yticks(range(len(corr_cols_p)),corr_cols_p); plt.title("Puzzle Corr"); plt.tight_layout(); plt.show()

# ----------------------------------------------------
# 4. ANOVA, POST-HOC & BOXPLOTS (Advanced)
# ----------------------------------------------------
print("\n--- Advanced ANOVA & Tukey ---")
def anova_tukey_box(df, dv, iv):
    print(f"\nANOVA {dv} ~ {iv}")
    m = ols(f"{dv} ~ C({iv})", df).fit()
    print(sm.stats.anova_lm(m, typ=2))
    t = pairwise_tukeyhsd(df[dv], df[iv])
    print(t)
    gr = df[iv].unique()
    data = [df[df[iv]==g][dv].dropna() for g in gr]
    plt.figure(); plt.boxplot(data,labels=gr); plt.title(f"{dv} by {iv}") 
    plt.show()

anova_tukey_box(wdf, "Attempts","AI_Tone")
anova_tukey_box(wdf, "Total_Time_sec","AI_Tone")
anova_tukey_box(pdf,"Hints_Used","Puzzle_Emotion")
anova_tukey_box(pdf,"Puzzle_Time_sec","Puzzle_Emotion")

# ----------------------------------------------------
# 5. SURVEY→ PERFORMANCE REGRESSION (Advanced)
# ----------------------------------------------------
print("\n--- Survey→Performance Regression ---")
def survey_reg(df, perf, survey_cols):
    df2 = df[[perf]+survey_cols].dropna()
    if df2.empty: 
        print(f"Skipping {perf} regression—no data"); return
    df2["mean_s"] = df2[survey_cols].mean(axis=1)
    X = sm.add_constant(df2["mean_s"]); y=df2[perf]
    mod=sm.OLS(y,X).fit(); print(mod.summary())
    plt.figure()
    plt.scatter(df2["mean_s"],y,alpha=0.6)
    xs=np.linspace(df2["mean_s"].min(),df2["mean_s"].max(),100)
    plt.plot(xs,mod.predict(sm.add_constant(xs)),'r--'); plt.title(f"{perf} vs survey mean"); plt.show()

survey_reg(wdf,"Attempts",w_survey)
survey_reg(wdf,"Total_Time_sec",w_survey)
survey_reg(pdf,"Hints_Used",p_survey)
survey_reg(pdf,"Puzzle_Time_sec",p_survey)

# ----------------------------------------------------
# 6. RELIABILITY & CLUSTERING (Advanced)
# ----------------------------------------------------
print("\n--- Reliability & Clustering ---")
def alpha(df, items):
    k=len(items); vs=df[items].var(ddof=1).sum(); tv=df[items].sum(axis=1).var(ddof=1)
    return (k/(k-1))*(1-vs/tv)

print("Cronbach α Wordle:",alpha(wdf,w_survey).round(2))
print("Cronbach α Puzzle:",alpha(pdf,p_survey).round(2))

def cluster(df,pid,feats):
    agg=df.groupby(pid)[feats].mean().dropna()
    n=agg.shape[0]; k=min(3,n) if n>=2 else 0
    if k<2:
        print(f"Skip clustering {pid}, n={n}")
        return
    km=KMeans(n_clusters=k,random_state=0,n_init=10).fit(agg)
    agg["cluster"]=km.labels_; print(agg.head())

cluster(wdf,"ParticipantID",["Attempts","Total_Time_sec","Hints_Count"])
cluster(pdf,"ParticipantID",["Hints_Used","Puzzle_Time_sec"])

# ----------------------------------------------------
# 7. SURVIVAL ANALYSIS (Advanced)
# ----------------------------------------------------
print("\n--- Survival Analysis ---")
solcol = next((c for c in wdf.columns if c.lower()=="solved"), None)
if solcol:
    kmf=KaplanMeierFitter(); T=wdf["Total_Time_sec"]; E=wdf[solcol].astype(int)
    kmf.fit(T,event_observed=E,label="Solve Time")
    ax=kmf.plot_survival_function(); ax.set_xlabel("Time (sec)"); plt.show()
else:
    print("No 'solved' column—skip survival")
