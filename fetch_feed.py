#!/usr/bin/env python3
"""
My Daily Feed - 情報キュレーションツール
各ソースから最新情報を取得し、HTMLページを生成します。
英語コンテンツは自動で日本語に翻訳されます。
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from deep_translator import GoogleTranslator
import json
import html
import re
import time

JST = timezone(timedelta(hours=9))

# ===================== ソース定義 =====================

SOURCES = {
    "ochiai_note": {
        "name": "落合陽一",
        "type": "rss",
        "url": "https://note.com/ochyai/rss",
        "emoji": "🧠",
        "platform": "note",
    },
    "ochiai_yt": {
        "name": "落合陽一",
        "type": "youtube_search",
        "query": "落合陽一",
        "emoji": "🧠",
        "platform": "YouTube",
        "max_age_days": 90,
    },
    "karpathy_yt": {
        "name": "Andrej Karpathy",
        "type": "rss",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCXUPKJO5MZQN11PqgIvyuvQ",
        "emoji": "🤖",
        "platform": "YouTube",
    },
    "hardfork": {
        "name": "Hard Fork",
        "type": "rss",
        "url": "https://feeds.simplecast.com/l2i9YnTd",
        "emoji": "🎙️",
        "platform": "Podcast",
    },
    "every": {
        "name": "Every",
        "type": "scrape",
        "url": "https://every.to",
        "emoji": "📝",
        "platform": "Newsletter",
    },
    "moltbook": {
        "name": "Moltbook",
        "type": "scrape",
        "url": "https://www.moltbook.com",
        "emoji": "📚",
        "platform": "Community",
    },
    "amodei": {
        "name": "Dario Amodei",
        "type": "scrape",
        "url": "https://darioamodei.com",
        "emoji": "🏛️",
        "platform": "Blog",
    },
    "technium": {
        "name": "Kevin Kelly",
        "type": "rss",
        "url": "https://kk.org/thetechnium/feed/",
        "emoji": "🔮",
        "platform": "The Technium",
    },
    "tedchiang": {
        "name": "Ted Chiang",
        "type": "scrape",
        "url": "https://www.newyorker.com/contributors/ted-chiang",
        "emoji": "✍️",
        "platform": "The New Yorker",
    },
    "wired_jp": {
        "name": "WIRED JAPAN",
        "type": "rss",
        "url": "https://wired.jp/rssfeeder/",
        "emoji": "⚡",
        "platform": "WIRED",
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# ===================== 二十四節気・七十二候 =====================

# 2026年の二十四節気と七十二候（暦生活・国立天文台ベース）
SEKKI_72KOU = [
    # (開始月日, 終了月日, 節気, 候名, 候読み, 一言)
    ("01-05", "01-09", "小寒", "芹乃栄", "せりすなわちさかう", "芹が水辺で力強く育ち始める頃。七草がゆで新年の体を整えます"),
    ("01-10", "01-14", "小寒", "水泉動", "しみずあたたかをふくむ", "地中で凍った泉の水がわずかに動き出す頃。春の気配が地の底から"),
    ("01-15", "01-19", "小寒", "雉始雊", "きじはじめてなく", "雄の雉が鳴き始める頃。求愛の声が冬の野に響きます"),
    ("01-20", "01-24", "大寒", "款冬華", "ふきのはなさく", "蕗の薹が雪の下からそっと顔を出す頃。春一番の便りです"),
    ("01-25", "01-29", "大寒", "水沢腹堅", "さわみずこおりつめる", "沢の水が厚く張りつめて凍る頃。寒さの底ですが、光は日ごとに強く"),
    ("01-30", "02-03", "大寒", "鶏始乳", "にわとりはじめてとやにつく", "鶏が卵を産み始める頃。春に向けて生命が動き出します"),
    ("02-04", "02-08", "立春", "東風解凍", "はるかぜこおりをとく", "春風が吹いて、凍っていた川や地面の氷が少しずつ解け始める頃"),
    ("02-09", "02-13", "立春", "黄鶯睍睆", "うぐいすなく", "鶯が山里で美しい声でさえずり始める頃。春の訪れを告げる声"),
    ("02-14", "02-18", "立春", "魚上氷", "うおこおりをいずる", "氷が割れて、その隙間から魚が飛び跳ねる頃。水の中にも春が来ます"),
    ("02-19", "02-23", "雨水", "土脉潤起", "つちのしょううるおいおこる", "雪が雨に変わり、土が潤い始める頃。大地が目を覚まします"),
    ("02-24", "02-28", "雨水", "霞始靆", "かすみはじめてたなびく", "春霞がたなびき始める頃。遠くの景色がやわらかくにじみます"),
    ("03-01", "03-05", "雨水", "草木萌動", "そうもくめばえいずる", "草や木の芽が膨らんで萌え始める頃。いよいよ春本番が近づきます"),
    ("03-06", "03-10", "啓蟄", "蟄虫啓戸", "すごもりむしとをひらく", "冬ごもりの虫が土の中から出てくる頃。大地が目覚めます"),
    ("03-11", "03-15", "啓蟄", "桃始笑", "ももはじめてさく", "桃の花がほころび始める頃。花が咲くことを「笑う」と表す美しい表現"),
    ("03-16", "03-20", "啓蟄", "菜虫化蝶", "なむしちょうとなる", "青虫がさなぎから蝶へと生まれ変わる頃。春の変容です"),
    ("03-21", "03-25", "春分", "雀始巣", "すずめはじめてすくう", "雀が巣を作り始める頃。春の陽気に誘われて"),
    ("03-26", "03-30", "春分", "桜始開", "さくらはじめてひらく", "桜の花が咲き始める頃。日本の春の象徴です"),
    ("03-31", "04-04", "春分", "雷乃発声", "かみなりすなわちこえをはっす", "春雷が鳴り始める頃。空気が冬から春へと入れ替わります"),
    ("04-05", "04-09", "清明", "玄鳥至", "つばめきたる", "燕が南の国から渡ってくる頃。春の使者の到来です"),
    ("04-10", "04-14", "清明", "鴻雁北", "こうがんきたへかえる", "雁が北へ帰っていく頃。秋に来た渡り鳥との別れの季節"),
    ("04-15", "04-19", "清明", "虹始見", "にじはじめてあらわる", "春の雨上がりに虹が見え始める頃。空気が潤みます"),
    ("04-20", "04-24", "穀雨", "葭始生", "あしはじめてしょうず", "葦が芽吹き始める頃。水辺に緑が戻ります"),
    ("04-25", "04-29", "穀雨", "霜止出苗", "しもやんでなえいずる", "霜が降りなくなり、苗が育つ頃。田植えの準備が始まります"),
    ("04-30", "05-05", "穀雨", "牡丹華", "ぼたんはなさく", "牡丹の花が咲く頃。百花の王と呼ばれる華やかさ"),
    ("05-06", "05-10", "立夏", "蛙始鳴", "かわずはじめてなく", "蛙が鳴き始める頃。田んぼに元気な合唱が響きます"),
    ("05-11", "05-15", "立夏", "蚯蚓出", "みみずいずる", "ミミズが地上に出てくる頃。大地の恵みを支える生きもの"),
    ("05-16", "05-20", "立夏", "竹笋生", "たけのこしょうず", "筍が生えてくる頃。竹林に旬の味覚が実ります"),
    ("05-21", "05-25", "小満", "蚕起食桑", "かいこおきてくわをはむ", "蚕が桑の葉を盛んに食べ始める頃"),
    ("05-26", "05-30", "小満", "紅花栄", "べにばなさかう", "紅花が盛んに咲く頃。鮮やかな黄色が野に広がります"),
    ("05-31", "06-05", "小満", "麦秋至", "むぎのときいたる", "麦が熟して収穫を迎える頃。初夏の黄金色"),
    ("06-06", "06-10", "芒種", "螳螂生", "かまきりしょうず", "カマキリが生まれる頃。小さな命の営みが始まります"),
    ("06-11", "06-15", "芒種", "腐草為蛍", "くされたるくさほたるとなる", "蛍が飛び始める頃。夜の水辺にやさしい光が灯ります"),
    ("06-16", "06-20", "芒種", "梅子黄", "うめのみきばむ", "梅の実が黄色く色づく頃。梅雨の語源ともいわれます"),
    ("06-21", "06-25", "夏至", "乃東枯", "なつかれくさかるる", "夏枯草が枯れ始める頃。夏至を過ぎ、陽はゆっくりと短くなります"),
    ("06-26", "06-30", "夏至", "菖蒲華", "あやめはなさく", "菖蒲の花が咲く頃。雨に濡れた紫が美しい"),
    ("07-01", "07-06", "夏至", "半夏生", "はんげしょうず", "半夏が生える頃。田植えを終える目安とされます"),
    ("07-07", "07-11", "小暑", "温風至", "あつかぜいたる", "温かい風が吹き始める頃。本格的な夏の到来です"),
    ("07-12", "07-16", "小暑", "蓮始開", "はすはじめてひらく", "蓮の花が開き始める頃。早朝の池に清らかな美しさ"),
    ("07-17", "07-22", "小暑", "鷹乃学習", "たかすなわちわざをならう", "鷹の幼鳥が飛ぶことを覚える頃"),
    ("07-23", "07-28", "大暑", "桐始結花", "きりはじめてはなをむすぶ", "桐の花が実を結び始める頃"),
    ("07-29", "08-02", "大暑", "土潤溽暑", "つちうるおうてむしあつし", "土が湿り蒸し暑くなる頃。夏の暑さの盛りです"),
    ("08-03", "08-07", "大暑", "大雨時行", "たいうときどきにふる", "時折大雨が降る頃。夕立が暑さを和らげます"),
    ("08-08", "08-12", "立秋", "涼風至", "すずかぜいたる", "涼しい風が吹き始める頃。暦の上では秋の始まり"),
    ("08-13", "08-17", "立秋", "寒蝉鳴", "ひぐらしなく", "ひぐらしが鳴き始める頃。夕暮れにもの悲しい声が響きます"),
    ("08-18", "08-22", "立秋", "蒙霧升降", "ふかききりまとう", "深い霧が立ちこめる頃。朝晩にどこか秋の気配"),
    ("08-23", "08-27", "処暑", "綿柎開", "わたのはなしべひらく", "綿の萼が開く頃。ふわふわの綿が顔を出します"),
    ("08-28", "09-01", "処暑", "天地始粛", "てんちはじめてさむし", "暑さがようやく収まり始める頃。空が高くなります"),
    ("09-02", "09-07", "処暑", "禾乃登", "こくものすなわちみのる", "稲が実る頃。田んぼが黄金色に色づきます"),
    ("09-08", "09-12", "白露", "草露白", "くさのつゆしろし", "草に降りた露が白く光る頃。朝晩の冷え込みが増します"),
    ("09-13", "09-17", "白露", "鶺鴒鳴", "せきれいなく", "鶺鴒が鳴き始める頃。秋の気配が色濃くなります"),
    ("09-18", "09-22", "白露", "玄鳥去", "つばめさる", "燕が南へ帰っていく頃。春に来た使者との別れ"),
    ("09-23", "09-27", "秋分", "雷乃収声", "かみなりすなわちこえをおさむ", "雷が鳴らなくなる頃。空気が澄み始めます"),
    ("09-28", "10-02", "秋分", "蟄虫坏戸", "むしかくれてとをふさぐ", "虫が土の中に隠れて戸をふさぐ頃。冬支度の始まり"),
    ("10-03", "10-07", "秋分", "水始涸", "みずはじめてかるる", "田の水を抜いて稲刈りの準備をする頃"),
    ("10-08", "10-12", "寒露", "鴻雁来", "こうがんきたる", "雁が北から渡ってくる頃。秋の空に雁行の列"),
    ("10-13", "10-17", "寒露", "菊花開", "きくのはなひらく", "菊の花が咲き始める頃。秋の彩りです"),
    ("10-18", "10-22", "寒露", "蟋蟀在戸", "きりぎりすとにあり", "蟋蟀が戸口で鳴く頃。秋の夜長に虫の音が響きます"),
    ("10-23", "10-27", "霜降", "霜始降", "しもはじめてふる", "霜が初めて降りる頃。冬の足音が近づきます"),
    ("10-28", "11-01", "霜降", "霎時施", "こさめときどきふる", "小雨がしとしとと降る頃。晩秋の静かな雨"),
    ("11-02", "11-06", "霜降", "楓蔦黄", "もみじつたきばむ", "紅葉や蔦が色づく頃。山が燃えるような美しさに"),
    ("11-07", "11-11", "立冬", "山茶始開", "つばきはじめてひらく", "山茶花が咲き始める頃。冬の庭に彩りを添えます"),
    ("11-12", "11-16", "立冬", "地始凍", "ちはじめてこおる", "大地が凍り始める頃。冬が本格的にやってきます"),
    ("11-17", "11-21", "立冬", "金盞香", "きんせんかさく", "水仙の花が咲き始める頃。清楚な香りが漂います"),
    ("11-22", "11-26", "小雪", "虹蔵不見", "にじかくれてみえず", "虹を見かけなくなる頃。冬の空気は乾いて澄んでいます"),
    ("11-27", "12-01", "小雪", "朔風払葉", "きたかぜこのはをはらう", "北風が木の葉を吹き払う頃。冬枯れの景色"),
    ("12-02", "12-06", "小雪", "橘始黄", "たちばなはじめてきばむ", "橘の実が黄色く色づき始める頃"),
    ("12-07", "12-11", "大雪", "閉塞成冬", "そらさむくふゆとなる", "空が重く閉ざされ、本格的な冬が訪れる頃"),
    ("12-12", "12-16", "大雪", "熊蟄穴", "くまあなにこもる", "熊が冬眠のために穴に入る頃。山も静かに眠りにつきます"),
    ("12-17", "12-21", "大雪", "鱖魚群", "さけのうおむらがる", "鮭が群がって川を上る頃。命をつなぐ壮大な旅"),
    ("12-22", "12-26", "冬至", "乃東生", "なつかれくさしょうず", "夏枯草が芽を出す頃。冬至を過ぎ、陽が少しずつ長くなります"),
    ("12-27", "12-31", "冬至", "麋角解", "さわしかのつのおつる", "鹿の角が落ちる頃。新しい年への準備が始まります"),
    ("01-01", "01-04", "冬至", "雪下出麦", "ゆきわたりてむぎのびる", "雪の下で麦が芽を出す頃。見えないところで春への準備"),
]


def get_seasonal_message():
    """今日の日付に対応する七十二候の情報を返す"""
    now = datetime.now(JST)
    month_day = now.strftime("%m-%d")

    for start, end, sekki, kou_name, kou_reading, description in SEKKI_72KOU:
        # 年をまたぐケース（12月→1月）に対応
        if start <= end:
            if start <= month_day <= end:
                return sekki, kou_name, kou_reading, description
        else:
            if month_day >= start or month_day <= end:
                return sekki, kou_name, kou_reading, description

    return "立春", "東風解凍", "はるかぜこおりをとく", "春風が吹いて氷が解け始める頃"


# ===================== 翻訳 =====================

translator = GoogleTranslator(source="en", target="ja")


def is_english(text):
    """テキストが英語かどうかを簡易判定"""
    if not text:
        return False
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return ascii_chars / max(len(text), 1) > 0.8


def translate_to_japanese(text):
    """英語テキストを日本語に翻訳（無料のGoogle Translate使用）"""
    if not text or not is_english(text):
        return text
    try:
        if len(text) > 4500:
            text = text[:4500]
        result = translator.translate(text)
        return result if result else text
    except Exception as e:
        print(f"    ⚠️ 翻訳スキップ: {str(e)[:50]}")
        return text


# ===================== ユーティリティ =====================

def time_ago(dt):
    """日時を「◯時間前」「◯日前」などに変換"""
    if dt is None:
        return ""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    hours = diff.total_seconds() / 3600
    if hours < 1:
        return "たった今"
    elif hours < 24:
        return f"{int(hours)}時間前"
    elif hours < 48:
        return "1日前"
    elif hours < 168:
        return f"{int(hours / 24)}日前"
    else:
        weeks = int(hours / 168)
        if weeks <= 4:
            return f"{weeks}週間前"
        else:
            months = int(hours / 720)
            return f"{months}ヶ月前"


def clean_html(text):
    """HTMLタグを除去してプレーンテキストに"""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)[:300]


def parse_date(entry):
    """feedparserのentryから日時を取得"""
    for field in ["published_parsed", "updated_parsed"]:
        t = entry.get(field)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except:
                pass
    return None


def parse_youtube_time(time_text):
    """YouTubeの「3時間前」「2週間前」などの相対時間を解析"""
    now = datetime.now(timezone.utc)
    if not time_text:
        return None
    num_match = re.search(r'(\d+)', time_text)
    if not num_match:
        return None
    num = int(num_match.group(1))
    if '時間' in time_text or 'hour' in time_text:
        return now - timedelta(hours=num)
    elif '日' in time_text or 'day' in time_text:
        return now - timedelta(days=num)
    elif '週' in time_text or 'week' in time_text:
        return now - timedelta(weeks=num)
    elif 'か月' in time_text or 'month' in time_text:
        return now - timedelta(days=num * 30)
    elif '年' in time_text or 'year' in time_text:
        return now - timedelta(days=num * 365)
    return None


def extract_image_from_entry(entry):
    """RSSエントリからサムネイル画像URLを取得"""
    # media:thumbnail
    media_thumb = entry.get("media_thumbnail")
    if media_thumb and isinstance(media_thumb, list) and len(media_thumb) > 0:
        url = media_thumb[0].get("url", "")
        if url:
            return url

    # media:content
    media_content = entry.get("media_content")
    if media_content and isinstance(media_content, list):
        for mc in media_content:
            if mc.get("medium") == "image" or (mc.get("type", "").startswith("image")):
                return mc.get("url", "")

    # enclosure (podcasts often use this)
    enclosures = entry.get("enclosures", [])
    for enc in enclosures:
        if enc.get("type", "").startswith("image"):
            return enc.get("href", enc.get("url", ""))

    # image in feed content / summary
    summary = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""
    if summary:
        soup = BeautifulSoup(summary, "html.parser")
        img = soup.find("img", src=True)
        if img:
            return img["src"]

    return ""


# ===================== データ取得 =====================

def fetch_rss(source_key, source):
    """RSSフィードからアイテムを取得"""
    items = []
    max_age = source.get("max_age_days")
    try:
        print(f"  📡 RSS取得中: {source['name']} ({source['platform']})...")
        feed = feedparser.parse(source["url"])
        for entry in feed.entries[:10]:
            title = entry.get("title", "（タイトルなし）")
            link = entry.get("link", "")
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            pub_date = parse_date(entry)
            image = extract_image_from_entry(entry)

            # YouTube動画の場合、サムネイルを生成
            if not image and "youtube.com" in link:
                vid_match = re.search(r'v=([^&]+)', link)
                if vid_match:
                    image = f"https://i.ytimg.com/vi/{vid_match.group(1)}/mqdefault.jpg"

            if max_age and pub_date:
                age_days = (datetime.now(timezone.utc) - pub_date).days
                if age_days > max_age:
                    continue

            if len(items) >= 5:
                break

            items.append({
                "source_key": source_key,
                "title": title,
                "summary": summary,
                "link": link,
                "date": pub_date,
                "time_ago": time_ago(pub_date),
                "image": image,
                "original_lang": "en" if is_english(title) else "ja",
            })
        print(f"  ✅ {len(items)}件取得")
    except Exception as e:
        print(f"  ❌ エラー: {e}")
    return items


def search_youtube(source_key, source):
    """YouTube検索で動画を取得"""
    items = []
    query = source.get("query", "")
    max_age = source.get("max_age_days", 90)
    try:
        print(f"  🔍 YouTube検索中: {query}...")
        encoded_query = requests.utils.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}&sp=CAI%3D"
        resp = requests.get(url, headers=HEADERS, timeout=15)

        match = re.search(r'ytInitialData\s*=\s*({.*?});</script>', resp.text, re.DOTALL)
        if not match:
            print("  ⚠️ YouTube検索データが取得できませんでした")
            return items

        data = json.loads(match.group(1))

        try:
            contents = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
            for section in contents:
                video_items = section.get('itemSectionRenderer', {}).get('contents', [])
                for vi in video_items:
                    vr = vi.get('videoRenderer')
                    if not vr:
                        continue
                    vid = vr.get('videoId', '')
                    title = vr.get('title', {}).get('runs', [{}])[0].get('text', '')
                    channel = vr.get('ownerText', {}).get('runs', [{}])[0].get('text', '')
                    published = vr.get('publishedTimeText', {}).get('simpleText', '')
                    # サムネイル取得
                    thumbs = vr.get('thumbnail', {}).get('thumbnails', [])
                    thumb_url = thumbs[-1].get('url', '') if thumbs else ''
                    if not thumb_url and vid:
                        thumb_url = f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"

                    if not title or not vid:
                        continue
                    pub_date = parse_youtube_time(published)
                    if pub_date and max_age:
                        age_days = (datetime.now(timezone.utc) - pub_date).days
                        if age_days > max_age:
                            continue

                    items.append({
                        "source_key": source_key,
                        "title": title,
                        "summary": f"📺 {channel}" if channel else "",
                        "link": f"https://www.youtube.com/watch?v={vid}",
                        "date": pub_date,
                        "time_ago": time_ago(pub_date) if pub_date else published,
                        "image": thumb_url,
                        "original_lang": "ja",
                    })
                    if len(items) >= 5:
                        break
                if len(items) >= 5:
                    break
        except (KeyError, IndexError) as e:
            print(f"  ⚠️ YouTube検索のパースに失敗: {e}")

        print(f"  ✅ {len(items)}件取得")
    except Exception as e:
        print(f"  ❌ エラー: {e}")
    return items


def scrape_every():
    """Every.toのトップページから記事を取得"""
    items = []
    seen_titles = set()
    skip_words = ["subscribe", "sign up", "log in", "newsletter", "cookie",
                  "introducing every", "pricing", "about", "advertise",
                  "view all", "read more", "careers", "contact"]
    try:
        print(f"  🌐 スクレイピング中: Every...")
        resp = requests.get("https://every.to", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        candidates = []
        for heading in soup.find_all(["h1", "h2", "h3"]):
            a_tag = heading.find("a", href=True)
            if a_tag:
                candidates.append(a_tag)

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if re.match(r"^/[a-z-]+/[a-z0-9-]+", href) and len(href) > 15:
                candidates.append(a_tag)

        for a_tag in candidates:
            href = a_tag.get("href", "")
            if not href or href.startswith("#"):
                continue
            title_text = ""
            for child in a_tag.descendants:
                if isinstance(child, str):
                    title_text += child
            title_text = title_text.strip()
            title_text = re.sub(r'(?<=[A-Z])\s+(?=[a-z])', '', title_text)
            title_text = re.sub(r'\s+', ' ', title_text).strip()

            if not title_text or len(title_text) < 10 or len(title_text) > 200:
                continue
            if any(sw in title_text.lower() for sw in skip_words):
                continue
            title_lower = title_text.lower()
            if title_lower in seen_titles:
                continue
            seen_titles.add(title_lower)

            # 近くの画像を探す
            image = ""
            parent = a_tag.parent
            for _ in range(5):
                if parent is None:
                    break
                img = parent.find("img", src=True)
                if img and not img["src"].startswith("data:"):
                    image = img["src"]
                    break
                parent = parent.parent

            full_url = href if href.startswith("http") else f"https://every.to{href}"
            items.append({
                "source_key": "every",
                "title": title_text,
                "summary": "",
                "link": full_url,
                "date": None,
                "time_ago": "最近",
                "image": image,
                "original_lang": "en",
            })
            if len(items) >= 5:
                break
        print(f"  ✅ {len(items)}件取得")
    except Exception as e:
        print(f"  ❌ エラー: {e}")
    return items


def scrape_moltbook():
    """Moltbookのコンテンツを取得"""
    items = []
    try:
        print(f"  🌐 スクレイピング中: Moltbook...")
        requests.get("https://www.moltbook.com", headers=HEADERS, timeout=15)
        items.append({
            "source_key": "moltbook",
            "title": "Moltbook — AIエージェントのソーシャルネットワーク（ベータ版）",
            "summary": "AIエージェント同士が交流する新しいプラットフォーム。ベータ版のため投稿はまだ少なめです。",
            "link": "https://www.moltbook.com",
            "date": None,
            "time_ago": "",
            "image": "",
            "original_lang": "ja",
        })
        print(f"  ✅ {len(items)}件取得")
    except Exception as e:
        print(f"  ❌ エラー: {e}")
    return items


def scrape_amodei():
    """Dario Amodeiの個人ブログから記事を取得"""
    items = []
    try:
        print(f"  🌐 スクレイピング中: Dario Amodei...")
        resp = requests.get("https://darioamodei.com", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        # ブログのリンクを探す
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            title_text = a_tag.get_text(strip=True)

            if not title_text or len(title_text) < 10 or len(title_text) > 300:
                continue

            skip = ["home", "about", "contact", "subscribe", "menu", "navigation",
                    "dario amodei", "privacy", "terms"]
            if any(sw in title_text.lower() for sw in skip):
                continue

            full_url = href if href.startswith("http") else f"https://darioamodei.com{href}"

            # 画像を探す
            image = ""
            parent = a_tag.parent
            for _ in range(4):
                if parent is None:
                    break
                img = parent.find("img", src=True)
                if img and not img["src"].startswith("data:"):
                    img_src = img["src"]
                    if not img_src.startswith("http"):
                        img_src = f"https://darioamodei.com{img_src}"
                    image = img_src
                    break
                parent = parent.parent

            items.append({
                "source_key": "amodei",
                "title": title_text,
                "summary": "",
                "link": full_url,
                "date": None,
                "time_ago": "",
                "image": image,
                "original_lang": "en",
            })
            if len(items) >= 5:
                break

        print(f"  ✅ {len(items)}件取得")
    except Exception as e:
        print(f"  ❌ エラー: {e}")
    return items


def scrape_tedchiang():
    """Ted ChiangのNew Yorker記事を取得"""
    items = []
    try:
        print(f"  🌐 スクレイピング中: Ted Chiang (The New Yorker)...")
        resp = requests.get("https://www.newyorker.com/contributors/ted-chiang",
                          headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # 記事リンクのパターン
            if not re.search(r'/(magazine|culture|tech|news|science)/', href):
                continue

            title_text = a_tag.get_text(strip=True)
            if not title_text or len(title_text) < 10 or len(title_text) > 300:
                continue

            skip = ["subscribe", "sign in", "newsletter", "new yorker", "podcast",
                    "cartoon", "crossword", "goings on"]
            if any(sw in title_text.lower() for sw in skip):
                continue

            full_url = href if href.startswith("http") else f"https://www.newyorker.com{href}"

            # 画像
            image = ""
            parent = a_tag.parent
            for _ in range(5):
                if parent is None:
                    break
                img = parent.find("img", src=True)
                if img and not img["src"].startswith("data:"):
                    image = img["src"]
                    break
                parent = parent.parent

            items.append({
                "source_key": "tedchiang",
                "title": title_text,
                "summary": "",
                "link": full_url,
                "date": None,
                "time_ago": "",
                "image": image,
                "original_lang": "en",
            })
            if len(items) >= 5:
                break

        print(f"  ✅ {len(items)}件取得")
    except Exception as e:
        print(f"  ❌ エラー: {e}")
    return items


# ===================== 翻訳処理 =====================

def translate_items(all_items):
    """英語アイテムのタイトルとサマリーを日本語に翻訳"""
    en_items = [i for i in all_items if i.get("original_lang") == "en"]
    if not en_items:
        return

    print(f"\n🌐 英語コンテンツ {len(en_items)}件を日本語に翻訳中...")

    for i, item in enumerate(en_items):
        original_title = item["title"]
        translated_title = translate_to_japanese(original_title)
        if translated_title != original_title:
            item["title_ja"] = translated_title
            item["title_en"] = original_title
            print(f"  ✅ {i+1}/{len(en_items)}: {original_title[:40]}...")
        else:
            item["title_ja"] = None
            item["title_en"] = original_title

        if item["summary"] and is_english(item["summary"]):
            item["summary_ja"] = translate_to_japanese(item["summary"])
        else:
            item["summary_ja"] = item["summary"]

        time.sleep(0.3)

    print(f"  ✅ 翻訳完了")


# ===================== HTML生成 =====================

SOURCE_COLORS = {
    "ochiai_note": {"text": "#8B5E3C", "bg": "#FFF5ED", "badge_bg": "#F5E0CE"},
    "ochiai_yt":   {"text": "#8B5E3C", "bg": "#FFF5ED", "badge_bg": "#F5E0CE"},
    "karpathy_yt": {"text": "#3D7A3D", "bg": "#EFF8EF", "badge_bg": "#D4EDDA"},
    "hardfork":    {"text": "#B83B46", "bg": "#FFF0F1", "badge_bg": "#FADCE0"},
    "every":       {"text": "#2E6B96", "bg": "#EDF5FB", "badge_bg": "#D0E5F5"},
    "moltbook":    {"text": "#6B4E8B", "bg": "#F5F0FA", "badge_bg": "#E4D9F2"},
    "amodei":      {"text": "#2D6A4F", "bg": "#EDF7F0", "badge_bg": "#C8E6C9"},
    "technium":    {"text": "#5C6BC0", "bg": "#EDE7F6", "badge_bg": "#D1C4E9"},
    "tedchiang":   {"text": "#6D4C41", "bg": "#EFEBE9", "badge_bg": "#D7CCC8"},
    "wired_jp":    {"text": "#00695C", "bg": "#E0F2F1", "badge_bg": "#B2DFDB"},
}

def generate_html(all_items, output_path):
    """全アイテムからHTMLページを生成"""

    all_items.sort(key=lambda x: x["date"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    now_jst = datetime.now(JST)
    date_str = now_jst.strftime("%Y年%-m月%-d日")
    day_names = ["月", "火", "水", "木", "金", "土", "日"]
    day_str = day_names[now_jst.weekday()]
    time_str = now_jst.strftime("%-H:%M")
    hour = now_jst.hour

    if hour < 11:
        greeting = "おはよう、Matsuco\U0001F44B\U0001F3FB"
    elif hour < 17:
        greeting = "こんにちは、Matsuco\U0001F44B\U0001F3FB"
    else:
        greeting = "こんばんは、Matsuco\U0001F44B\U0001F3FB"

    # 二十四節気・七十二候
    sekki, kou_name, kou_reading, seasonal_desc = get_seasonal_message()

    source_counts = {}
    for item in all_items:
        sk = item["source_key"]
        source_counts[sk] = source_counts.get(sk, 0) + 1

    cards_html = ""
    for idx, item in enumerate(all_items):
        src = SOURCES.get(item["source_key"], {})
        is_en = item.get("original_lang") == "en"
        sc = SOURCE_COLORS.get(item["source_key"], {"text": "#888", "bg": "#F8F8F8", "badge_bg": "#EEE"})
        src_text = sc["text"]
        src_bg = sc["bg"]
        src_badge_bg = sc["badge_bg"]

        if is_en and item.get("title_ja"):
            display_title = item["title_ja"]
            original_line = f'<p class="original-text">原文: {html.escape(item.get("title_en", ""))}</p>'
        else:
            display_title = item["title"]
            original_line = ""

        display_summary = item.get("summary_ja", item["summary"]) if is_en else item["summary"]

        title_escaped = html.escape(display_title)
        summary_escaped = html.escape(display_summary)
        link = html.escape(item.get("link", "#"))
        badge_name = src.get("name", "")
        platform = src.get("platform", "")
        time_ago_str = item.get("time_ago", "")

        lang_badge = ""
        if is_en:
            lang_badge = '<span class="lang-badge">翻訳</span>'

        # 画像部分
        image_url = item.get("image", "")
        image_html = ""
        if image_url:
            image_escaped = html.escape(image_url)
            image_html = f'<div class="card-image"><img src="{image_escaped}" alt="" loading="lazy" onerror="this.parentElement.style.display=\'none\'"></div>'

        cards_html += f"""
        <a href="{link}" target="_blank" rel="noopener" class="card" data-source="{item['source_key']}" style="background: {src_bg}">
            {image_html}
            <div class="card-content">
                <div class="card-header">
                    <span class="source-badge" style="color: {src_text}; background: {src_badge_bg}">{badge_name}</span>
                    <span class="meta">{platform}　{time_ago_str}</span>
                </div>
                <h3 class="card-title">{title_escaped}</h3>
                {original_line}
                {"<p class='card-summary'>" + summary_escaped + "</p>" if summary_escaped else ""}
                <div class="card-footer">
                    {lang_badge}
                    <span class="read-more">つづきを読む →</span>
                </div>
            </div>
        </a>
        """

    # フィルターボタン
    filter_buttons = '<button class="filter-btn active" data-filter="all">ぜんぶ</button>'
    seen_source_names = set()
    for sk, src in SOURCES.items():
        count = source_counts.get(sk, 0)
        if count > 0 and src["name"] not in seen_source_names:
            seen_source_names.add(src["name"])
            sc = SOURCE_COLORS.get(sk, {"text": "#888", "bg": "#F8F8F8", "badge_bg": "#EEE"})
            total = sum(source_counts.get(k, 0) for k, s in SOURCES.items() if s["name"] == src["name"])
            filter_buttons += f'<button class="filter-btn" data-filter="{sk}" data-color="{sc["badge_bg"]}" data-text="{sc["text"]}" style="background: {sc["badge_bg"]}; color: {sc["text"]}">{src["name"]} <span style="opacity:0.6;font-size:10px">{total}</span></button>'

    en_count = sum(1 for i in all_items if i.get("original_lang") == "en")

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>けさの手帖 — {date_str}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400;500;600;700&family=Zen+Maru+Gothic:wght@400;500;700&display=swap');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: "Zen Maru Gothic", "Noto Serif JP", "Hiragino Kaku Gothic ProN", sans-serif;
    background: #FFFFFF;
    color: #3A3A3A;
    line-height: 1.8;
    letter-spacing: 0.03em;
}}

.container {{
    max-width: 640px;
    margin: 0 auto;
    padding: 52px 28px 80px;
}}

/* === ヘッダー === */
.header {{
    margin-bottom: 32px;
}}

.greeting {{
    font-size: 26px;
    font-weight: 700;
    color: #2A2A2A;
    line-height: 1.4;
    margin-bottom: 6px;
    font-family: "Noto Serif JP", serif;
}}

.header .date {{
    font-size: 13px;
    color: #999;
    letter-spacing: 0.08em;
}}

/* === 季節カード === */
.season-card {{
    background: linear-gradient(135deg, #fafaf5 0%, #f5f0e8 100%);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 32px;
    border: 1px solid #ece6d8;
}}

.season-sekki {{
    font-size: 11px;
    color: #A08060;
    letter-spacing: 0.1em;
    margin-bottom: 4px;
}}

.season-kou {{
    font-size: 18px;
    font-weight: 600;
    color: #5A4A3A;
    font-family: "Noto Serif JP", serif;
    margin-bottom: 2px;
}}

.season-reading {{
    font-size: 12px;
    color: #B0A090;
    margin-bottom: 8px;
}}

.season-desc {{
    font-size: 13px;
    line-height: 1.7;
    color: #7A6A5A;
}}

/* === 統計 === */
.stats {{
    display: flex;
    gap: 20px;
    margin-bottom: 20px;
    font-size: 12px;
    color: #AAA;
}}

/* === フィルター === */
.filters {{
    display: flex;
    gap: 8px;
    margin-bottom: 36px;
    flex-wrap: wrap;
}}

.filter-btn {{
    padding: 5px 14px;
    border: none;
    border-radius: 20px;
    background: #F5F5F5;
    color: #777;
    font-family: inherit;
    font-size: 12px;
    letter-spacing: 0.04em;
    cursor: pointer;
    transition: all 0.2s;
}}

.filter-btn.active {{
    background: #3A3A3A !important;
    color: #FFF !important;
}}

.filter-btn:hover:not(.active) {{
    opacity: 0.8;
}}

/* === カード === */
.feed {{
    display: flex;
    flex-direction: column;
    gap: 0px;
}}

.card {{
    display: flex;
    text-decoration: none;
    color: inherit;
    padding: 18px 20px;
    margin-bottom: 12px;
    border-radius: 12px;
    border: none;
    transition: transform 0.12s, box-shadow 0.12s;
    gap: 16px;
    align-items: flex-start;
}}

.card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}}

.card-image {{
    flex-shrink: 0;
    width: 100px;
    height: 72px;
    border-radius: 8px;
    overflow: hidden;
    background: rgba(0,0,0,0.04);
}}

.card-image img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}}

.card-content {{
    flex: 1;
    min-width: 0;
}}

.card-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 4px;
    gap: 12px;
}}

.source-badge {{
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.06em;
    padding: 2px 10px;
    border-radius: 12px;
    display: inline-block;
    white-space: nowrap;
}}

.meta {{
    font-size: 11px;
    color: #BBB;
    white-space: nowrap;
}}

.card-title {{
    font-size: 15px;
    font-weight: 500;
    line-height: 1.6;
    margin-bottom: 4px;
    color: #2A2A2A;
    font-family: "Noto Serif JP", serif;
}}

.card-summary {{
    font-size: 13px;
    line-height: 1.7;
    color: #888;
    margin-bottom: 6px;
}}

.original-text {{
    font-size: 11px;
    color: #BBB;
    margin-bottom: 4px;
    line-height: 1.4;
}}

.card-footer {{
    display: flex;
    align-items: center;
    gap: 10px;
}}

.lang-badge {{
    display: inline-block;
    padding: 1px 7px;
    border-radius: 10px;
    font-size: 10px;
    color: #4A7FA5;
    background: #EDF4F8;
    letter-spacing: 0.04em;
}}

.read-more {{
    font-size: 12px;
    color: #BBB;
    margin-left: auto;
}}

/* === フッター === */
.footer {{
    margin-top: 56px;
    padding-top: 24px;
    text-align: center;
    font-size: 11px;
    color: #CCC;
}}

.footer-dots {{
    letter-spacing: 0.4em;
    margin-bottom: 12px;
    color: #DDD;
}}

/* === モバイル === */
@media (max-width: 600px) {{
    .container {{ padding: 36px 18px 60px; }}
    .greeting {{ font-size: 22px; }}
    .card {{ padding: 14px 16px; margin-bottom: 10px; flex-direction: column; gap: 10px; }}
    .card-image {{ width: 100%; height: 160px; }}
    .card-title {{ font-size: 15px; }}
    .season-card {{ padding: 16px 18px; }}
    .season-kou {{ font-size: 16px; }}
}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="greeting">{greeting}</div>
        <div class="date">{date_str}（{day_str}）　{time_str} 取得</div>
    </div>

    <div class="season-card">
        <div class="season-sekki">{sekki}</div>
        <div class="season-kou">{kou_name}</div>
        <div class="season-reading">{kou_reading}</div>
        <div class="season-desc">{seasonal_desc}</div>
    </div>

    <div class="stats">
        <span>{len(all_items)}件</span>
        <span>{len([sk for sk in source_counts if source_counts[sk] > 0])}つの情報源</span>
        {"<span>" + str(en_count) + "件を翻訳</span>" if en_count > 0 else ""}
    </div>

    <div class="filters" id="filters">
        {filter_buttons}
    </div>

    <div class="feed" id="feed">
        {cards_html}
    </div>

    <div class="footer">
        <div class="footer-dots">· · ·</div>
        <p>けさの手帖 — 静かにあつめています</p>
    </div>
</div>

<script>
// ソース名のグループマッピング
const sourceGroups = {{}};
document.querySelectorAll('.filter-btn[data-filter]').forEach(btn => {{
    const f = btn.dataset.filter;
    if (f !== 'all') {{
        if (!sourceGroups[f]) sourceGroups[f] = [f];
    }}
}});
// 落合陽一のnoteとYTをグループ化
sourceGroups['ochiai_note'] = ['ochiai_note', 'ochiai_yt'];
sourceGroups['ochiai_yt'] = ['ochiai_note', 'ochiai_yt'];

document.getElementById('filters').addEventListener('click', e => {{
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    const filter = btn.dataset.filter;
    document.querySelectorAll('.filter-btn').forEach(b => {{
        b.classList.remove('active');
    }});
    btn.classList.add('active');
    const matchKeys = sourceGroups[filter] || [filter];
    document.querySelectorAll('.card').forEach(card => {{
        if (filter === 'all') {{
            card.style.display = '';
        }} else {{
            card.style.display = matchKeys.includes(card.dataset.source) ? '' : 'none';
        }}
    }});
}});
</script>
</body>
</html>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\n🎉 HTMLファイルを生成しました: {output_path}")


# ===================== メイン =====================

def main():
    print("=" * 50)
    print("📰 My Daily Feed - データ取得開始")
    print(f"⏰ {datetime.now(JST).strftime('%Y-%m-%d %H:%M')} JST")
    print("=" * 50)

    all_items = []

    for key, source in SOURCES.items():
        if source["type"] == "rss":
            items = fetch_rss(key, source)
            all_items.extend(items)
        elif source["type"] == "youtube_search":
            items = search_youtube(key, source)
            all_items.extend(items)
        elif key == "every":
            items = scrape_every()
            all_items.extend(items)
        elif key == "moltbook":
            items = scrape_moltbook()
            all_items.extend(items)
        elif key == "amodei":
            items = scrape_amodei()
            all_items.extend(items)
        elif key == "tedchiang":
            items = scrape_tedchiang()
            all_items.extend(items)
        time.sleep(0.5)

    print(f"\n📊 合計 {len(all_items)} 件のアイテムを取得")

    # 英語コンテンツを翻訳
    translate_items(all_items)

    output_path = "index.html"

    generate_html(all_items, output_path)

if __name__ == "__main__":
    main()
