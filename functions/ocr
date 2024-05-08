#한국어 메뉴판 가정

import re
import requests

endpoint = "https://api.ocr.space/parse/image"

api_key = "API key"
language = "kor"

image_path = "image path"

response = requests.post(endpoint, files={"file": open(image_path, "rb")},
                         data={"apikey": api_key, "language": language})
result = response.json()
korean_text = re.sub('[^ 가-힣]', '', result["ParsedResults"][0]["ParsedText"])
print(korean_text)
