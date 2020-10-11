from requests import Session


class HttpService:
    def __init__(self):
        self.session = Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36',
            'Cache-Control': 'no-cache'
        }

    def get(self, url):
        res = self.session.get(url)
        if res.status_code == 200:
            return res.content
        else:
            raise Exception('Invalid Server Response')
