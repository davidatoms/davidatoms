from datetime import datetime
import pytz

def update_readme():
	# Get current time in Mountain Time
	timezone = pytz.timezone('America/Denver')
	current_time = datetime.now(timezone)

	# Format as "Last Updated: DD MM YYYY HH:MM:SS
	timestamp = current_time.strftime('Last Updated: %d %b %Y %H:%M:%S')

	# Read the README
	with open('README.md', 'r') as file:
		content = file.readlines()

	# Update the timestamp line
	for i, line in enumerate(content):
		if 'Last updated --' in line:
			content[i] = timestamp + '\n\n'
			break

	# Write back to README
	with open('README.md', 'w') as file:
		file.writelines(content)

if __name__ == '__main__':
	update_readme()
