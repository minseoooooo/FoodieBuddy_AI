import os
import base64
import requests
import xml.etree.ElementTree as ET

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

os.environ["OPENAI_API_KEY"] = "API key"

def search_ingredients(dish_name):

  model = ChatOpenAI()

  chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "Translate a korean dish name in korean without any explanation. Your answer MUST be a one korean word. Examples - Q:Kimchi Jjigae (Kimchi Stew) A:김치찌개, Q:Samgyeopsal (Grilled Pork Belly) A:삼겹살"),
    ("user",  "Q:{dish_name} A:"),
  ])

  chain = chat_prompt | model | StrOutputParser()

  response = chain.invoke({"dish_name":f"{dish_name}",})

  url = 'http://apis.data.go.kr/1390802/AgriFood/FdFood/getKoreanFoodFdFoodList'
  myKey = 'apikey'
  params ={'serviceKey' : myKey, 'service_Type' : 'xml', 'Page_No' : '1', 'Page_Size' : '20', 'food_Name' : response}

  ingredients_response = requests.get(url, params=params)

  xml_data = ingredients_response.content
  root = ET.fromstring(xml_data)

  result_msg_element = root.find('.//result_Msg')

  if result_msg_element is None or result_msg_element.text == '요청 데이터 없음':
      return "No information"
  else:
      item = root.find('body/items').findall('item')[0]
      food_List = item.find('food_List').findall('food')

      ingredients = ""

      for food in food_List:
          fd_Eng_Nm = food.find('fd_Eng_Nm').text
          ingredient = fd_Eng_Nm.split(',')[0]


          if ingredients == "":
            ingredients = ingredient
          else :
            ingredients = ingredients +  ", " + ingredient

      return f"Ingredients of {dish_name} are "+ingredients

def get_img_response_prompt(param_dict):
  system_message = """You are a kind expert in Korean cuisine. What is the name of the korean side dish in the image?
  
  YOU MUST USE THIS FORM: The dish name in English (The pronunciation of its korean name). 
  For example, "Kimchi Jjigae (Kimchi Stew)", "Samgyeopsal (Grilled Pork Belly)".
  """
  human_message = [
      {
          "type": "text",
          "text": f"{param_dict['diet']}",

      },
      {
          "type":"image_url",
          "image_url": {
              "url": f"{param_dict['image_url']}",
          }
      }
  ]

  return [SystemMessage(content=system_message), HumanMessage(content=human_message)]

def get_img_response(img_path,str_user_diet):

  with open(img_path, "rb") as image_file:
    base64_img = base64.b64encode(image_file.read()).decode('utf-8')

  model = ChatOpenAI(model = "gpt-4o")

  chain = get_img_response_prompt | model | StrOutputParser()
  response = chain.invoke({"diet": str_user_diet,
                         "image_url":f"data:image/jpeg;base64,{base64_img}"
                         }
                       )
  return response

def askdish(dish_img, str_user_diet):

  # 채팅 사용 모델 - 파인 튜닝하면 여기에 쓸 모델 id가 바뀜
  model = ChatOpenAI(model = "gpt-4o")
  chat_history = ChatMessageHistory()

  #대화 시작 멘트 - 밑반찬 설명
  dish_name = get_img_response(dish_img, str_user_diet)
  system_message = SystemMessage(content=dish_name)
  chat_history.add_message(system_message)

  ingredients = search_ingredients(dish_name)
  ingredients_message = SystemMessage(content=ingredients)
  chat_history.add_message(ingredients_message)

  # askdish용 프롬프트
  askdish_prompt = f"""
  ## Instructions
  You are a kind expert in Korean cuisine. You will chat with a user in English to explain a korean side dish to the user based on the user's dietary restrictions.
  The user is a foreigner visiting a Korean restaurant in Korea.
  The user's dietary restrictions are {str_user_diet}. 
  
  Everytime you mention the dish name, YOU MUST USE THIS FORM: The dish name in English(The pronunciation of its korean name). 
  For example, "**Kimchi Stew(Kimchi Jjigae)**", "**Grilled Pork Belly(Samgyeopsal)**".

  Follow the steps below:
  1. You will be given a dish name and the its ingredients from the system. Using these information, Explain the dish from the image.
     YOU MUST SAY ONLY IN THE FORM BELOW INCLUDING LINEBREAKS.:
     "The basic information of the dish in one sentence.
     
      The main ingredients of the dish in one sentence. The information related to the user's dietary restrictions in one sentence.
      Whether it is suitable for the user or not.
      
      Several hashtags related to the dish."
      For example, "This dish is Braised Burdock Root(Ueongjorim), a type of side dish made with burdock root.
      
      It typically includes burdock root, soy sauce, sugar, sesame oil, and sometimes garlic. Since you avoid gluten, you should check if the soy sauce used in this preparation is gluten-free. 
      If it contains regular soy sauce, it might not be suitable for you.
      
      #healthy #side_dish #vegetable"
  2. Check if the user have any question. If user ask any questions about the dish, explain it kindly.
  """

  prompt = ChatPromptTemplate.from_messages(
        [
            ("system", askdish_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

  chain = prompt | model

  while True:
    response = chain.invoke({"messages": chat_history.messages})
    chat_history.add_ai_message(response.content)
    print(f"FoodieBuddy:{response.content}")

    user_message = input("You: ")
    if user_message.lower() == 'x':
      print("Chat ended.")
      break
    chat_history.add_user_message(user_message)
  return chat_history.messages

#유저 샘플 데이터
user_sample = [
    {"name": "John",
     "diet":{"meat": ["red meat", "other meat"],
              "dairy": ["milk"],
              "seafood" : ["shrimp"],
              "gluten(wheat)" : []
            }},
             ]

#유저 샘플 데이터를 prompt에 넣어주기 위해 변환
user_diet = user_sample[0]["diet"]
str_user_diet = ""
for category in user_diet:
  str_user_diet += category + ":"
  for i in user_diet[category]:
    str_user_diet += i + ","

#물어볼 밑반찬 사진
#사진을 또보내고싶으면 이 전체 플로우를 다시 시작하는 방향으로...?!
dish_img = "img_path"

#함수 실행
askdish_history = askdish(dish_img, str_user_diet)
