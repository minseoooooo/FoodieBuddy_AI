import os
import base64

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

os.environ["OPENAI_API_KEY"] = "API key"

def get_img_response_prompt(param_dict):
  system_message = """You are a kind expert in Korean cuisine. You will explain a korean side dish image to a user in English.
  Your explanation must be based on the user's dietary restrictions. Explain it in 3 or 4 sentences.
  
  Everytime you mention the dish name, YOU MUST USE THIS FORM: The dish name in English(The pronunciation of its korean name). 
  For example, "**Kimchi Stew(Kimchi Jjigae)**", "**Grilled Pork Belly(Samgyeopsal)**".
  
  YOU MUST SAY ONLY IN THE FORM BELOW INCLUDING LINEBREAKS.:
  "The basic information of the dish in one sentence.
  
  The main ingredients of the dish in one sentence. The information related to the user's dietary restrictions in one sentence.
  Whether it is suitable for the user or not.
  
  Several hashtags related to the dish."
  For example, "This dish is Braised Burdock Root(Ueongjorim), a type of side dish made with burdock root.
  
  It typically includes burdock root, soy sauce, sugar, sesame oil, and sometimes garlic. Since you avoid gluten, you should check if the soy sauce used in this preparation is gluten-free. 
  If it contains regular soy sauce, it might not be suitable for you.
  
  #healthy #side_dish #vegetable"
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

  # 밑반찬 답변 모델 - 파인 튜닝하면 여기에 쓸 모델 id가 바뀜
  model = ChatOpenAI(model = "gpt-4o")

  chain = get_img_response_prompt | model | StrOutputParser()
  response = chain.invoke({"diet": str_user_diet,
                         "image_url":f"data:image/jpeg;base64,{base64_img}"
                         }
                       )
  return response

def askdish(dish_img, str_user_diet):

  model = ChatOpenAI(model = "gpt-4o")
  chat_history = ChatMessageHistory()

  #대화 시작 멘트 - 밑반찬 설명
  dish_explain = get_img_response(dish_img, str_user_diet)
  print(f"FoodieBuddy:{dish_explain}")
  chat_history.add_ai_message(dish_explain)

  # askdish용 프롬프트
  askdish_prompt = f"""
  ## Instructions
  You are a kind expert in Korean cuisine. You will chat with a user in English to explain a korean side dish to the user based on the user's dietary restrictions.
  The user is a foreigner visiting a Korean restaurant in Korea.
  The user's dietary restrictions are {str_user_diet}. 
  
  Everytime you mention the dish name, YOU MUST USE THIS FORM: The dish name in English(The pronunciation of its korean name). 
  For example, "**Kimchi Stew(Kimchi Jjigae)**", "**Grilled Pork Belly(Samgyeopsal)**".

  Follow the steps below:
  1. Explain the dish from the image.
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
    user_message = input("You: ")
    if user_message.lower() == 'x':
      print("Chat ended.")
      break
    chat_history.add_user_message(user_message)

    response = chain.invoke({"messages":chat_history.messages})
    chat_history.add_ai_message(response.content)
    print(f"FoodieBuddy:{response.content}")

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
#사진을 또보내고싶으면 이 전체 플로우를 다시 시작
dish_img = "img_path"

#함수 실행
askdish_history = askdish(dish_img, str_user_diet)
