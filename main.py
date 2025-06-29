import cv2
import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import argparse
import sys
import os
from pathlib import Path
from langdetect import detect, DetectorFactory
import string

DetectorFactory.seed = 0  # for consistent language detection

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

def preprocess_image(img):
    """Preprocess the image to improve OCR results."""
    # Convert to grayscale
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

    # Resize (Tesseract works better with larger text)
    scale_percent = 150  # increase by 150%
    width = int(gray.shape[1] * scale_percent / 100)
    height = int(gray.shape[0] * scale_percent / 100)
    gray = cv2.resize(gray, (width, height), interpolation=cv2.INTER_LINEAR)

    # Apply thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Remove noise (optional)
    denoised = cv2.medianBlur(thresh, 3)

    return Image.fromarray(denoised)

def ocr_image(image_path):
    image = Image.open(image_path)
    processed = preprocess_image(image)
    return pytesseract.image_to_string(processed, config='--oem 3 --psm 6 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:;!?()[]{}<>_+=-*/"\'@#$%^&~|')

def ocr_pdf(pdf_path):
    pages = convert_from_path(pdf_path, dpi=300)
    final_text = ""
    for i, page in enumerate(pages):
        processed = preprocess_image(page)
        raw_text = pytesseract.image_to_string(processed, config='--oem 3 --psm 6')
        t = filter_english_lines(raw_text)
        final_text += f"\n--- Page {i+1} ---\n{t}"
  
    return final_text

def get_downloads_path():
    """Return the user's Downloads folder on Windows"""
    return str(Path.home() / "Downloads")

def main():
    parser = argparse.ArgumentParser(description="OCR tool for image or PDF input")
    parser.add_argument("file", help="Path to the image or PDF file")
    parser.add_argument("-o", "--output", help="Path to output text file (optional)")
    parser.add_argument("-d", "--download", action="store_true", help="Save output in Downloads folder with the same name as input")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print("Error: File does not exist.")
        return

    print(f"Processing file: {args.file}")

    if args.file.lower().endswith(".pdf"):
        text = ocr_pdf(args.file)
    else:
        text = ocr_image(args.file)

    if args.output:
        out_path = args.output
    elif args.download:
        downloads_dir = get_downloads_path()
        base_name = Path(args.file).stem
        out_path = os.path.join(downloads_dir, f"{base_name}.txt")
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
    main()
