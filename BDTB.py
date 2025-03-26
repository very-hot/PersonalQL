import hashlib
import json
import os
import re
import requests
import urllib3

# 禁用不安全请求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 定义基础类
class CheckIn:
    pass

# 解析环境变量中的 cookie
def parse_cookie(cookie_str):
    """
    解析 cookie 字符串为字典
    :param cookie_str: cookie 字符串
    :return: 解析后的 cookie 字典
    """
    cookie_dict = {}
    for item in cookie_str.split("; "):
        if "=" in item:
            key, value = item.split("=", 1)
            cookie_dict[key] = value
    return cookie_dict

# 百度贴吧签到类
class Tieba(CheckIn):
    name = "百度贴吧"

    def __init__(self, check_item):
        self.check_item = check_item
        self.session = requests.session()
        self.session.headers.update({"Referer": "https://www.baidu.com/"})
        requests.utils.add_dict_to_cookiejar(self.session.cookies, self.check_item)

    def login_info(self):
        """
        获取登录信息
        :return: 登录信息的 JSON 数据
        """
        try:
            return self.session.get(url="https://zhidao.baidu.com/api/loginInfo").json()
        except requests.RequestException as e:
            print(f"获取登录信息失败，错误信息: {e}")
            return {}

    def valid(self):
        """
        验证登录状态并获取 tbs 和用户名
        :return: tbs 和用户名
        """
        try:
            content = self.session.get(url="https://tieba.baidu.com/dc/common/tbs")
            data = content.json()
            if data["is_login"] == 0:
                return False, "登录失败, cookie 异常"
            tbs = data["tbs"]
            user_name = self.login_info().get("userName", "")
            return tbs, user_name
        except (requests.RequestException, json.JSONDecodeError) as e:
            return False, f"登录验证异常, 错误信息: {e}"

    def tieba_list_more(self):
        """
        生成关注的贴吧列表
        :return: 生成器，返回关注的贴吧名称
        """
        try:
            content = self.session.get(
                url="https://tieba.baidu.com/f/like/mylike?&pn=1",
                timeout=(5, 20),
                allow_redirects=False,
            )
            try:
                pn = int(
                    re.match(
                        r".*/f/like/mylike\?&pn=(.*?)\">尾页.*", content.text, re.S | re.I
                    ).group(1)
                )
            except (AttributeError, ValueError):
                pn = 1
            next_page = 1
            pattern = re.compile(r".*?<a href=\"/f\?kw=.*?title=\"(.*?)\">")
            while next_page <= pn:
                tbname = pattern.findall(content.text)
                yield from tbname
                next_page += 1
                content = self.session.get(
                    url=f"https://tieba.baidu.com/f/like/mylike?&pn={next_page}",
                    timeout=(5, 20),
                    allow_redirects=False,
                )
        except requests.RequestException as e:
            print(f"获取贴吧列表失败，错误信息: {e}")

    def get_tieba_list(self):
        """
        获取关注的贴吧列表
        :return: 关注的贴吧名称列表
        """
        return list(self.tieba_list_more())

    def sign(self, tb_name_list, tbs):
        """
        对贴吧列表进行签到操作
        :param tb_name_list: 贴吧名称列表
        :param tbs: tbs 信息
        :return: 签到结果信息
        """
        success_count, error_count, exist_count, shield_count = 0, 0, 0, 0
        for tb_name in tb_name_list:
            md5 = hashlib.md5(
                f"kw={tb_name}tbs={tbs}tiebaclient!!!".encode()
            ).hexdigest()
            data = {"kw": tb_name, "tbs": tbs, "sign": md5}
            try:
                response = self.session.post(
                    url="https://c.tieba.baidu.com/c/c/forum/sign",
                    data=data,
                    verify=False,
                ).json()
                if response["error_code"] == "0":
                    success_count += 1
                elif response["error_code"] == "160002":
                    exist_count += 1
                elif response["error_code"] == "340006":
                    shield_count += 1
                else:
                    error_count += 1
            except (requests.RequestException, json.JSONDecodeError) as e:
                print(f"贴吧 {tb_name} 签到异常, 原因: {e}")
        msg = [
            {"name": "贴吧总数", "value": len(tb_name_list)},
            {"name": "签到成功", "value": success_count},
            {"name": "已经签到", "value": exist_count},
            {"name": "被屏蔽的", "value": shield_count},
            {"name": "签到失败", "value": error_count},
        ]
        return msg

    def main(self):
        """
        主函数，执行签到流程
        :return: 签到结果信息
        """
        tbs, user_name = self.valid()
        if tbs:
            tb_name_list = self.get_tieba_list()
            msg = self.sign(tb_name_list, tbs)
            msg = [{"name": "帐号信息", "value": user_name}] + msg
        else:
            msg = [
                {"name": "帐号信息", "value": user_name},
                {"name": "签到信息", "value": "Cookie 可能过期"},
            ]
        msg = "\n".join([f"{one.get('name')}: {one.get('value')}" for one in msg])
        return msg

if __name__ == "__main__":
    APP_NAME = "百度贴吧"
    BDTB_ENV_NAME = 'BDTB'
    bdtb_cookie_str = os.environ.get(BDTB_ENV_NAME)

    if not bdtb_cookie_str:
        print(f"未填写{BDTB_ENV_NAME}变量，请在环境变量中配置该变量。")
        exit()

    bdtb_cookie = parse_cookie(bdtb_cookie_str)

    print(f'''
✨✨✨ {APP_NAME}签到✨✨✨
✨ 功能：
      签到
✨ 设置青龙变量：
export {BDTB_ENV_NAME}="这里填写你的 cookie"
export SCRIPT_UPDATE = 'False' 关闭脚本自动更新，默认开启
✨ 推荐cron：0 9 * * *
''')

    tieba = Tieba(bdtb_cookie)
    print(tieba.main())