import pyautogui
import webbrowser
import time
import os
import struct
import ctypes

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


def execute(nodes):
    for node in nodes:
        t = node["type"]

        if t == "open":
            print(f"  -> Opening {node['url']}")
            webbrowser.open(node["url"])

        elif t == "gap":
            print(f"  -> Waiting {node['duration']}s")
            time.sleep(node["duration"])

        elif t == "press":
            key, count = node["key"], node["count"]
            print(f"  -> Pressing '{key}' x{count}")
            pyautogui.press(key, presses=count, interval=0.05)

        elif t == "type":
            print(f"  -> Typing \"{node['text']}\"")
            pyautogui.write(node["text"], interval=0.03)

        elif t == "loop":
            n = node["count"]
            print(f"  -> Loop x{n}")
            for _ in range(n):
                execute(node["body"])

        elif t == "click":
            btn = node["button"]
            print(f"  -> {btn.capitalize()} click")
            pyautogui.click(button=btn)

        elif t == "hotkey":
            combo = " + ".join(node["keys"])
            print(f"  -> Hotkey {combo}")
            pyautogui.hotkey(*node["keys"])

        elif t == "scroll":
            direction = "up" if node["amount"] > 0 else "down"
            print(f"  -> Scroll {direction} {abs(node['amount'])}")
            pyautogui.scroll(node["amount"])

        elif t == "screenshot":
            fname = node["filename"]
            print(f"  -> Screenshot -> {fname}")
            pyautogui.screenshot(fname)

        elif t == "find":
            image = node["image"]
            print(f"  -> Finding '{image}' on screen ...")
            location = None
            for attempt in range(1, 11):
                try:
                    location = pyautogui.locateCenterOnScreen(
                        image, confidence=0.8
                    )
                except pyautogui.ImageNotFoundException:
                    location = None
                if location is not None:
                    break
                print(f"    attempt {attempt}/10 -- not found, retrying ...")
                time.sleep(1)
            if location is None:
                raise RuntimeError(
                    f"FIND failed: could not locate '{image}' on screen"
                )
            x, y = location
            print(f"  -> Found at ({x}, {y}) -- moving mouse")
            pyautogui.moveTo(x, y)

        elif t == "alert":
            msg = node["message"]
            print(f"  -> Alert: {msg}")
            pyautogui.alert(text=msg, title="Automation Script", button="OK")

        elif t == "typefile":
            filepath = node["path"]
            print(f"  -> Typing contents of '{filepath}'")
            with open(filepath, 'r') as f:
                lines = f.read().strip().splitlines()
            for i, line in enumerate(lines):
                line = line.strip()
                if line:
                    pyautogui.write(line, interval=0.03)
                    if i < len(lines) - 1:
                        pyautogui.press('enter')
                        time.sleep(0.1)

        elif t == "copyfiles":
            folder = node["folder"]
            exclude = node["exclude"]
            print(f"  -> Copying files from '{folder}' to clipboard", end="")
            if exclude:
                print(f" (excluding '{exclude}')")
            else:
                print()
            file_paths = []
            for name in os.listdir(folder):
                full = os.path.join(folder, name)
                if os.path.isfile(full):
                    if exclude and name.lower() == exclude.lower():
                        continue
                    file_paths.append(os.path.abspath(full))
            if not file_paths:
                raise RuntimeError(f"No files found in '{folder}'")
            offset = 20
            files_data = b""
            for p in file_paths:
                files_data += p.encode('utf-16-le') + b'\x00\x00'
            files_data += b'\x00\x00'
            header = struct.pack('IIIii', offset, 0, 0, 0, 1)
            data = header + files_data
            GMEM_MOVEABLE = 0x0002
            CF_HDROP = 15
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
            kernel32.GlobalAlloc.restype = ctypes.c_void_p
            kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            user32.OpenClipboard.argtypes = [ctypes.c_void_p]
            user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
            user32.CloseClipboard.argtypes = []
            hMem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            pMem = kernel32.GlobalLock(hMem)
            if not pMem:
                raise RuntimeError("Failed to lock global memory for clipboard.")
            ctypes.memmove(pMem, data, len(data))
            kernel32.GlobalUnlock(hMem)
            opened = False
            for _ in range(10):
                if user32.OpenClipboard(None):
                    opened = True
                    break
                time.sleep(0.05)
            if not opened:
                raise RuntimeError("Could not open Windows clipboard.")
            user32.EmptyClipboard()
            user32.SetClipboardData(CF_HDROP, hMem)
            user32.CloseClipboard()
            print(f"     {len(file_paths)} file(s) copied to clipboard")

        elif t == "wait":
            input("  Paused -- press Enter to continue...")