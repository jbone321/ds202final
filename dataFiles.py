import pandas as pd
import os

def convertToDatetime(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df

# Load and clean participant status logs
participantStatusLogs = []
for i in range(72):
    log = pd.read_csv(f"Datasets/ActivityLogs/ParticipantStatusLogs{i+1}.csv")
    participantStatusLogs.append(log)
dfParticipantStatusLogs = pd.concat(participantStatusLogs, ignore_index=True)
dfParticipantStatusLogs.dropna()  # Drop missing values

# Load attributes
data_folder = "Datasets/Attributes"
files = [f for f in os.listdir(data_folder) if f.endswith('.csv')]
attributes = {file: pd.read_csv(os.path.join(data_folder, file)) for file in files}
for name, df in attributes.items():
    df.dropna()  # Drop missing values

# Convert time columns to datetime in attributes
for name, df in attributes.items():
    timeColumns = [col for col in df.columns if "time" in col.lower()]
    if timeColumns:
        df = convertToDatetime(df, timeColumns)

# Load journals
data_folder = "Datasets/Journals"
files = [f for f in os.listdir(data_folder) if f.endswith('.csv')]
journals = {file: pd.read_csv(os.path.join(data_folder, file)) for file in files}
for name, df in journals.items():
    df.dropna()  # Drop missing values

# Convert time columns to datetime in journals
for name, df in journals.items():
    timeColumns = [col for col in df.columns if "time" in col.lower()]
    if timeColumns:
        df = convertToDatetime(df, timeColumns)

# Clean Participant Status Log timestamp
dfParticipantStatusLogs["timestamp"] = pd.to_datetime(dfParticipantStatusLogs["timestamp"], format="%Y-%m-%dT%H:%M:%SZ")

# Save the processed data as pickle files for faster loading
dfParticipantStatusLogs.to_pickle('processed_participant_status_logs.pkl')
for name, df in attributes.items():
    df.to_pickle(f'processed_{name}_attributes.pkl')
for name, df in journals.items():
    df.to_pickle(f'processed_{name}_journals.pkl')

# Optional: Save specific computed metrics as well (if needed)
householdKidCounts = attributes["Participants.csv"].groupby(['householdSize', 'haveKids']).size().reset_index(name='count')
householdKidCounts.to_pickle('processed_household_kid_counts.pkl')
