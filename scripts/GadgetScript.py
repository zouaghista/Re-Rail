import time
import serial
import cv2
import requests
import threading

gps_port = 'devserial0'
baud_rate = 9600
ser = serial.Serial(gps_port, baud_rate, timeout=1)
global pos 


def read_gps()
    global pos
    while True
        data = ser.readline().decode('ascii', errors='ignore')
        if data.startswith('$GPGGA')
            parts = data.split(',')
            if len(parts) = 6
                raw_latitude = parts[2]
                lat_direction = parts[3]
                raw_longitude = parts[4]
                lon_direction = parts[5]
                if raw_latitude and raw_longitude
                    latitude = convert_to_decimal(raw_latitude, lat_direction)
                    longitude = convert_to_decimal(raw_longitude, lon_direction)
                    pos = f{longitude}, {latitude}
        
        time.sleep(0.9)


def upload_request(api_url, image_bytes, text)
    files = {
        'image' ('camera_image.jpg', image_bytes, 'imagejpeg')
    }
    data = {
        'text' text
    }
    try
        response = requests.post(api_url, files=files, data=data, verify=False)
    except requests.exceptions.RequestException as e
        print(Error during request, e)


def get_picture_from_camera_and_upload(api_url)
    global pos
    pos = ""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened()
        print(Error Could not open camera.)
        return
    start_time = time.time()
    period = 0.9
    while True
        ret, frame = cap.read()
        if not ret
            print(Error Failed to capture image.)
            break
        frame=cv2.flip(frame, 0)
        #cv2.imshow('Camera', frame)
        #key = cv2.waitKey(1) & 0xFF
        if time.time()-start_time  period
            _, image_encoded = cv2.imencode('.jpg', frame)
            image_bytes = image_encoded.tobytes()
            upload_request(api_url, image_bytes, pos)
            start_time = time.time()

        # If 'q' key is pressed, quit the loop
        #elif key == ord('q')
        #    break

    cap.release()
    #cv2.destroyAllWindows()


thread = threading.Thread(target=read_gps)
thread.start()
api_url = http192.168.47.1067089ImageUploadImage
get_picture_from_camera_and_upload(api_url)