from DrissionPage import ChromiumPage
from DrissionPage.common import Keys
import csv
import time
import re
import os

# ================= 配置 =================
USER_ID = '' 
# =======================================

def clean_html(html_text):
    if not html_text: return ""
    text = str(html_text).replace('<br>', '\n').replace('<br/>', '\n')
    pattern = re.compile(r'<[^>]+>', re.S)
    text = pattern.sub('', text)
    return text.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>').strip()

def get_desktop_path():
    """获取当前用户的桌面路径"""
    return os.path.join(os.path.expanduser("~"), 'Desktop')

def fetch_zhihu_fast_desktop():
    # 1. 设置保存路径到桌面
    desktop_dir = get_desktop_path()
    file_name = f'{USER_ID}_data.csv'
    full_path = os.path.join(desktop_dir, file_name)

    # 2. 启动浏览器
    page = ChromiumPage()
    page.set.window.max() # 窗口最大化
    page.get(f'https://www.zhihu.com/people/{USER_ID}')
    
    print(f"正在打开主页，准备保存到: {full_path}")

    # 3. 登录检测
    if 'signin' in page.url or '登录' in page.title:
        print(">>> 请扫码登录...")
        while 'signin' in page.url:
            time.sleep(1)
        print(">>> 登录成功！")
        time.sleep(2)

    # 4. 开启监听
    page.listen.start('api/v3/moments')

    # 5. 激活窗口焦点 (点击页面中间，防止按键无效)
    try:
        page.ele('tag:body').click(by_js=True)
    except:
        pass

    print(f"==================================================")
    print(f" 🚀 极速抓取模式启动")
    print(f" 📂 文件将保存在桌面: {file_name}")
    print(f"==================================================")

    with open(full_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['类型', '标题', '内容', '作者', '链接', '时间'])
        
        total_count = 0
        empty_rounds = 0
        
        while True:
            # ============================================
            # 🔥 性能优化核心：模拟按下 "End" 键
            # End 键直接跳到页面最底部，不消耗计算资源，不卡顿
            # ============================================
            try:
                page.actions.type(Keys.END)
            except:
                # 如果按键报错，尝试用 JS 兜底
                page.run_js('window.scrollTo(0, document.body.scrollHeight)')

            # 等待加载 (知乎加载需要时间)
            time.sleep(1.5) 
            
            # 微调：往上回滚一点点再滚下去，防止加载圈卡死
            # 这种“抖动”能有效触发懒加载
            page.scroll.up(100)
            time.sleep(0.5)
            page.scroll.down(100)

            # ============================================
            # 👂 接收数据 (只处理新包)
            # ============================================
            packet_found = False
            
            # wait 方法：等待新数据包出现，最多等 5 秒
            # 这样网络卡的时候它会自动多等一会儿，不会漏数据
            if page.listen.wait(timeout=5):
                for packet in page.listen.steps():
                    if packet.response.status != 200: continue
                    try:
                        data = packet.response.body
                        items = data.get('data', [])
                        if not items: continue

                        for item in items:
                            if item.get('verb') != 'MEMBER_VOTEUP_ANSWER': continue
                            target = item.get('target', {})
                            
                            title = target.get('question', {}).get('title', '无标题')
                            # 优先获取纯文本内容
                            raw_content = target.get('content') or target.get('excerpt')
                            content = clean_html(raw_content)
                            author = target.get('author', {}).get('name', '匿名')
                            link = f"https://www.zhihu.com/question/{target.get('question', {}).get('id')}/answer/{target.get('id')}"
                            t_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item.get('created_time')))

                            writer.writerow(['回答', title, content, author, link, t_time])
                            total_count += 1
                            packet_found = True
                            print(f"[{total_count}] {title[:15]}...")
                    except: pass
            
            # ============================================
            # 🛑 结束判断
            # ============================================
            if packet_found:
                empty_rounds = 0
            else:
                empty_rounds += 1
                print(f"未刷新到新内容... ({empty_rounds}/8)")
            
            if empty_rounds >= 8:
                if "没有更多" in page.html or "End of" in page.html:
                    print(">>> 页面显示已到底。")
                    break
                else:
                    print(">>> 连续多次无数据，结束抓取。")
                    break

    print(f"\n✅ 抓取结束！共 {total_count} 条。")
    print(f"📂 请去桌面查看文件: {file_name}")

if __name__ == '__main__':
    fetch_zhihu_fast_desktop()