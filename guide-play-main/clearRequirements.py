# Read the requirements.txt file
with open('requirements.txt', 'r') as file:
    lines = file.readlines()

# Remove duplicates
lines = list(set(lines))

# Write the updated requirements.txt file
with open('requirements_.txt', 'w') as file:
    file.writelines(lines)
