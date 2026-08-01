import re

# Convert a hunk header string to a dictionary.
def hunkheader_to_dict(hunk_header):
    """
    Convert a hunk header string to a dictionary.

    Args:
        hunk_header (str): The hunk header string.

    Returns:
        dict: A dictionary containing the parsed hunk header information.
    """
    pattern = r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@'
    match = re.match(pattern, hunk_header)
    # Check if the hunk header is valid
    if not match:
        raise ValueError(f"Invalid hunk header format: {hunk_header}")
    
    return {
        'old_start': int(match.group(1)),
        'old_length': int(match.group(2)) if match.group(2) else 1,
        'new_start': int(match.group(3)),
        'new_length': int(match.group(4)) if match.group(4) else 1
    }
# Parse a unified diff string into a structured format.
def parse_diff(diff_text):
    """
    Parse a unified diff string into a structured format.

    Args:
        diff_text (str): The unified diff string.

    Returns:
        list: A list of dictionaries, each representing a file's diff.
    """
    files = []
    current_file = None
    current_hunk = None
    # Iterate through each line in the diff text
    for line in diff_text.splitlines():
        if line.startswith('diff --git'):
            if current_file:
                files.append(current_file)
            if current_hunk: 
                current_file['hunks'].append(current_hunk)
                current_hunk = None
            current_file = {
                'old_path': None,
                'new_path': None,
                'hunks': []
            }
            parts = line.split(' ')
            current_file['old_path'] = parts[2][2:]  # Remove the 'a/' prefix
            current_file['new_path'] = parts[3][2:]  # Remove the 'b/' prefix
        elif line.startswith('@@'):
            if current_hunk:
                current_file['hunks'].append(current_hunk)
            current_hunk = hunkheader_to_dict(line)
            current_hunk['lines'] = []
        elif current_hunk is not None:
            current_hunk['lines'].append(line)

    if current_hunk:
        current_file['hunks'].append(current_hunk)
    if current_file:
        files.append(current_file)

    return files  # Return the list of parsed files

def get_changed_line_numbers(diff_text):
    changed_lines = {}
    files = parse_diff(diff_text)

    for file in files:
        file_line_set = set()

        for hunk in file['hunks']:
            hunk_range = range(hunk['new_start'], hunk['new_start'] + hunk['new_length'])
            file_line_set.update(hunk_range)

        changed_lines[file['new_path']] = file_line_set

    return changed_lines
