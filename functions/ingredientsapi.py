import requests
import xml.etree.ElementTree as ET

def prettify(elem, level=0):
    indent = "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = "\n" + indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = "\n" + indent
        for subelem in elem:
            prettify(subelem, level + 1)
        if not subelem.tail or not subelem.tail.strip():
            subelem.tail = "\n" + indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = "\n" + indent
    return elem

myKey = 'API key'

url = 'http://apis.data.go.kr/1390802/AgriFood/FdFood/getKoreanFoodFdFoodList'
params ={'serviceKey' : myKey, 'service_Type' : 'xml', 'Page_No' : '1', 'Page_Size' : '20', 'food_Name' : '김치찌개' }

response = requests.get(url, params=params)
xml_data = response.content
root = ET.fromstring(xml_data)

prettify(root)
print(ET.tostring(root, encoding='utf8').decode('utf8'))

items = root.find('body/items').findall('item')

for item in items:
    fd_Code = item.find('fd_Code').text
    fd_Nm = item.find('fd_Nm').text
    fd_Grupp_Nm = item.find('fd_Grupp_Nm').text
    fd_Wgh = item.find('fd_Wgh').text
    food_List = item.find('food_List').findall('food')


    print(f"음식 이름: {fd_Nm}")
    print(f"음식 그룹: {fd_Grupp_Nm}")
    print("음식 세부 정보:")
    for food in food_List:
        food_Nm = food.find('food_Nm').text
        fd_Eng_Nm = food.find('fd_Eng_Nm').text
        print(f"    식재료 이름: {food_Nm}")
        print(f"    식재료 영문 이름: {fd_Eng_Nm}")
    print("------------------")
