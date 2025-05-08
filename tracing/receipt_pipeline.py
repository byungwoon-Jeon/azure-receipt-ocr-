import cv2
import numpy as np
import os

def load_image(path):
    image = cv2.imread(path)
    if image is None:
        raise FileNotFoundError(f"Image not found at {path}")
    return image

def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (21, 21), 0)
    normalized = cv2.divide(gray, blur, scale=255)
    return normalized

def get_edges(image):
    edges = cv2.Canny(image, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    return edges_closed

def find_receipt_contours(edges, min_area=1000):
    contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    receipt_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            receipt_contours.append(approx.reshape(4, 2))
    return receipt_contours

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def perspective_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxW = int(max(widthA, widthB))
    maxH = int(max(heightA, heightB))
    dst = np.array([[0, 0], [maxW - 1, 0], [maxW - 1, maxH - 1], [0, maxH - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxW, maxH))
    return warped

def process_receipt_image(image_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    image = load_image(image_path)

    # Step 1: Preprocessing
    preprocessed = preprocess_image(image)
    cv2.imwrite(os.path.join(output_dir, "preprocessed.png"), preprocessed)

    # Step 2: Edge Detection
    edges = get_edges(preprocessed)
    cv2.imwrite(os.path.join(output_dir, "edges.png"), edges)

    # Step 3: Contour Detection
    contours = find_receipt_contours(edges)

    outputs = []
    for idx, pts in enumerate(contours):
        warped = perspective_transform(image, pts)
        filename = os.path.join(output_dir, f"receipt_{idx + 1}.png")
        cv2.imwrite(filename, warped)
        outputs.append((filename, pts.tolist()))

    return outputs
