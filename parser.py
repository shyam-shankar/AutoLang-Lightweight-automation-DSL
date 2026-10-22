class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def parse(self):
        return self._parse_block(until_rbrace=False)

    def _parse_block(self, until_rbrace=False):
        nodes = []

        while self.pos < len(self.tokens):
            kind, value = self.tokens[self.pos]

            if kind == 'NEWLINE':
                self.pos += 1
                continue

            if kind == 'RBRACE':
                if until_rbrace:
                    self.pos += 1
                    return nodes
                raise SyntaxError("Unexpected '}'")

            if kind == 'COMMAND':
                nodes.append(self._parse_command())
            else:
                raise SyntaxError(
                    f"Expected a command, got {kind} ('{value}')")

        if until_rbrace:
            raise SyntaxError("Expected '}' but reached end of file")

        return nodes

    def _parse_command(self):
        _, cmd = self.tokens[self.pos]
        self.pos += 1

        if cmd == 'OPEN':
            url = self._expect('STRING')
            return {"type": "open", "url": url}

        if cmd in ('GAP', 'SLEEP'):
            duration = int(self._expect('NUMBER'))
            return {"type": "gap", "duration": duration}

        if cmd == 'PRESS':
            key = self._expect('KEY')
            count = 1
            if self._peek() == 'NUMBER':
                count = int(self.tokens[self.pos][1])
                self.pos += 1
            return {"type": "press", "key": key.lower(), "count": count}

        if cmd == 'TYPE':
            text = self._expect('STRING')
            return {"type": "type", "text": text}

        if cmd == 'LOOP':
            count = int(self._expect('NUMBER'))
            self._skip_newlines()
            self._expect('LBRACE')
            body = self._parse_block(until_rbrace=True)
            return {"type": "loop", "count": count, "body": body}

        if cmd == 'CLICK':
            button = 'left'
            if self._peek() == 'KEY':
                button = self.tokens[self.pos][1].lower()
                self.pos += 1
            return {"type": "click", "button": button}

        if cmd == 'HOTKEY':
            keys = []
            while self._peek() == 'KEY':
                keys.append(self.tokens[self.pos][1].lower())
                self.pos += 1
            if not keys:
                raise SyntaxError("HOTKEY requires at least one key")
            return {"type": "hotkey", "keys": keys}

        if cmd == 'SCROLL':
            direction = self._expect('KEY').upper()
            amount = 3
            if self._peek() == 'NUMBER':
                amount = int(self.tokens[self.pos][1])
                self.pos += 1
            if direction == 'DOWN':
                amount = -amount
            return {"type": "scroll", "amount": amount}

        if cmd == 'SCREENSHOT':
            filename = 'screenshot.png'
            if self._peek() == 'STRING':
                filename = self.tokens[self.pos][1]
                self.pos += 1
            return {"type": "screenshot", "filename": filename}

        if cmd == 'FIND':
            image = self._expect('STRING')
            return {"type": "find", "image": image}

        if cmd == 'ALERT':
            message = self._expect('STRING')
            return {"type": "alert", "message": message}

        if cmd == 'TYPEFILE':
            path = self._expect('STRING')
            return {"type": "typefile", "path": path}

        if cmd == 'COPYFILES':
            folder = self._expect('STRING')
            exclude = None
            if self._peek() == 'STRING':
                exclude = self.tokens[self.pos][1]
                self.pos += 1
            return {"type": "copyfiles", "folder": folder, "exclude": exclude}

        if cmd == 'WAIT':
            return {"type": "wait"}

        raise SyntaxError(f"Unknown command: {cmd}")

    def _expect(self, kind):
        if self.pos >= len(self.tokens):
            raise SyntaxError(f"Expected {kind} but reached end of file")
        actual_kind, value = self.tokens[self.pos]
        if actual_kind != kind:
            raise SyntaxError(
                f"Expected {kind}, got {actual_kind} ('{value}')")
        self.pos += 1
        return value

    def _peek(self):
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos][0]

    def _skip_newlines(self):
        while self.pos < len(self.tokens) and self.tokens[self.pos][0] == 'NEWLINE':
            self.pos += 1


def parse(tokens):
    return Parser(tokens).parse()
