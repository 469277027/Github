import re
import scrapy
from github.items import langaugeitems, repoitems, useritems, resultcntitems


class GithubSpider(scrapy.Spider):

    name = "github"

    def start_requests(self):
        """ 爬虫入口
        
        func 参数:
            self.prepare_repos: 查询仓库类数据
            self.prepare_users: 查询用户类数据
            self.parse_language: 查询对应语言的数据
            self.parse_resultcnt: 查询返回结果数
        """
        func = self.parse_resultcnt
        urls = self.gen_urls(q="location", expr="UK", s="followers", stop=2)

        for url in urls:
            yield scrapy.Request(url=url, callback=func)


    def gen_urls(self, q=None, *, expr=None, s=None, start=1, stop, l="all"):
        """urls参数
        
        :param expr: str
            查询表达式
                forks, repos, stars, followers: "> 10000 < 100000" , ">= 1000"
                location: "China", "UA"
        
        :param q: str
            查询的内容
                Users 类: repos, followers, location
                Repos 类: forks, stars
        
        :param s: str ( 默认是 best match )
            查询的内容按某个值排序
                Users 类: repositories, followers
                Repos 类: stars, forks
        
        :param start: int ( 默认从第 1 页开始 )
            查询内容的起始页数
        
        :param stop: int
            查询内容的结束页数
        
        :param l: str ( 默认为全部语言 all )
            查询的语言
                Python, C++, C#, C, JavaScript, Java
        
        :return: 组装的 urls 列表
        """
        type = " "
        if q in ["stars", "forks"]:
            type = "Repositories"
        elif q == ["followers", "repos", "location"]:
            type = "Users"

        urls = ['https://github.com/search?p={p}&o=desc&q={q}:"{expr}"&s={s}&type={type}&l={l}&utf8=%E2%9C%93'.
                format(p=p, expr=expr, q=q, s=s, type=type, l=l)
                for p in range(start, stop)]
        return urls


    def prepare_repos(self, response):
        """ 解析仓库类查询的列表，并回调给下一级解析方法 """

        html = response.body.decode("utf-8")
        repos = re.findall(r'(?<="v-align-middle">)[\w\/\-\.]+', html)

        for repo in repos:
            yield scrapy.Request(url="https://github.com/{}".format(repo), callback=self.parse_forks_stars)


    def prepare_users(self, response):
        """ 解析用户类查询的列表，并回调给下一级解析方法 """

        html = response.body.decode("utf-8")
        users = re.findall(r'(?<=ml-2\">\n\s{6}<a href=\")\S+(?=\">)', html)

        for user in users:
            yield scrapy.Request(url="https://github.com{}".format(user), callback=self.parse_user)


    def parse_forks_stars(self, response):
        """ 解析具体仓库的 forks 和 stars 的数据 """

        html = response.body.decode("utf-8")
        repo_data = re.findall(r'(?<=aria-label=\")\d+', html)
        try:
            item = repoitems.Item()
            item['repo'] = response.url
            item['repo_watch'], item['repo_star'], item['repo_fork'] = repo_data
            yield item

        except ValueError as e:
            print("ValueError:{}".format(e))


    def parse_user(self, response):
        """ 解析具体用户的数据 """

        html = response.body.decode("utf-8")
        user_data = [data.strip() for data in re.findall(r'(?<=Counter\">)\s+\S+\s+', html)]
        try:
            item = useritems.Item()
            item['user'] = response.url
            item['user_repo'], item['user_star'], item['user_follower'], item['user_following'] = user_data
            yield item

        except ValueError as e:
            print("ValueError:{}".format(e))


    def parse_language(self, response):
        """ 解析特定查询下仓库的语言对应的数量 """

        html = response.body.decode("utf-8")
        language = re.findall(r'(?<=</span>\n\s{14})\S+', html)
        language_cnt = [l.replace(",", "") for l in re.findall(r'(?<=count\">)\d*\,?\d+', html)]

        for z in zip(language, language_cnt):
            try:
                item = langaugeitems.Item()
                item['language'], item['language_cnt'] = z
                yield item

            except ValueError as e:
                print("ValueError:{}".format(e))


    def parse_resultcnt(self, response):
        """ 解析特定查询下返回的结果数 """

        html = response.body.decode("utf-8")

        result1 = [s.replace(",", "") for s in
                   re.findall(r'\S+(?= available repository)', html)]
        result2 = [s.replace(",", "") for s in
                   re.findall(r'(?<=border-bottom pb-3\">\n\s{4}<h3>\n\s{4})\S+', html)]

        item = resultcntitems.Item()
        if result1:
            item['result_cnt'] = result1
        if result2:
            item['result_cnt'] = result2
        yield item
