import pytesseract
from PIL import Image
import os


def find_tesseract():

    possible_paths = [

        # chemins classiques Windows
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",

        # autres cas possibles
        r"C:\Tesseract-OCR\tesseract.exe",
    ]

    # vérifier chemins connus
    for path in possible_paths:
        if os.path.exists(path):
            return path

    print("🔎 Searching for tesseract.exe on disk...")

    # recherche disque C (plus lent mais efficace)
    for root, dirs, files in os.walk("C:\\"):
        if "tesseract.exe" in files:
            found_path = os.path.join(root, "tesseract.exe")
            print(f"✅ Found Tesseract at: {found_path}")
            return found_path

    return None


# trouver tesseract automatiquement
tesseract_path = find_tesseract()

if tesseract_path:

    pytesseract.pytesseract.tesseract_cmd = tesseract_path

else:

    raise Exception(
        "❌ Tesseract not found. Please install it."
    )


def read_text(image_path):

    img = Image.open(image_path)

    text = pytesseract.image_to_string(img)

    return text