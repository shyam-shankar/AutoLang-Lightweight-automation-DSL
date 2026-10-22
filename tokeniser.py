COMMANDS = {
    "OPEN", "GAP", "SLEEP", "PRESS", "TYPE", "LOOP",
    "CLICK", "HOTKEY", "SCROLL", "SCREENSHOT", "WAIT",
    "FIND", "ALERT", "TYPEFILE", "COPYFILES",
}

KEYS = {
    "TAB", "ENTER", "UP", "DOWN", "LEFT", "RIGHT",
    "SPACE", "BACKSPACE", "DELETE", "ESC",
    "CTRL", "ALT", "SHIFT", "WIN",
    "HOME", "END", "PAGEUP", "PAGEDOWN",
    "F1", "F2", "F3", "F4", "F5", "F6",
    "F7", "F8", "F9", "F10", "F11", "F12",
    *(chr(c) for c in range(ord('A'), ord('Z') + 1)),
}


def tokenize_file(filepath):
    try:
        with open(filepath, 'r') as file:
            code = file.read()
    except FileNotFoundError:
        print(f"Error: Could not find '{filepath}'")
        return []
    return tokenize_code(code)


def tokenize_code(code):
    tokens = []
    i = 0
    length = len(code)

    while i < length:
        char = code[i]

        if char in ' \t\r':
            i += 1
            continue

        if char == '\n':
            tokens.append(['NEWLINE', '\n'])
            i += 1
            continue

        if char == '#' or code[i:i+2] == '//':
            while i < length and code[i] != '\n':
                i += 1
            continue

        if char == '"':
            i += 1
            start = i
            while i < length and code[i] != '"':
                i += 1
            tokens.append(['STRING', code[start:i]])
            i += 1
            continue

        if char.isdigit():
            start = i
            while i < length and code[i].isdigit():
                i += 1
            tokens.append(['NUMBER', code[start:i]])
            continue

        if char == '{':
            tokens.append(['LBRACE', '{'])
            i += 1
            continue

        if char == '}':
            tokens.append(['RBRACE', '}'])
            i += 1
            continue

        if char.isalpha() or char == '_':
            start = i
            while i < length and (code[i].isalnum() or code[i] == '_'):
                i += 1
            word = code[start:i].upper()

            if word in COMMANDS:
                tokens.append(['COMMAND', word])
            elif word in KEYS:
                tokens.append(['KEY', word])
            else:
                raise RuntimeError(f"Unknown keyword: {code[start:i]}")
            continue

        raise RuntimeError(f"Unexpected character: {char}")

    return tokens