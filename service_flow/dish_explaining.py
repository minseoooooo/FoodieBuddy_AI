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

def get_dish_explanation(gemini_prompt, img_path):
  client = Client("http://103.170.5.190:7860/")
  result = client.predict( api_name="/clear_history" )

  result = client.predict(gemini_prompt, img_path, "Default", api_name="/add_text_1" )
  result = client.predict( "MGM-34B-HD", 0.5, 0.5, 1024,
			"No", #'Generate Image'
			"No",	#'Use OCR'
			api_name="/http_bot_1")
  
  explanation = result[0][1]

  return explanation

cohere_prompt = f"""
## Instructions
You are a kind expert of korean dish. You will help a user to learn one dish based on user's dietary restrictions in a restaurant. The user's dietary restrictions are {user_diet}.
Perform the following steps:

1. After the user ask information of one dish, explain the dish based on the user's dietary restrictions.
2. If the user ask a question, answer it and ask if there are more questions.
3.1. If the user has more questions, answer it and go back to step 2.
3.2. If the user doesn't have any question left, start your overall output with "END" and create a sentence that ends the conversation.
"""

co = cohere.Client("API key")
chat_history=[{"role": "SYSTEM", "message": cohere_prompt}]

img_path = "/content/20240413010331.png"
gemini_prompt = f"Name the korean side dish in the image and explain its ingredients based on my dietary restirctions :{user_diet}."
gemini_response = get_dish_explanation(gemini_prompt,img_path)

print(f"FoodieBuddy: {gemini_response} \n")
chat_history.append({"role": "AI", "message": gemini_response})

while True:

  user_message = input("You: ")

  chat_history.append({"role": "USER", "message": user_message})

  response = co.chat(
    chat_history = chat_history,
    message = user_message,
    connectors = [{"id": "web-search"}]
  )

  if response.text.startswith("END"):
        print(f"FoodieBuddy:{response.text[3:]} \n")
        break

  else : print(f"FoodieBuddy: {response.text} \n")

  chat_history.append({"role": "AI", "message": response.text})
