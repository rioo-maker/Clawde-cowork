from vision.screenshot import capture_screen
from vision.ocr import read_text

def analyze_screen():

    img_path = capture_screen()

    text = read_text(img_path)

    return text