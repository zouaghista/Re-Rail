import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import logging
import numpy as np
import requests
from signalrcore.hub_connection_builder import HubConnectionBuilder
import asyncio
import urllib.parse as parse
import cv2
import supervision as sv
from ultralytics import YOLO
model = YOLO('best1.pt')

def get_unique_detections(results):
    """Print unique detections and return formatted string"""
    # Get all detection names
    detections = [results.names[int(box.cls[0])] for box in results.boxes]
    
    # Get unique detections
    unique_detections = sorted(set(detections))
    
    # Print unique detections
    print("Unique detections:")
    for detection in unique_detections:
        print(detection)
        
    # Create formatted string
    formatted_string =  ", ".join(unique_detections)
    
    return formatted_string

class SignalRClient:
    def __init__(self, queue, inference_queue):
        self.hub_connection = None
        self.connection_id = None
        self.connected = False
        self.logger = logging.getLogger("SignalRClient")
        self._queue = queue
        self._inference_queue = inference_queue

    def configure_logging(self):
        logging.basicConfig(level=logging.DEBUG)

    def on_open(self):
        self.connected = True
        try:
            connection_id = parse.parse_qs(parse.urlparse(self.hub_connection.transport.url).query)['id'][0]
            self.connection_id = connection_id
            self.logger.info(f"Connected with connection ID: {self.connection_id}")
            self.hub_connection.send("SubToResolver", ["Testingdgrd"])
        except Exception as e:
            self.logger.error(f"Error retrieving connection ID: {e}")

    def on_close(self):
        self.connected = False
        self.logger.info("Connection closed")

    def on_error(self, data):
        self.logger.error(f"An exception was thrown: {data.error}")

    def connect(self):
        #self.configure_logging()
        try:
            self.hub_connection = HubConnectionBuilder() \
                .with_automatic_reconnect({
                    "type": "raw",
                    "keep_alive_interval": 100,
                    "reconnect_interval": 5,
                    "max_attempts": 5
                }) \
                .with_url("http://192.168.47.106:7089/Classification?uid=jason&sid=test&api-key=112233", options={"verify_ssl": False}) \
                .build()

            self.hub_connection.on("ProcessImage", self.receive_message)
            self.hub_connection.on_open(self.on_open)
            self.hub_connection.on_close(self.on_close)
            self.hub_connection.on_error(self.on_error)
            self.hub_connection.start()
        except Exception as e:
            self.logger.error(f"Failed to connect to the server: {e}")

    def receive_message(self, *args, **kwargs):
        print(f"jeni message{args[0]}")
        print(f"queue size {self._queue.qsize()}")
        self._queue.put_nowait(args[0][0])

    async def listen_forever(self):
        while True:
            if not self.connected:
                self.logger.warning("Disconnected, attempting to reconnect...")
                self.hub_connection.stop()
                self.connected = False
                self.connect()
            elif self._inference_queue.qsize() > 0:
                item = self._inference_queue.get_nowait()
                print([item[0], item[1]])
                self.hub_connection.send("SetClassification", [item[0], item[1]])
            await asyncio.sleep(0.1)


def get_image_from_url(url):
    # Send a GET request to the image URL
    response = requests.get(url,verify=False)
    # Check if the request was successful
    if response.status_code == 200:
        # Convert the image data to a numpy array
        image_array = np.asarray(bytearray(response.content), dtype=np.uint8)

        # Decode the image from the byte array
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is not None:
            return image
        else:
            print("Error: Failed to decode the image.")
            return None
    else:
        print(f"Error: Unable to fetch image. Status code: {response.status_code}")
        return None


async def Resolver(queue, inference_queue):
    while True:
        item = await queue.get()  # Get an item from the queue
        print(f"consumer: Queue size {queue.qsize()}")
        print(f"will treat {item}")
        if item is None:  # Sentinel value, time to stop
            break
        print(f'Consumer: Processing {item}')
        url = f"http://192.168.47.106:7089/Image/GetImage?Id={item}"  # Replace with the actual image URL
        image = get_image_from_url(url)
        
        results = model(image)[0]
        formatted_result = get_unique_detections(results)
        """
        detections = sv.Detections.from_ultralytics(results)
        bounding_box_annotator = sv.BoundingBoxAnnotator()
        label_annotator = sv.LabelAnnotator()
        annotated_image = bounding_box_annotator.annotate(
            scene=image, detections=detections)
        annotated_image = label_annotator.annotate(
            scene=annotated_image, detections=detections)
        """
        #sv.plot_image(annotated_image)
        print("fetched image")
        await inference_queue.put((item, formatted_result))
    print("Consumer: Finished processing")


async def main():
    queue = asyncio.Queue()
    inference_queue = asyncio.Queue()
    signalr_client = SignalRClient(queue, inference_queue)
    signalr_client.connect()
    res = asyncio.create_task(Resolver(queue, inference_queue))
    await signalr_client.listen_forever()
    await res


asyncio.run(main())