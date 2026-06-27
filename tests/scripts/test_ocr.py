import requests

# 测试图片识字功能
url = "http://localhost:8000/api/v1/multimodal/image/ocr"

# 上传图片文件
with open('../img/jiemian.png', 'rb') as f:
    files = {'file': ('jiemian.png', f, 'image/png')}
    response = requests.post(url, files=files)

print("响应状态码:", response.status_code)
print("响应内容:", response.json())
