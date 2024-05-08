! pip install gradio_client

import gradio_client
import re
import io
import base64

from gradio_client import Client
from PIL import Image

client = Client("wcy1122/Mini-Gemini")

result = client.predict(
		api_name="/clear_history"
)
print(result)

result = client.predict(
		imagebox=None,
		textbox="Hello!!",
		image_process_mode="Default",
		gen_image="No",
		temperature=0.2,
		top_p=0.7,
		max_output_tokens=512,
		api_name="/generate_1"
)
print(result)

result = client.predict(
		imagebox=None,
		textbox="What is 김치찌개? Explain its ingredients and generate an image of the korean dish.",
		image_process_mode="Default",
		gen_image="Yes",
		temperature=0.2,
		top_p=0.7,
		max_output_tokens=512,
		api_name="/generate_1"
)

pattern = r'src="data:image/jpeg;base64,([^"]+)"'

resultstr = str(result)
imagecode = re.findall(pattern, resultstr)

base64_image_data = imagecode[0]
image_data = base64.b64decode(base64_image_data)

image = Image.open(io.BytesIO(image_data))

image.show()
image.save("save path")
