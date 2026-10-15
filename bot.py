import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

# 初始化 NoneBot（会自动读取 .env / .env.{ENVIRONMENT}）
nonebot.init()

# 注册 OneBot V11 适配器（NapCat 走的就是这套协议）
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 加载 src/plugins 下的所有插件
nonebot.load_plugins("src/plugins")

if __name__ == "__main__":
    nonebot.run()
