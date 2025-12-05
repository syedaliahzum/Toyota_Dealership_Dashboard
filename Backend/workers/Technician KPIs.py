import pandas as pd

# Load the dataset
df = pd.read_csv('D:/Toyota/csv_files/daily clean.csv')

# ============ TABLE 1: Job counts with Grace and Late status ============
# Part 1: Count the number of jobs per technician
technician_job_count = df['TECHNICIAN_NAME'].value_counts().reset_index()
technician_job_count.columns = ['TECHNICIAN_NAME', 'NUMBER_OF_JOBS']

# Part 2: Create a pivot table to count the number of Grace and Late statuses per technician
status_technician_count = df.groupby(['TECHNICIAN_NAME', 'status']).size().unstack(fill_value=0)

# Merge the job count and status count
table1_result = pd.merge(technician_job_count, status_technician_count, left_on='TECHNICIAN_NAME', right_index=True, how='left')

# Display the result
table1_result = table1_result[['TECHNICIAN_NAME', 'NUMBER_OF_JOBS', 'Grace', 'Late']].fillna(0)

print("TABLE 1: Technician Job Counts with Grace and Late Status")
print("=" * 70)
print(table1_result)
print("\n\n")

# ============ TABLE 2: Efficiency rankings ============
# Normalize status values and create counts per technician
def normalize_status(s: str) -> str:
	if pd.isna(s):
		return ''
	val = str(s).strip().lower()
	# canonical mapping
	if val in ("on time", "on-time", "ontime", "on_time"):
		return 'On-time'
	if val in ("late",):
		return 'Late'
	if val in ("grace",):
		return 'Grace'
	# fallback: title-case the cleaned value
	return s.strip()

status_series = df['status'] if 'status' in df.columns else pd.Series([''] * len(df), index=df.index)
df['status_norm'] = status_series.apply(normalize_status)

status_technician_count_norm = (
	df.groupby(['TECHNICIAN_NAME', 'status_norm']).size().unstack(fill_value=0)
)

# Count jobs per technician again for table 2
technician_job_count2 = df['TECHNICIAN_NAME'].value_counts().reset_index()
technician_job_count2.columns = ['TECHNICIAN_NAME', 'NUMBER_OF_JOBS']

# Merge the job count and status count
table2_result = pd.merge(
	technician_job_count2,
	status_technician_count_norm,
	left_on='TECHNICIAN_NAME',
	right_index=True,
	how='left'
)

# Ensure expected columns exist; reindex will create missing columns filled with 0
expected_status_cols = ['Grace', 'Late', 'On-time']
for col in expected_status_cols:
	if col not in table2_result.columns:
		table2_result[col] = 0

# Combine 'Grace' into 'On-time' per request: On-time_total = On-time + Grace
table2_result['On-time'] = table2_result['On-time'].fillna(0) + table2_result['Grace'].fillna(0)
# Optionally drop the separate 'Grace' column to avoid confusion
if 'Grace' in table2_result.columns:
	table2_result = table2_result.drop(columns=['Grace'])

# Calculate Efficiency % for each technician using combined On-time (includes Grace)
table2_result['Efficiency %'] = (table2_result['On-time'] / table2_result['NUMBER_OF_JOBS']).fillna(0) * 100

# Sort by Efficiency % and rank technicians
table2_result['Position'] = table2_result['Efficiency %'].rank(ascending=False, method='min')

# Sort the result by position and efficiency
table2_result = table2_result.sort_values(by='Position')

# Display the result with rankings
table2_result = table2_result[['Position', 'TECHNICIAN_NAME', 'Efficiency %', 'On-time', 'NUMBER_OF_JOBS']]

print("TABLE 2: Technician Efficiency Rankings")
print("=" * 70)
print(table2_result)