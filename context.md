# Matsuco Daily Feed — プロジェクト引き継ぎメモ

## 概要

Matsuco（松嶋千尋さん）のための、パーソナライズされた日本語ニュース／コンテンツ集約ツール。
Python スクリプト (`fetch_feed.py`) を実行すると、複数のソースから最新情報を取得し、
翻訳済みのスタンドアロン HTML ファイル (`my-daily-feed.html`) を生成する。

**コンセプト**: 暮しの手帖のような素朴で温かみのあるデザイン。白背景、丸ゴシック＋明朝体、ソースごとの色分けカード。

---

## アーキテクチャ

```
fetch_feed.py（Python スクリプト）
    │
    ├─ RSS取得（feedparser）
    │    ├ 落合陽一 note
    │    ├ Andrej Karpathy YouTube
    │    ├ Hard Fork Podcast
    │    ├ Kevin Kelly / The Technium
    │    └ WIRED JAPAN
    │
    ├─ YouTube検索スクレイピング（requests + JSON parse）
    │    └ 落合陽一（他チャンネル出演）
    │
    ├─ Webスクレイピング（requests + BeautifulSoup）
    │    ├ Every.to
    │    ├ Moltbook（ベータ版、フォールバック表示）
    │    ├ Dario Amodei 個人ブログ
    │    └ Ted Chiang（The New Yorker 著者ページ）
    │
    ├─ 英語→日本語翻訳（deep-translator / Google Translate 無料）
    │
    └─ HTML生成（スタンドアロン、外部依存なし）
         └ my-daily-feed.html
```

---

## ソース一覧と取得方法

| ソース | 取得方法 | URL / 備考 |
|--------|----------|------------|
| 落合陽一 (note) | RSS | `https://note.com/ochyai/rss` |
| 落合陽一 (YouTube) | YouTube検索スクレイピング | 検索クエリ「落合陽一」、90日以内。ytInitialData JSON をパース |
| Andrej Karpathy | RSS (YouTube) | `https://www.youtube.com/feeds/videos.xml?channel_id=UCXUPKJO5MZQN11PqgIvyuvQ` |
| Hard Fork | RSS (Podcast) | `https://feeds.simplecast.com/l2i9YnTd` |
| Every | Webスクレイピング | `https://every.to` のトップページ。h1-h3内リンク＋記事パスを抽出 |
| Moltbook | フォールバック | ベータ版のため固定カード表示。`https://www.moltbook.com` |
| Dario Amodei | Webスクレイピング | `https://darioamodei.com` の記事リンクを抽出 |
| Kevin Kelly | RSS | `https://kk.org/thetechnium/feed/`（The Technium ブログ）|
| Ted Chiang | Webスクレイピング | `https://www.newyorker.com/contributors/ted-chiang` の記事リンク |
| WIRED JAPAN | RSS | `https://wired.jp/rssfeeder/` |

---

## デザイン仕様

### カラースキーム（ソースごと）

| ソース | テキスト色 | 背景色 | バッジ背景 |
|--------|-----------|--------|-----------|
| 落合陽一 | `#8B5E3C` | `#FFF5ED` | `#F5E0CE` |
| Karpathy | `#3D7A3D` | `#EFF8EF` | `#D4EDDA` |
| Hard Fork | `#B83B46` | `#FFF0F1` | `#FADCE0` |
| Every | `#2E6B96` | `#EDF5FB` | `#D0E5F5` |
| Moltbook | `#6B4E8B` | `#F5F0FA` | `#E4D9F2` |
| Dario Amodei | `#2D6A4F` | `#EDF7F0` | `#C8E6C9` |
| Kevin Kelly | `#5C6BC0` | `#EDE7F6` | `#D1C4E9` |
| Ted Chiang | `#6D4C41` | `#EFEBE9` | `#D7CCC8` |
| WIRED JAPAN | `#00695C` | `#E0F2F1` | `#B2DFDB` |

### フォント
- **Zen Maru Gothic**（丸ゴシック）— 本文
- **Noto Serif JP**（明朝体）— 見出し、挨拶

### 挨拶ロジック
- 11時前: `おはよう、Matsuco👋🏻`
- 11〜17時: `こんにちは、Matsuco👋🏻`
- 17時以降: `こんばんは、Matsuco👋🏻`

### 季節カード
- ページ上部に**二十四節気・七十二候**の情報を表示
- 72候すべてのデータを `SEKKI_72KOU` リストに内蔵（月日範囲、節気名、候名、読み、一言解説）
- 日付ベースで自動的に切り替わる

### 画像サムネイル
- RSS: `media_thumbnail`, `media_content`, `enclosure`, summary内の `<img>` から取得
- YouTube: `videoRenderer.thumbnail` または `https://i.ytimg.com/vi/{id}/mqdefault.jpg`
- スクレイピング: 記事リンク近くの `<img>` タグを親要素を遡って探索
- 読み込みエラー時は `onerror` で非表示

---

## 既知の問題・注意点

1. **Every.to のタイトル空白問題**: HTMLの `<span>` 構造により "A tlas" のような空白が入ることがある。`re.sub(r'(?<=[A-Z])\s+(?=[a-z])', '', title)` で修正済み
2. **Moltbook**: ベータ版で実コンテンツがほぼないため、固定のフォールバックカードを表示
3. **YouTube検索スクレイピング**: YouTube側の変更で `ytInitialData` の構造が変わる可能性あり
4. **翻訳レート制限**: `deep-translator` の Google Translate は無料だが、大量リクエストでブロックされる可能性あり。0.3秒のスリープを挟んでいる
5. **Karpathy YouTube**: 投稿頻度が低いため、RSS が空を返すことがある
6. **落合陽一 Threads**: API が公開されていないため未実装
7. **ダークモード**: ユーザー要望により削除済み（常に白背景）

---

## 今後の拡張案（未実装）

- Threads API 対応（落合陽一）
- X/Twitter 連携（Karpathy など）
- 定期実行の自動化（cron / GitHub Actions / Vercel）
- ホスティング（Vercel, Netlify, GitHub Pages）
- お気に入り・既読管理機能
- ソースの追加削除をconfig.jsonで管理

---

## 使い方

```bash
# 1. 依存ライブラリをインストール
pip install -r requirements.txt

# 2. スクリプトを実行
python fetch_feed.py

# 3. 生成された HTML をブラウザで開く
open my-daily-feed.html
```

出力ファイル `my-daily-feed.html` は完全にスタンドアロンで、サーバー不要。
ブラウザでそのまま開けます。

---

## ファイル構成

```
matsuco-daily-feed/
├── fetch_feed.py          # メインスクリプト（データ取得→翻訳→HTML生成）
├── requirements.txt       # Python依存ライブラリ
├── context.md             # このファイル（引き継ぎメモ）
└── my-daily-feed.html     # 生成される出力（実行後に作成される）
```
