import cv2

# Initialize the camera
cap = cv2.VideoCapture(0)  # 0 is the default camera

if not cap.isOpened():
    print("Error: Could not open video device")
    exit()

# Set camera resolution (optional)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# Capture a single frame
ret, frame = cap.read()

if ret:
    # Save the captured image to a file
    cv2.imwrite('/home/pi/captured_image.jpg', frame)
    print("Image captured and saved as captured_image.jpg")
else:
    print("Error: Could not read frame")

# Release the camera
cap.release()
