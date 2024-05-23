! pip install gradio_client

import gradio_client
import re
import io
import base64

from gradio_client import Client
from PIL import Image

client = Client("http://103.170.5.190:7860/")

result = client.predict(
		api_name="/clear_history"
)
print(result)

result = client.predict(
		"Hi",	# str  in 'parameter_3' Textbox component
		None,	# filepath  in 'parameter_11' Image component
		"Default",	# Literal['Crop', 'Resize', 'Pad', 'Default']  in 'Preprocess for non-square image' Radio component
		api_name="/add_text_1"
)
print(result)

result = client.predict(
		"MGM-34B-HD",	# Literal['MGM-34B-HD']  in 'parameter_10' Dropdown component
		0,	# float (numeric value between 0.0 and 1.0) in 'Temperature' Slider component
		0,	# float (numeric value between 0.0 and 1.0) in 'Top P' Slider component
		100,	# float (numeric value between 0 and 1024) in 'Max output tokens' Slider component
		"No",	# Literal['Yes', 'No']  in 'Generate Image' Radio component
		"No",	# Literal['Yes', 'No']  in 'Use OCR' Radio component
		api_name="/http_bot_1"
)
print(result)

pattern = r'src="data:image/jpeg;base64,([^"]+)"'

resultstr = str(result)
imagecode = re.findall(pattern, resultstr)

base64_image_data = imagecode[0]
image_data = base64.b64decode(base64_image_data)

image = Image.open(io.BytesIO(image_data))

image.show()
image.save("save path")
