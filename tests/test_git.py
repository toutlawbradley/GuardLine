from src.utils.git import get_changed_line_numbers, hunkheader_to_dict, parse_diff

def test_hunkheader_with_comma():
    result = hunkheader_to_dict("@@ -40,2 +40,5 @@")
    assert result == {"old_start": 40, "old_length": 2, "new_start": 40, "new_length": 5}

def test_hunkheader_without_comma():
    result = hunkheader_to_dict("@@ -40 +40 @@")
    assert result == {"old_start": 40, "old_length": 1, "new_start": 40, "new_length": 1}

def test_hunkheader_invalid_format():
    try:
        hunkheader_to_dict("@@ -40,2 +40,5")
        assert False, "Expected ValueError for invalid format"
    except ValueError as e:
        assert str(e) == "Invalid hunk header format: @@ -40,2 +40,5"

def test_hunkheader_with_missing_lengths():
    result = hunkheader_to_dict("@@ -40 +40 @@")
    assert result == {"old_start": 40, "old_length": 1, "new_start": 40, "new_length": 1}

def test_hunkheader_with_zero_lengths():
    result = hunkheader_to_dict("@@ -40,0 +40,0 @@")
    assert result == {"old_start": 40, "old_length": 0, "new_start": 40, "new_length": 0}

def test_hunkheader_with_large_numbers():
    result = hunkheader_to_dict("@@ -1000000,2000000 +3000000,4000000 @@")
    assert result == {"old_start": 1000000, "old_length": 2000000, "new_start": 3000000, "new_length": 4000000}

def test_parse_diff_with_single_file():
    diff_text = """diff --git a/file1.txt b/file1.txt
@@ -1,2 +1,3 @@
-Line 1
+Line 1 modified
+Line 2 added
"""
    files = parse_diff(diff_text)
    assert len(files) == 1
    assert files[0]['old_path'] == 'file1.txt'
    assert files[0]['new_path'] == 'file1.txt'

def test_parse_diff_with_multiple_files():
    diff_text = """diff --git a/file1.txt b/file1.txt
@@ -1,2 +1,3 @@   
-Line 1
+Line 1 modified
diff --git a/file2.txt b/file2.txt
@@ -1,1 +1,2 @@
-Line A
+Line A modified
+Line B added
"""
    files = parse_diff(diff_text)
    assert len(files) == 2
    assert files[0]['old_path'] == 'file1.txt'
    assert files[0]['new_path'] == 'file1.txt'
    assert files[1]['old_path'] == 'file2.txt'
    assert files[1]['new_path'] == 'file2.txt'

def test_parse_diff_with_hunks():
    diff_text = """diff --git a/file1.txt b/file1.txt
@@ -1,2 +1,3 @@
-Line 1
+Line 1 modified    
+Line 2 added
"""
    files = parse_diff(diff_text)
    assert len(files) == 1
    hunks = files[0]['hunks']
    assert len(hunks) == 1
    assert hunks[0]['old_start'] == 1
    assert hunks[0]['old_length'] == 2
    assert hunks[0]['new_start'] == 1
    assert hunks[0]['new_length'] == 3

def test_parse_diff_with_multiple_hunks():
    diff_text = """diff --git a/file1.txt b/file1.txt
@@ -1,2 +1,3 @@
-Line 1
+Line 1 modified
@@ -4,1 +5,2 @@
-Line 4
+Line 4 modified
+Line 5 added
"""
    files = parse_diff(diff_text)
    assert len(files) == 1
    hunks = files[0]['hunks']
    assert len(hunks) == 2
    assert hunks[0]['old_start'] == 1
    assert hunks[0]['old_length'] == 2
    assert hunks[0]['new_start'] == 1
    assert hunks[0]['new_length'] == 3

def test_hunkheader_with_negative_numbers():
    try:
        hunkheader_to_dict("@@ -40,-2 +40,-5 @@")
        assert False, "Expected ValueError for negative numbers"
    except ValueError as e:
        assert str(e) == "Invalid hunk header format: @@ -40,-2 +40,-5 @@"

def test_hunkheader_with_non_integer_values():
    try:
        hunkheader_to_dict("@@ -40,a +40,b @@")
        assert False, "Expected ValueError for non-integer values"
    except ValueError as e:
        assert str(e) == "Invalid hunk header format: @@ -40,a +40,b @@"

def test_parse_diff_with_no_hunks():
    diff_text = """diff --git a/file1.txt b/file1.txt
"""
    files = parse_diff(diff_text)
    assert len(files) == 1
    assert files[0]['old_path'] == 'file1.txt'
    assert files[0]['new_path'] == 'file1.txt'
    assert len(files[0]['hunks']) == 0

def test_parse_diff_with_empty_diff():
    diff_text = ""
    files = parse_diff(diff_text)
    assert len(files) == 0

def test_get_changed_line_numbers_with_single_file():
    diff_text = """diff --git a/file1.txt b/file1.txt
@@ -1,2 +1,3 @@
-Line 1
+Line 1 modified
+Line 2 added
"""
    changed_lines = get_changed_line_numbers(diff_text)
    assert len(changed_lines) == 1
    assert 'file1.txt' in changed_lines
    assert changed_lines['file1.txt'] == {1, 2, 3}

def test_get_changed_line_numbers_with_multiple_files():
    diff_text = """diff --git a/file1.txt b/file1.txt
@@ -1,2 +1,3 @@ 
-Line 1
+Line 1 modified
diff --git a/file2.txt b/file2.txt
@@ -1,1 +1,2 @@
-Line A
+Line A modified
+Line B added
"""
    changed_lines = get_changed_line_numbers(diff_text)
    assert len(changed_lines) == 2
    assert 'file1.txt' in changed_lines
    assert 'file2.txt' in changed_lines
    assert changed_lines['file1.txt'] == {1, 2, 3}
    assert changed_lines['file2.txt'] == {1, 2}

def test_get_changed_line_numbers_with_no_changes():
    diff_text = """diff --git a/file1.txt b/file1.txt
"""
    changed_lines = get_changed_line_numbers(diff_text)
    # a file with no hunks still gets an entry, just with an empty set
    assert len(changed_lines) == 1
    assert changed_lines['file1.txt'] == set()