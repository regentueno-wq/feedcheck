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
    date_str = now_jst.strftime("%Y年%m月%d日")
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

    sekki, kou_name, kou_reading, seasonal_desc = get_seasonal_message()
    
    # ニュース項目の生成
    items_html = ""
    source_counts = {}
    en_count = 0
    for item in all_items:
        source = item.get("source", "不明")
        source_counts[source] = source_counts.get(source, 0) + 1
        if item.get("is_translated"):
            en_count += 1
        
        items_html += f"""
        <div class="item" data-source="{source}">
            <div class="item-meta">
                <span class="source-tag">{source}</span>
                <span class="time">{item['time_ago']}</span>
            </div>
            <a href="{item['link']}" class="item-title" target="_blank">{item['title']}</a>
            <div class="item-summary">{item['summary']}</div>
            <a href="{item['link']}" class="read-more" target="_blank">つづきを読む →</a>
        </div>
        """

    # フィルタボタンの生成
    filter_buttons = '<div class="filters" id="filters">'
    filter_buttons += '<button class="filter-btn active" data-filter="all">ぜんぶ</button>'
    for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        filter_buttons += f'<button class="filter-btn" data-filter="{source}">{source} <small>{count}</small></button>'
    filter_buttons += '</div>'

    # HTML全体の組み立て
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>けさの手帖 - {date_str}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400;500;600;700&family=Zen+Maru+Gothic:wght@400;500;700&display=swap');
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: "Zen Maru Gothic", "Noto Serif JP", serif; background: #FFFFFF; color: #3A3A3A; line-height: 1.8; letter-spacing: 0.03em; }}
            .container {{ max-width: 640px; margin: 0 auto; padding: 52px 28px 80px; }}
            .refresh-container {{ text-align: right; margin-bottom: 24px; }}
            .refresh-btn {{ padding: 6px 14px; border: 1px solid #ECE6D8; background: #FAF9F6; color: #A08060; border-radius: 20px; font-size: 11px; cursor: pointer; transition: all 0.3s ease; }}
            .refresh-btn:hover {{ background: #F0EDE5; }}
            .header {{ margin-bottom: 48px; border-bottom: 1px solid #F5F2EB; padding-bottom: 24px; }}
            .greeting {{ font-size: 24px; font-weight: 500; color: #5C5446; margin-bottom: 8px; }}
            .date {{ font-size: 13px; color: #9A9284; }}
            .season-card {{ background: #FAF9F6; border-radius: 16px; padding: 32px; margin-bottom: 48px; }}
            .season-sekki {{ font-size: 13px; color: #A08060; margin-bottom: 8px; font-weight: 500; }}
            .season-kou {{ font-size: 22px; color: #5C5446; margin-bottom: 8px; font-weight: 600; }}
            .season-reading {{ font-size: 12px; color: #B0A898; margin-bottom: 16px; }}
            .season-desc {{ font-size: 15px; color: #7C7466; line-height: 1.8; }}
            .filters {{ margin-bottom: 32px; display: flex; flex-wrap: wrap; gap: 8px; }}
            .filter-btn {{ padding: 6px 16px; border-radius: 20px; border: none; background: #F0F0F0; font-size: 12px; cursor: pointer; transition: 0.2s; }}
            .filter-btn.active {{ background: #4A4A4A; color: white; }}
            .item {{ margin-bottom: 40px; }}
            .item-meta {{ margin-bottom: 8px; font-size: 11px; }}
            .source-tag {{ background: #E0E0E0; padding: 2px 8px; border-radius: 4px; margin-right: 8px; }}
            .item-title {{ display: block; font-size: 18px; font-weight: 600; color: #3A3A3A; text-decoration: none; margin-bottom: 8px; line-height: 1.4; }}
            .item-summary {{ font-size: 14px; color: #666; margin-bottom: 8px; }}
            .read-more {{ font-size: 12px; color: #A0A0A0; text-decoration: none; }}
            .footer {{ margin-top: 80px; text-align: center; color: #B0A898; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="refresh-container">
                <button class="refresh-btn" onclick="triggerRefresh()">手帖を最新に更新する</button>
            </div>
            
            <div class="header">
                <div class="greeting">{greeting}</div>
                <div class="date">{date_str} ({day_str})  {time_str} 取得</div>
            </div>
            
            <div class="season-card">
                <div class="season-sekki">{sekki}</div>
                <div class="season-kou">{kou_name}</div>
                <div class="season-reading">{kou_reading}</div>
                <div class="season-desc">{seasonal_desc}</div>
            </div>

            <div class="stats" style="font-size: 12px; color: #B0A898; margin-bottom: 24px;">
                {len(all_items)}件のニュース
            </div>

            {filter_buttons}
            <div id="items-container">
                {items_html}
            </div>

            <div class="footer">
                <p>・ ・ ・</p>
                <p>けさの手帖 － 静かにあつめています</p>
            </div>
        </div>

        <script>
        function triggerRefresh() {{
            const hookUrl = "https://api.netlify.com/build_hooks/698fddd90daa0f765f996b27";
            if (confirm("最新の情報を取得しにいきます。完了まで1〜2分かかりますが、よろしいですか？")) {{
                fetch(hookUrl, {{ method: 'POST' }})
                    .then(() => alert("職人が作業を開始しました！少し待ってから再読み込みしてください。"))
                    .catch(() => alert("エラーが発生しました。"));
            }}
        }}

        // フィルタ機能
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const filter = btn.dataset.filter;
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('.item').forEach(item => {{
                    item.style.display = (filter === 'all' || item.dataset.source === filter) ? 'block' : 'none';
                }});
            }});
        }});
        </script>
    </body>
    </html>
    """

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

def fetch_all_feeds():
    """画像付きで全ソースからニュースを取得する完全版"""
    import feedparser
    from bs4 import BeautifulSoup
    from datetime import datetime, timezone
    
    # Matsucoさん専用のソース一覧
    RSS_URLS = {
        "WIRED JAPAN": "https://wired.jp/rss/rssf/",
        "Every": "https://every.to/feed",
        "Hard Fork": "https://feeds.simplecast.com/K_9_S6f_",
        "Kevin Kelly": "https://kk.org/the-technium/feed/",
        "Moltbook": "https://moltbook.xyz/feed",
        "落合陽一": "https://note.com/ochyai/rss",
        "Anthropic": "https://www.anthropic.com/index.xml", # ダリオ・アモデイ
        "Ted Chiang": "https://muckrack.com/ted-chiang/articles.rss" # テッド・チャン
    }
    
    all_items = []
    for name, url in RSS_URLS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                # 画像の抽出
                img_url = ""
                # 1. RSSのタグ(media:content)から探す
                if 'media_content' in entry:
                    img_url = entry.media_content[0]['url']
                # 2. 本文(summaryやcontent)の中の<img>タグから探す
                if not img_url:
                    soup = BeautifulSoup(entry.get("summary", "") + entry.get("description", ""), 'html.parser')
                    img = soup.find('img')
                    if img: img_url = img['src']

                all_items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get("summary", "")[:120] + "...",
                    "date": datetime(*entry.published_parsed[:6], tzinfo=timezone.utc) if hasattr(entry, 'published_parsed') else None,
                    "source": name,
                    "image": img_url,
                    "time_ago": "最近"
                })
        except:
            continue
    return all_items

def generate_html(all_items, output_path):
    # (中略: 計算部分は同じです)
    
    # ニュース項目の生成（画像ありVer）
    items_html = ""
    for item in all_items:
        img_tag = f'<img src="{item["image"]}" class="item-img">' if item["image"] else ""
        items_html += f"""
        <div class="item" data-source="{item['source']}">
            {img_tag}
            <div class="item-meta">
                <span class="source-tag tag-{item['source'].replace(' ', '-')}">{item['source']}</span>
                <span class="time">{item['time_ago']}</span>
            </div>
            <a href="{item['link']}" class="item-title" target="_blank">{item['title']}</a>
            <div class="item-summary">{item['summary']}</div>
        </div>
        """

    # --- デザインの復活（色分けCSS） ---
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <style>
            /* ソースごとの色分け */
            .tag-WIRED-JAPAN {{ background: #E0F2F1; color: #00796B; }}
            .tag-落合陽一 {{ background: #FCE4EC; color: #C2185B; }}
            .tag-Hard-Fork {{ background: #FFF3E0; color: #E65100; }}
            .tag-Every {{ background: #E3F2FD; color: #1976D2; }}
            .tag-Moltbook {{ background: #F3E5F5; color: #7B1FA2; }}
            .tag-Anthropic {{ background: #EFEBE9; color: #5D4037; }}
            
            /* 画像のスタイル */
            .item-img {{ width: 100%; height: 200px; object-fit: cover; border-radius: 12px; margin-bottom: 16px; }}
            .item {{ margin-bottom: 52px; border-bottom: 1px solid #F5F2EB; padding-bottom: 32px; }}
            /* (他の既存スタイルはそのまま維持) */
        </style>
        ...
    </head>
    ...
    </html>
    """
    # (以下、保存処理とtriggerRefreshは以前と同じ)
