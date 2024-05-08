!pip install cohere

import cohere

co = cohere.Client('API key')
response = co.chat(
  chat_history=[
    {"role": "USER", "message": "I am vegan and I can't eat mushrooms. I want to eat korean dish."},
  ],
  message="What can I eat for lunch based on my dietary restriction?",

  connectors=[{"id": "web-search"}]
)
print(response.text)
