import os
import re
import requests
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

os.environ["OPENAI_API_KEY"] = "API key"

def search_ingredients(dish_name):

  model = ChatOpenAI()

  chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "Translate a korean dish name in korean without any explanation. Your answer MUST be a one korean word. Examples - Q:Kimchi jjigae A:김치찌개, Q:Tteokbokki A:떡볶이"),
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

  if result_msg_element is not None and result_msg_element.text == '요청 데이터 없음':
      return ""
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

      return "Main ingredients are "+ingredients

def google_search(query):
  search_url = f"https://serpapi.com/search.json?q={query}&api_key=apikey"
  response = requests.get(search_url)
  return response.json()

def scrape_website(url):
  response = requests.get(url)
  soup = BeautifulSoup(response.content, 'html.parser')
  directions_section = soup.find('h2', string='Directions')  # 'Directions' 섹션 찾기
  recipe_list = directions_section.find_all_next('ol')  # 모든 <ol> 찾기
  recipe = ""

  if directions_section is not None:
      recipe_list = directions_section.find_all_next('ol')  # 모든 <ol> 찾기

      for i in range(len(recipe_list)):
        if i == len(recipe_list)-1: break
        list_items = recipe_list[i].find_all('li')  # <ol> 안의 모든 <li> 추출
        recipe += f"\n#{i+1}"
        for i, item in enumerate(list_items, 1):
           recipe += f"\n{i}. {item.get_text(strip=True)}"

  return recipe

def search_recipe(dish_name):
  search_results = google_search(f"How to cook {dish_name}")
  url = next((result['link'] for result in search_results['organic_results'] if result['link'].startswith('https://www.maangchi.com')), None)

  if url is None:
      return ""

  recipe = scrape_website(url)

  return "Generate the image based on the recipe below:" + recipe

def dishimg_gen(dish_name):

  dish_name = dish_name.replace("[","").replace("]","")
  sd_prompt = f"A realistic image of {dish_name}"

  sd_prompt += search_ingredients(dish_name)
  sd_prompt += search_recipe(dish_name)

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
  For example, "Kimchi Stew(Kimchi Jjigae)", "Grilled Pork Belly(Samgyeopsal)".
  
  Follow the steps below:
  1. Start the conversation and ask which type of dish the user wants to try.
  2. Based on the user's answer and user's dietary restrictions, suggest a dish what the user can eat for the meal. 
     In this step, YOU MUST START YOUR OUTPUT WITH "[THE DISH NAME IN ENGLISH]". Then explain the dish in detail. For example, "[Kimchi Stew] Kimchi Stew(Kimchi Jjigae) is ...(continue)...."
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
      dishimg_gen(dish_name)
      response.content = response.content[len(dish_name)+2:].lstrip()

    print(f"FoodieBuddy:{response.content}")

    user_message = input("You: ")
    if user_message.lower() == 'x':
      print("Chat ended.")
      break
    chat_history.add_user_message(user_message)

  return chat_history.messages

user_sample = [
    {"name": "John",
     "diet":{"meat": ["red meat", "other meat"],
              "dairy": ["milk"],
              "seafood" : ["shrimp"],
              "gluten(wheat)" : []
            }},
    {"name": "Julia",
     "diet":{"meat": ["red meat"],
              "dairy": ["milk","cheese"],
              "honey" : [],
              "nuts" : ["peanuts"],
              "gluten(wheat)" : [],
              "vegetables" : ["tomato"]
            }},
             ]

user_diet = user_sample[0]["diet"]
str_user_diet = ""

for category in user_diet:
  str_user_diet += category + ":"
  for i in user_diet[category]:
    str_user_diet += i + ","

recommend_history = recommendation(str_user_diet)
