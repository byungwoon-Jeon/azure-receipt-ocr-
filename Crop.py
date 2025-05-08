import cv2
import numpy as np

# 1. 이미지 로드 및 전처리
image = cv2.imread('input.jpg')
gray  = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
blur  = cv2.GaussianBlur(gray, (5,5), 0)

# 2. 에지 검출
edges = cv2.Canny(blur, threshold1=50, threshold2=150)  # 임곗값은 이미지에 맞게 조절

# 3. 윤곽선 검출 (외곽만)
contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 4. 각 윤곽선에 대해 처리
receipt_idx = 0
for cnt in contours:
    area = cv2.contourArea(cnt)
    if area < 1000:   # 너무 작은 영역 무시 (필요시 조절)
        continue
    # 5. 다각형 근사
    peri   = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
    # 컨벡스 헐 적용 (윤곽의 볼록한 외곽 얻기)
    hull = cv2.convexHull(cnt)
    hull_area = cv2.contourArea(hull)
    if hull_area < 1000:
        continue
    # 헐도 근사해서 4점 얻기 시도
    hull_poly = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
    corners = None
    if len(approx) == 4:
        corners = approx
    elif len(hull_poly) == 4:
        corners = hull_poly
    else:
        # 사각형으로 근사되지 않은 경우 bounding box 사용
        x,y,w,h = cv2.boundingRect(cnt)
        corners = np.array([ [x,y], [x+w, y], [x+w, y+h], [x, y+h] ], dtype=np.float32)
    corners = corners.reshape(4,2).astype(np.float32)

    # 6. 좌표 정렬 및 원근 변환
    # (보통 좌표를 [좌상, 우상, 우하, 좌하] 순으로 정렬)
    # OpenCV의 perspectiveTransform은 점 순서에 따라 결과가 달라지므로 정렬이 필요
    ordered = order_points(corners)  # 좌표를 정렬하는 사용자 함수가 있다고 가정
    (tl, tr, br, bl) = ordered
    # 폭과 높이 계산
    widthA  = np.linalg.norm(br - bl)
    widthB  = np.linalg.norm(tr - tl)
    maxW = int(max(widthA, widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxH = int(max(heightA, heightB))
    dst_quad = np.array([[0,0],[maxW-1,0],[maxW-1,maxH-1],[0,maxH-1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(ordered, dst_quad)
    warp = cv2.warpPerspective(image, M, (maxW, maxH))

    # 7. 개별 이미지 저장
    receipt_idx += 1
    cv2.imwrite(f"receipt_{receipt_idx}.png", warp)
    # (추가로 corners 좌표를 저장하거나 처리할 수 있음)
