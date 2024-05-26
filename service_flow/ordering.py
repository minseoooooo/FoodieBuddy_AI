!pip install cohere
!pip install gradio_client

import re
import requests

import gradio_client
import re
import io
import base64

from gradio_client import Client, file
from PIL import Image

import cohere

import requests

import xml.etree.ElementTree as ET

#user 정보
user_diet = "Must not eat : Tofu, Should avoid : Mushroom, Can eat in moderation: Gluten"

def get_menu_ocr(image_path):
  endpoint = "https://api.ocr.space/parse/image"

  api_key = "K84679065888957"
  language = "kor"
  image_path = image_path

  response = requests.post(endpoint, files={"file": open(image_path, "rb")},
                          data={"apikey": api_key, "language": language})
  ocr_result = response.json()
  korean_text = re.sub('[^ 가-힣]', '', ocr_result["ParsedResults"][0]["ParsedText"])

  return korean_text

def dishimg_gen(gemini_prompt):
	client = Client("http://103.170.5.190:7860/")
	gemini_result = client.predict( api_name="/clear_history" )

	text = gemini_prompt

	result = client.predict( api_name="/clear_history" )

	result = client.predict( text, None, "Default", api_name="/add_text_1" )

	result = client.predict( "MGM-34B-HD", 0.5, 0.5, 1024,
			"Yes", #'Generate Image'
			"No",	#'Use OCR'
			api_name="/http_bot_1")

	pattern = r'src="data:image/jpeg;base64,([^"]+)"'
	resultstr = str(result)

	imagecode = re.findall(pattern, resultstr)

	print(imagecode)
	base64_image_data = imagecode[0]
	image_output = base64.b64decode(base64_image_data)

	image_output = Image.open(io.BytesIO(image_output))

	return image_output

def search_ingredients(dish_name):
  temp_co = cohere.Client("2U2SvgDQbaD38G2znqB4yWYW8uk5bi99gT0hKmOf")
  kor_dish_name = temp_co.chat(
    chat_history = [],
    message = "Translate a korean dish name in korean without any explanation. Your answer should be a one korean word. Q:Kimchi jjigae A:김치찌개, Q:Tteokbokki A:떡볶이, Q:"+dish_name+" A:",
    connectors = [{"id": "web-search"}]
  )
  print(kor_dish_name.text)

  url = 'http://apis.data.go.kr/1390802/AgriFood/FdFood/getKoreanFoodFdFoodList'
  myKey = '6KMoh6rjEGBq/v8QvaX/3/KAj0DppT17EgLbwzR1IrrWDX+yiTuMtBEgo35a9fgZHz+5aW/wzd0Kv4RDo7Zuyg=='
  params ={'serviceKey' : myKey, 'service_Type' : 'xml', 'Page_No' : '1', 'Page_Size' : '20', 'food_Name' : kor_dish_name.text}

  ingredients_response = requests.get(url, params=params)

  xml_data = ingredients_response.content
  root = ET.fromstring(xml_data)

  result_msg_element = root.find('.//result_Msg')

  if result_msg_element is not None and result_msg_element.text == '요청 데이터 없음':
      return "no information"
  else:
      item = root.find('body/items').findall('item')[0]
      food_List = item.find('food_List').findall('food')

      ingredients = ""
      count_item = 0

      for food in food_List:
          fd_Eng_Nm = food.find('fd_Eng_Nm').text
          ingredient = fd_Eng_Nm.split(',')[0]


          if count_item == 0:
            ingredients = ingredient
          else :
            ingredients = ingredients +  ", " + ingredient
            if count_item == 4: break

          count_item+=1

      return ingredients


cohere_prompt = f"""
## Instructions
You are an kind expert of korean dish. You will help a user to choose a dish based on user's dietary restrictions in a restaurant. The user's dietary restrictions are {user_diet}.
The overall flow consists oftwo parts. If the user ask any questions in the middle of this flow, you should answer it kindly.
Using the included text below, perform the following steps:

<Part 1>
1.1. You will be given a list of the dish name. If there is a typo in the input, you should fix it. Explain each dish in one sentence at once.
1.2. Ask the user which dish the user want to order and wait until the user choose the dish.
1.3. Based on the user's choice, start your output with "MARK" and explain the dish detailed way related to the user's dietary restrictions
1.4. Ask if the user wnat to order the dish.
1.5. If the user want to order the dish, continue to step 1.6. If the user don't want to order the dish, start from the step 1.2 again, showing the result of the list and short explaination of the dish.
1.6. Ask if the user have any questions about the dish and continue to Part 2

<Part 2>
From now on, you will create guiding sentences for the user to order the dish in korean, with the pronounciation in IPA and the meaning in english of the sentence.
The frame of the output is as below:
"a sentence in korean
[IPA sign]
the meaning of the sentence in english"
EVERY TIME YOU USE THIS FRAME, LET THE USER ENTER THE ANSWER OF THE SENTENCE.

2.1. Create a sentence to start the conversation with the waiter.
The example of the output is as below:
"사장님, 비빔밥 하나 주문할 건데요, 그 전에 질문이 있어요.
[sʰadzaŋɲim pibimp̕ap̚ hana tsumunhal k̕ʌndeyo kɯ dzʌne tsilmuɲi is̕ʌyo]
I'm going to order Bibimbap, but before that, I have a few questions."

2.2. Ask the user if you can continue to 2.3.

2.3. Create a question about ONE INGREDIENT that user should not eat and what user want to know.
The example of the output is as below:
"비빔밥에 버섯 들어가면, 뺄 수 있나요?
[pibimp̕abe pʌsʰʌt̚ tɯrʌgamyʌn p̕ɛl s̕u innayo]?
If there are mushrooms in bibimbap, can you leave out mushrooms, please?"

2.4. Ask the user about the answer of the question.

2.4-1. If the user answers 'No' to the questions at least once, create a output as below:
"그럼 조금 더 고민해볼게요.
[kɯɾʌm t͡ɕoɡɯm tʰʌ kominha bʌlˈk̕ejo]
Then I'll think about it a little more."
Then, go back to Part 1, step 1.2, showing the result of the list and short explaination of the dish again.

2.4-2. If there are more restricted ingredients left that you didn't ask yet, you should go back to step 2.3.

2.5. After the user answers 'Yes' to all the questions, start your output with "END" and create a sentence that will end the ordering.
The example of the output is as below:
"그렇게 주문할게요. 감사합니다.
[kɯrʌkʰe tsumunhalk̕eyo kamsʰahamɲida]
I would like to order it like that. Thank you."
Also, let the user know the overall conversation is over.
"""
co = cohere.Client("2U2SvgDQbaD38G2znqB4yWYW8uk5bi99gT0hKmOf")

menu_ocr = get_menu_ocr("/content/1.1.png")

chat_history=[{"role": "SYSTEM", "message": cohere_prompt}]

response = co.chat(
  chat_history = chat_history,
  message = menu_ocr,
  connectors = [{"id": "web-search"}]
)

chat_history.append({"role": "USER", "message": menu_ocr})
print(f"FoodieBuddy: {response.text} \n")
chat_history.append({"role": "AI", "message": response.text})

while True:

  user_message = input("You: ")

  chat_history.append({"role": "USER", "message": user_message})

  response = co.chat(
    chat_history = chat_history,
    message = user_message,
    connectors = [{"id": "web-search"}]
  )

  if response.text.startswith("END"):
        print(response.text[3:])
        break

  if response.text.startswith("MARK"):
    dish_name_co = cohere.Client("2U2SvgDQbaD38G2znqB4yWYW8uk5bi99gT0hKmOf")
    dish_name_response = dish_name_co.chat(chat_history = [],
                   message = "FIND A DISH NAME FROM THE TEXT BELOW : \n " + response.text + "\n The output should be one noun",
                   connectors = [{"id": "web-search"}])

    dish_name = dish_name_response.text
    ingredients = search_ingredients(dish_name)

    gemini_prompt = f"""Create an image of {dish_name} which is a korean dish that contains {ingredients} as main ingredients."""
    dishimg = dishimg_gen(gemini_prompt)
    modified_dish_name = dish_name_response.text.lower().replace(" ", "")
    dishimg.save(f"/content/{modified_dish_name}.png")

    modified_response = response.text[4:]
    print(f"FoodieBuddy: {modified_response} \n")


  else : print(f"FoodieBuddy: {response.text} \n")

  chat_history.append({"role": "AI", "message": response.text})
