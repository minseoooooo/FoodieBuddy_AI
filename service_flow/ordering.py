#기본 로직은 완성, cohere은 그럭저럭 잘 되는 중, 중간에 minigemini, ingredient에서 오류 있어서 일단 제외해둠
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

#API 부르기 / 기본 세팅

#OCR API
endpoint = "https://api.ocr.space/parse/image"

api_key = "OCR key"
language = "kor"

#Mini Gemini API
client = Client("http://103.170.5.190:7860/")
result = client.predict(
		api_name="/clear_history"
)

#Cohere API
co = cohere.Client("Cohere Key")

#식재료 Data
myKey = 'data key'
url = 'http://apis.data.go.kr/1390802/AgriFood/FdFood/getKoreanFoodFdFoodList'

def get_menu_ocr(image_path):
  image_path = image_path

  response = requests.post(endpoint, files={"file": open(image_path, "rb")},
                          data={"apikey": api_key, "language": language})
  ocr_result = response.json()
  korean_text = re.sub('[^ 가-힣]', '', ocr_result["ParsedResults"][0]["ParsedText"])

  return korean_text

def dishimg_gen(gemini_prompt):
	gemini_result = client.predict( api_name="/clear_history" )
  
	text = gemini_prompt

	result = client.predict( api_name="/clear_history" )

	result = client.predict( text, None, "Default", api_name="/add_text_1" )

	result = client.predict( "MGM-34B-HD", 0.5, 0.5, 500,
			"Yes", #'Generate Image'
			"No",	#'Use OCR'
			api_name="/http_bot_1"
	)
 
	pattern = r'src="data:image/jpeg;base64,([^"]+)"'
	resultstr = str(gemini_result)

	imagecode = re.findall(pattern, resultstr)

	base64_image_data = imagecode[0]
	image_output = base64.b64decode(base64_image_data)

	image_output = Image.open(io.BytesIO(image_output))

	#image_output.show()
	#image_output.save("save path")
	return image_output

def search_ingredients(dish_name):
  temp_co = cohere.Client("2U2SvgDQbaD38G2znqB4yWYW8uk5bi99gT0hKmOf")
  kor_dish_name = temp_co.chat(
    chat_history = [],
    message = "Translate this korean dish name in korean without any explanation. Q:Kimchi jjigae A:김치찌개, Q:Tteokbokki A:떡볶이, Q:"+dish_name+" A:",
    connectors = [{"id": "web-search"}]
  )
  kor_dish_name.text
  params ={'serviceKey' : myKey, 'service_Type' : 'xml', 'Page_No' : '1', 'Page_Size' : '20', 'food_Name' : kor_dish_name.text}

  ingredients_response = requests.get(url, params=params)

  xml_data = response.content
  root = ET.fromstring(xml_data)

  result_msg_element = root.find('.//result_Msg')

  if result_msg_element is not None and result_msg_element.text == '요청 데이터 없음':
      return "not able to find"
  else:
      item = root.find('body/items').findall('item')[0]
      food_List = item.find('food_List').findall('food')

      ingredients = ""

      for food in food_List:
          fd_Eng_Nm = food.find('fd_Eng_Nm').text
          ingredient = fd_Eng_Nm.split(',')[0]

          ingredients = ingredients +  ", " + ingredient
      return ingredients

cohere_prompt = f"""
You are an expert of korean dish. You should lead the whole process of this conversation kindly to help a user to choose a dish based on user's dietary restrictions. The user's dietary restrictions are {user_diet}.
This prompt has two parts.

<Part 1>
1.1. When the user give you a list of the dish name, explain each dish of the input in one sentence. If there is a typo in the input, you should fix it.
1.2. When the user choose one of the dish that you explained, you should mark your ouput by starting your answer with "MARK" and explain the dish detailed way related to the user's dietary restrictions.
1.3. If the user want to order the dish, you can continue to step 1.4. If the user don't want to order the dish, you should go back to step 1.2, showing the result of the list and short explaination of the dish again and letting the user choose the dish again.
1.4. You should ask if the user have any questions about the dish. Then, let the user answer your question.

<Part 2>
From now on, you will create guide sentences for the user to order the dish in korean, with the pronounciation in IPA and the meaning in english of the sentence.
EVERY TIME YOU CREATE A SENTENCE USING THIS FRAME, YOU SHOULD LET THE USER ENTER THE ANSWER OF THE SENTENCE.
The frame of the output is as below:
"a sentence in korean
[IPA sign]
the meaning of the sentence in english"
If the user ask you to recreate the sentence with another meaning, you should recreate it based on the user's request.

2.1. You should create a sentence to start the conversation with the waiter and let the user answer if the user start the ordering.
The example of the output is as below:
"사장님, 비빔밥 하나 주문할 건데요, 그 전에 질문이 있어요.
[sʰadzaŋɲim pibimp̕ap̚ hana tsumunhal k̕ʌndeyo kɯ dzʌne tsilmuɲi is̕ʌyo]
I'm going to order Bibimbap, but before that, I have a few questions."

2.2. You should create a question about one ingredient that user should not eat and what user want to know and you should let the user enter the answer of each question.
You may repeat this step several times based on the number of ingredients in the user's dietary restrictions.
The example of the output is as below:
"비빔밥에 버섯 들어가면, 뺄 수 있나요?
[pibimp̕abe pʌsʰʌt̚ tɯrʌgamyʌn p̕ɛl s̕u innayo]?
If there are mushrooms in bibimbap, can you leave out mushrooms, please?"

2.2-1. If the user answers 'No' to the questions at least once, you should stop creating a question and create a output as below:
"그럼 조금 더 고민해볼게요.
[kɯɾʌm t͡ɕoɡɯm tʰʌ kominha bʌlˈk̕ejo]
Then I'll think about it a little more."
Then you should go back to step 2, showing the result of the list and short explaination of the dish again and letting the user choose the dish again.

2.3. If the user answers 'Yes' to all the questions, you should create a sentence that will end the ordering.
The example of the output is as below:
"그렇게 주문할게요. 감사합니다.
[kɯrʌkʰe tsumunhalk̕eyo kamsʰahamɲida]
I would like to order it like that. Thank you."
After that, you should also let the user know the overall conversation is over, marking your ouput by starting your answer with "END"

If the user ask any questions in the middle of the overall flow, you should answer it kindly.
"""

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
    
    #pattern = r"###(.*?)###"
    #dish_name = re.search(pattern, dish_name_response.text).group(1)
    #ingredients = search_ingredients(dish_name)

    #gemini_propmt = f"""Create an image of {dish_name} which is a korean dish that contains {ingredients} as main ingredients."""
    
    #gemini_prompt = f"""Create an image of {dish_name_response} which is a korean dish."""
    #dishimg = dishimg_gen(gemini_prompt)
    #dishimg.show()

    modified_response = response.text[4:]


  print(f"FoodieBuddy: {modified_response} \n")
  chat_history.append({"role": "AI", "message": response.text})
