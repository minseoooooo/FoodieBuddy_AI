import os
import re
import requests
import xml.etree.ElementTree as ET

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from sshtunnel import SSHTunnelForwarder
import pymysql

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
  myKey = 'API key'
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
          else:
              ingredients = ingredients + ", " + ingredient

      return f"Ingredients of {dish_name} are "+ingredients

def dishimg_gen(dish_name):

  dish_name = dish_name.replace("[","").replace("]","")
  sd_prompt = f"A realistic image of {dish_name}"

  response = requests.post(
    f"https://api.stability.ai/v2beta/stable-image/generate/ultra",
    headers={
        "authorization": f"API key",
        "accept": "image/*"
    },
    files={"none": ''},
    data={
        "prompt": sd_prompt,
        "output_format": "png",
    },
	)

  if response.status_code == 200:
    filename = dish_name.lower().replace(" ", "")
    with open(f"./images/{filename}_test.png", 'wb') as file:
      file.write(response.content)

  else:
	  raise Exception(str(response.json()))

def recommendation(str_user_diet):
  model = ChatOpenAI(model="gpt-4o")
  chat_history = ChatMessageHistory()

recommend_prompt = f"""
  ## Instructions
  You are a kind expert in Korean cuisine. You will chat with a user in English to recommend a dish to the user based on the user's dietary restrictions and additional information.
  The user's dietary restrictions are {str_user_diet}. 
  
  Everytime you mention the dish name, YOU MUST USE THIS FORM: The dish name in English(The pronunciation of its korean name). 
  For example, "**Kimchi Stew(Kimchi Jjigae)**", "**Grilled Pork Belly(Samgyeopsal)**".
  
  Everytime you ask a question use linebreaks before the question.
  For example, "Hello! I'm excited to help you explore some delicious Korean cuisine. Please let me know what type of dish you're interested in trying!
  
  Are you looking for something spicy, mild, savory, or maybe a specific type like a soup or a noodle dish?"
  Or, "Hello! I'm excited to help you explore some delicious Korean cuisine. 
  
  Could you please let me know what type of dish you're interested in trying today?"
  
  FOLLOW THE STEPS BELOW:
  1. Start the conversation and ask which type of dish the user wants to try.
  2. Choose a dish based on the user's answer and user's dietary restrictions. Create the output as the form below:
     "[The pronunciation of the korean dish name (The dish name in English)]"
     For example, "[Kimchi Jjigae (Kimchi Stew)]"
  3. After you get the system's message about the ingredients, explain the chosen dish.
     YOU MUST SAY ONLY IN THE FORM BELOW INCLUDING LINEBREAKS.:
     "**The dish name in English(The pronunciation of its korean name)**
     The basic information of the dish in one sentence.
     
     The main ingredients of the dish in one sentence. The information related to the user's dietary restrictions in one sentence.
     
     Several hashtags related to the dish."
     
     For example, "**Kimchi Stew(Kimchi Jjigae)**
     It is a classic Korean dish that's perfect for those who enjoy a spicy and warming meal.
     
     It's made with fermented kimchi, tofu, and various vegetables, simmered together to create a rich and flavorful broth. It's traditionally made with pork, but it can easily be adapted to fit your dietary restrictions by leaving out the meat.
     
     #spicy #polular #warm"
  3. If the user don't like the suggestion, go back to step 2.
  4. If the user decide what to eat, end the conversation.  
  """

  prompt = ChatPromptTemplate.from_messages(
        [
            ("system", recommend_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

  chain = prompt | model

  while True:
    response = chain.invoke({"messages":chat_history.messages})
    chat_history.add_ai_message(response.content)
    
    if response.content.startswith("["):
      dish_name = re.search(r'\[([\D]+)\]', response.content).group(1)

      ingredients = search_ingredients(dish_name)
      ingredients_message = SystemMessage(content=ingredients)
      chat_history.add_message(ingredients_message)

      response = chain.invoke({"messages": chat_history.messages})
      chat_history.add_ai_message(response.content)

      dishimg_gen(dish_name)

    print(f"FoodieBuddy:{response.content}")

    user_message = input("You: ")
    if user_message.lower() == 'x':
      print("Chat ended.")
      break
    chat_history.add_user_message(user_message)

  return chat_history.messages



# EC2 연결 설정
ssh_host = ''
ssh_user = 'ubuntu'
ssh_key_file = 'foodiebuddy-ec2-key.pem'

# RDS 데이터베이스 설정
rds_host = ''
rds_port = 3306

server = SSHTunnelForwarder(
    (ssh_host, 22),
    ssh_username=ssh_user,
    ssh_pkey=ssh_key_file,
    remote_bind_address=(rds_host, rds_port),
    local_bind_address=('127.0.0.1', 3307)  # 로컬 머신에서 3307 포트를 통해 연결
)

try:
    server.start()
    #print(f"SSH 터널이 열렸습니다. 로컬 포트 {server.local_bind_port}을 통해 RDS에 연결할 수 있습니다.")
except Exception as e:
    #print(f"SSH 터널을 여는 동안 오류가 발생했습니다: {e}")
    import traceback
    traceback.print_exc()

connection = pymysql.connect(
    host='127.0.0.1',  # 로컬 호스트에서 접근
    user='admin',
    password='',
    db='foodiebuddy', # foodiebuddy: 스키마 이름
    port=server.local_bind_port  # SSH 터널의 포트 (server.local_bind_port 사용)
)

#유저 한명 식이제한 불러오기
cursor = connection.cursor()
cursor.execute("SHOW COLUMNS FROM user")
diets_list = cursor.fetchall()

cursor.execute("SELECT * FROM user Where user_id = 1")
result = cursor.fetchall()
user_diets = list(result[0])
user_info = {}

for i in range(len(diets_list)):
    if diets_list[i][0] not in ('user_id', 'email', 'password', 'username'):
        user_info[diets_list[i][0]] = user_diets[i]

str_user_diet = f"Religion: {user_info['religion']}, Vegetarian: {user_info['vegetarian']}. Details: "
for k, v in user_info.items():
    if k == 'vegetarian' or k == 'religion':
        continue
    if v is None or v == b'\x00':
        continue

    if v == b'\x01':
        str_user_diet += k + ', '
    else:
        str_user_diet += k + ':' + v + ', '

str_user_diet = str_user_diet[:-2]+'.'

recommend_history = recommendation(str_user_diet)
