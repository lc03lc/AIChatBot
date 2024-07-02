import requests

def get_trending_news():
    url = "https://tenapi.cn/v2/toutiaohot"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['data'][:10]
    else:
        return "请求错误，状态码：" + str(response.status_code)


