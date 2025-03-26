"""
百度贴吧签到

export BDTB=""

cron: 30 6 * * *
"""
class CheckIn:
    pass

import hashlib
import json
import os
import re

import requests


class Tieba(CheckIn):
    name = "百度贴吧"

    def __init__(self, check_item):
        self.check_item = check_item

    @staticmethod
    def login_info(session):
        return session.get(url="https://zhidao.baidu.com/api/loginInfo").json()

    def valid(self, session):
        try:
            content = session.get(url="https://tieba.baidu.com/dc/common/tbs")
        except Exception as e:
            return False, f"登录验证异常,错误信息: {e}"
        data = json.loads(content.text)
        if data["is_login"] == 0:
            return False, "登录失败,cookie 异常"
        tbs = data["tbs"]
        user_name = self.login_info(session=session)["userName"]
        return tbs, user_name

    @staticmethod
    def tieba_list_more(session):
        content = session.get(
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
        except Exception:
            pn = 1
        next_page = 1
        pattern = re.compile(r".*?<a href=\"/f\?kw=.*?title=\"(.*?)\">")
        while next_page <= pn:
            tbname = pattern.findall(content.text)
            yield from tbname
            next_page += 1
            content = session.get(
                url=f"https://tieba.baidu.com/f/like/mylike?&pn={next_page}",
                timeout=(5, 20),
                allow_redirects=False,
            )

    def get_tieba_list(self, session):
        tieba_list = list(self.tieba_list_more(session=session))
        return tieba_list

    @staticmethod
    def sign(session, tb_name_list, tbs):
        success_count, error_count, exist_count, shield_count = 0, 0, 0, 0
        for tb_name in tb_name_list:
            md5 = hashlib.md5(
                f"kw={tb_name}tbs={tbs}tiebaclient!!!".encode()
            ).hexdigest()
            data = {"kw": tb_name, "tbs": tbs, "sign": md5}
            try:
                response = session.post(
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
            except Exception as e:
                print(f"贴吧 {tb_name} 签到异常,原因{str(e)}")
        msg = [
            {"name": "贴吧总数", "value": len(tb_name_list)},
            {"name": "签到成功", "value": success_count},
            {"name": "已经签到", "value": exist_count},
            {"name": "被屏蔽的", "value": shield_count},
            {"name": "签到失败", "value": error_count},
        ]
        return msg

    def main(self):
        tieba_cookie = {
            item.split("=")[0]: item.split("=")[1]
            for item in self.check_item.get("cookie").split("; ")
        }
        session = requests.session()
        requests.utils.add_dict_to_cookiejar(session.cookies, tieba_cookie)
        session.headers.update({"Referer": "https://www.baidu.com/"})
        tbs, user_name = self.valid(session=session)
        if tbs:
            tb_name_list = self.get_tieba_list(session=session)
            msg = self.sign(session=session, tb_name_list=tb_name_list, tbs=tbs)
            msg = [{"name": "帐号信息", "value": user_name}] + msg
        else:
            msg = [
                {"name": "帐号信息", "value": user_name},
                {"name": "签到信息", "value": "Cookie 可能过期"},
            ]
        msg = "\n".join([f"{one.get('name')}: {one.get('value')}" for one in msg])
        return msg


if __name__ == "__main__":
    APP_NAME = "百度贴吧签到"
    ENV_NAME = "BDTB"
    print(f'''
✨✨✨ {APP_NAME}签到✨✨✨
✨ 功能：
      签到
✨ 设置青龙变量：
export {ENV_NAME}参数值
export SCRIPT_UPDATE = 'False' 关闭脚本自动更新，默认开启
✨ 推荐cron：0 9 * * *
''')

    TIEBA_COOKIE = {
        "cookie": ENV_NAME
    }
    _check_item = TIEBA_COOKIE
    print(Tieba(check_item=_check_item).main())