import cv2
import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import argparse
import sys
import time
import os, subprocess, platform
from pathlib import Path
from langdetect import detect, DetectorFactory
import string
import json
import logging

BASE = Path(getattr(sys, "_MEIPASS",Path(__file__).parent))
out_path="@__INVALID__@"
def _get_exe_dir() -> Path:
    """
    Works both when you run the .py and when the app r̥r̥is frozen
    (e.g. PyInstaller, Nuitka, cx_Freeze).
    """
    if getattr(sys, 'frozen', False):          # the program is frozen
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent     # running as .py

LOG_PATH = _get_exe_dir() /"logs"/ "error.log"
LOG_DIR = str(_get_exe_dir() / "logs")
if not (os.path.exists(LOG_DIR)):
    os.mkdir(LOG_DIR)

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stderr)  # still show it in console
    ]
)

POPPLER_PATH_BIN = str(BASE / "lib" / "poppler" / "bin")
DetectorFactory.seed = 0  # for consistent language detection
def _log_unhandled_exception(exc_type, exc_value, exc_tb):
    """
    sys.excepthook replacement: writes uncaught exceptions to error.log
    and waits for Enter so the window doesn’t disappear.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Let Ctrl-C behave normally.
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    logging.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    print("\nA fatal error occurred. Full details are in error.log.")
    input("Press Enter to exit…")

sys.excepthook = _log_unhandled_exception

def tesseract_init():
    if platform.system() == "Windows":
        root = (BASE / "lib" / "tesseract")
        pytesseract.pytesseract.tesseract_cmd = str(root / "tesseract.exe")
        os.environ["TESSDATA_PREFIX"] = str(root / "tessdata")

def is_english(text):
    try:
        # langdetect can fail on very short strings, so filter those out
        if len(text.strip()) < 3:
            return True  # keep very short lines (like "a", "I")
        lang = detect(text)
        return lang == 'en'
    except:
        # If detection fails, consider it non-English
        return False

def filter_english_lines(text):
    lines = text.splitlines()
    filtered_lines = [line for line in lines if is_english(line)]
    return "\n".join(filtered_lines)


def preprocess_image(img: Image.Image) -> np.ndarray:
    """Universal preprocessing for both small and large text."""
    img_np = np.array(img)
    
    # Convert to grayscale if needed
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY) if len(img_np.shape) == 3 else img_np
    
    # Multi-scale preprocessing
    # 1. Normal-scale text enhancement
    _, normal_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 2. Large text enhancement (headers)
    dilated = cv2.dilate(gray, np.ones((5, 5), np.uint8), iterations=1)
    _, large_thresh = cv2.threshold(dilated, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Combine both
    combined = cv2.bitwise_or(normal_thresh, large_thresh)
    return combined


def ocr_image(image_path):
    image = Image.open(image_path)
    processed = preprocess_image(image)

    whitelist = (
        'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        '0123456789.,:;!?()[]{}<>_+=-*/"\\\':@#$%^&~|'
    )

    safe = json.dumps(whitelist)  
    safe_ascii = ''.join(c for c in string.printable[:95] if c != '"')
    whitelist   = ' ' + safe_ascii 

    custom_config = f'--oem 3 --psm 6 -c preserve_interword_spaces=1' #-c tessedit_char_whitelist="{whitelist}"'
    
    text = pytesseract.image_to_string(processed, config=custom_config, lang='eng+hin')
    return text

def preprocess_large_text(img: Image.Image) -> np.ndarray:
    """Optimized for large headers like 'JANE DOE'"""
    img_np = np.array(img)
    
    # 1. Convert to grayscale and invert (white text on black)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # 2. Gentle dilation (preserve letter shapes)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # 3. Noise removal (for isolated artifacts)
    processed = cv2.medianBlur(processed, 3)
    
    return processed


def ocr_pdf(pdf_path: str) -> str:
    images = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH_BIN)
    full_text = []
    
    for img in images:
        # Header extraction
        header_processed = preprocess_large_text(img)
        header_text = pytesseract.image_to_string(
            header_processed,
            config='--oem 3 --psm 11',
            lang='hin+eng'
        )
        
        # Body text extraction
        # gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        # _, body_processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # body_text = pytesseract.image_to_string(body_processed, config='--oem 3 --psm 6')
        
        full_text.append(f"{header_text.strip()}") #\n---\n{body_text}")
    
    return "\n---\n".join(full_text)
# def ocr_pdf__(pdf_path):
#     poppler_path = str(Path(__file__).parent / "poppler" / "bin")
#     pages = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)
#     final_text = ""
#     for i, page in enumerate(pages):
#         processed = preprocess_image(page)
#         raw_text = pytesseract.image_to_string(processed, config='--oem 3 --psm 6 -c preserve_interword_space=1', 
#         lang='eng+hin')
#         t = filter_english_lines(raw_text)
#         final_text += f"\n--- Page {i+1} ---\n{t}"
  
#     return final_text
def showLoadingBar():
    spinner = "|/-\\"
    idx = 0
    while not out_path == "@__INVALID__@":
        sys.stdout.write(f'\rProcessing... {spinner[idx % len(spinner)]}')
        sys.stdout.flush()
        idx += 1
        time.sleep(0.1)
    sys.stdout.write('\rProcessing... done!     \n')



def get_downloads_path():
    """Return the user's Downloads folder on Windows"""
    return str(Path.home() / "Downloads")

def main():
    print(r"""
    !Welcome to the SarasOCR! 👋
    OCR tool for image or PDF input 📃

    This tool extracts text from images or PDF files using OCR (Optical Character Recognition).
    It supports English and Hindi languages, and can save the recognized text to a file.

How it works:
1. You will be asked to enter the path to the input file (image or PDF).
2. Next, you will choose the output mode:
    - default : Save the OCR output as a .txt file in your Downloads folder.
    - output(o/O)  : Save the OCR output to a file path you specify.
    - print(p/P)   : Display the OCR output directly on the screen (no file saved).
3. If you choose 'output' mode, you will be prompted to enter the full path for the output text file.
4. Then, the OCR process will start and output will be saved or displayed accordingly.

Example:
  file: C:/path/to/file.pdf
  mode: O
  output: C:/path/to/output.txt
          

          
Notes:
- For file paths on Windows, use backslashes ( \ ), or double backslashes ( \\ ) if needed.
- If your path contains spaces, enclose it in quotes (e.g. "C:\Users\Your Name\Documents\file.txt").

Let's get started!
""")
    proceed = input("Do you want to continue? [Y/n]: ").strip().lower()
    if proceed not in ('', 'y', 'yes'):
        print("Exiting application.")
        return

    # parser = argparse.ArgumentParser(description="OCR tool for image or PDF input")
    # parser.add_argument("file", help="Path to the image or PDF file")
    # parser.add_argument("-o", "--output", help="Path to output text file (optional)")
    # parser.add_argument("-d", "--download", action="store_true", help="Save output in Downloads folder with the same name as input")

    
    #args = parser.parse_args()

    file = input("Enter the path to the file: ").strip().strip('"').strip("'")
    while not os.path.exists(file):
        print("Error: File does not exist.")
        file = input("Enter the path to the file: ").strip().strip('"').strip("'")

    print("\nChoose output mode:")
    print("  1. default (save to Downloads folder)")
    print("  2. output  (save to a file path you specify)")
    print("  3. print   (display output on screen)")
    mode = input("Enter 1, 2, or 3: ").strip()

    mode_map = {"1": "default", "2": "output", "3": "print"}

    if mode == '1':
        output = get_downloads_path() + "/" + Path(file).stem + ".txt"
    elif mode=='2':
        output = input("Enter the path to the output file: ")
        if output and not output.lower().endswith('.txt'):
            output += '.txt'
    else:
       output = None

    print(f"Processing file: {file}")

    showLoadingBar()

    if file.lower().endswith(".pdf"):
        text = ocr_pdf(file)
    else:
        text = ocr_image(file)

    if output:
        out_path = output
    else:
        out_path = None

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"OCR output saved to: {out_path}")
    else:
        print("\n=== OCR Output ===\n")
        print(text)

if __name__ == "__main__":
    try:
        tesseract_init()
        print(POPPLER_PATH_BIN)
        main()
    except Exception as e:
        logging.exception("Fatal error inside main()")
        print("\nSomething went wrong. Check error.log for details.")
        input("\nPress Enter to exit...")
    finally:
        if(getattr(sys,"frozen",False)):
            try:
                input("\n Press Enter to Exit...")
            except EOFError:
                pass