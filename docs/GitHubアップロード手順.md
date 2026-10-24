# はじめての GitHub アップロード手順（Ren'Py プロジェクト用）

対象リポジトリ: https://github.com/369nightcore/Ren-py

やり方は2通りあります。**パソコンの操作に慣れていなければ A（ブラウザだけで完結）** がおすすめです。

---

## 準備: 上げるもの / 上げないもの

### 上げるもの
```
game/
├── script.rpy           ← メインのスクリプト
├── story_clubs.rpy      ← 今回のエラーが出ているファイル
├── options.rpy
├── gui.rpy
├── screens.rpy
├── images/  audio/  gui/ fonts/ など
```

### 上げないもの（Ren'Py が自動生成するゴミ）
```
game/cache/          ... 起動するたびに作られるキャッシュ
game/saves/          ... あなたのセーブデータ（他人に見せる必要なし）
log.txt              ... エラーログ
errors.txt
tmp/  *.rpyc         ... コンパイル済みバイナリ（自動生成される）
```
このリポジトリには `.gitignore` を入れてあるので、**git を使う方法（B）なら自動的に除外されます**。
ブラウザからドラッグ＆ドロップする場合（A）は、上記フォルダを**選択しないように**してください。

---

## 方法A: ブラウザだけでアップロード（初心者向け・一番かんたん）

1. ブラウザで https://github.com/369nightcore/Ren-py を開く
2. GitHub にログイン（右上の自分のアイコン）
3. 画面中央あたりの **「uploading an existing file」** という青い文字リンクをクリック
   - リンクが見つからない場合は、直接このURLを開く:
     https://github.com/369nightcore/Ren-py/upload/main
4. 「Drag files here to add them」の枠に、エクスプローラー（Finder）から
   **`game` フォルダごと**ドラッグして離す
   - フォルダをドラッグできないWindowsの場合は、`game` フォルダを開いて
     中身のファイル・フォルダを全部選択（Ctrl+A）してからドラッグ
   - `game/cache` `game/saves` は選択に含めないこと
5. 下にスクロールして **「Commit changes」** ボタンを押す
   - 説明文は `Add game files` など適当でOK
6. 完了。ページに `game/script.rpy` などが表示されていれば成功

> 注意: ブラウザからのアップロードは一度に100ファイルまで・合計25MBまでが目安です。
> 画像が多くて入らない場合は、方法B（git）か方法C（zip）を使ってください。

---

## 方法B: git コマンドでアップロード（画像が多い・何度も更新するならこっち）

### 1. Git をインストール
- Windows: https://git-scm.com/download/win からダウンロードして、
  インストール中は全部「Next」でOK
- インストール後、スタートメニューから **「Git Bash」** を開く（黒い画面が出る）

### 2. 一度だけ初期設定（自分の名前とメールを登録）
Git Bash に以下を1行ずつ入力して Enter（`""` の中を自分の名前に置き換える）
```bash
git config --global user.name "369nightcore"
git config --global user.email "あなたのメールアドレス"
git config --global core.quotepath false
```
※ `core.quotepath false` は日本語ファイル名が文字化けしないようにする設定です。

### 3. プロジェクトフォルダに移動する
Ren'Py のプロジェクトフォルダ（`game` が入っているフォルダ）のパスを確認し、
Git Bash で移動します。例: プロジェクトが `C:\renpy\Ren-py` の場合
```bash
cd /c/renpy/Ren-py
```
- Windowsのパスは `C:\renpy\Ren-py` → `/c/renpy/Ren-py` と書き換えます
- 迷ったら、Git Bash を開いた状態でフォルダを `cd ` と打った後にドラッグ＆ドロップすると自動でパスが入ります

### 4. リポジトリをダウンロードして、game フォルダを置く
```bash
git clone https://github.com/369nightcore/Ren-py.git
```
これで `Ren-py` フォルダができるので、そこに **あなたのプロジェクトの `game` フォルダをコピー**します。
コピーしたら `Ren-py` の中身はこうなります:
```
Ren-py/
├── .git/
├── .gitignore
├── README.md
└── game/
    ├── script.rpy
    ├── story_clubs.rpy
    └── images/ ...
```

### 5. 変更を GitHub に送る
`cd` で `Ren-py` フォルダの中に入って、以下を順番に実行:
```bash
cd Ren-py
git add .
git commit -m "Add game files"
git push origin main
```
- 初回の `git push` だけ、ブラウザが開いて GitHub のログインを求められることがあります。
  表示に従って許可してください（**パスワードをチャットや画面に貼らないこと**）

### 6. 確認
https://github.com/369nightcore/Ren-py を開いて `game/` フォルダが見えたら成功です。

---

## 方法C: 一気に zip で送る（画像が多すぎる場合）

1. プロジェクトフォルダの `game` を右クリック → 「圧縮」で `game.zip` を作る
   （`cache` `saves` フォルダは削除してから圧縮すると軽くなります）
2. https://app.gigafile.nu/ や Google Drive などのファイル共有サービスに上げる
3. URLをこのチャットに貼る → 私がダウンロードして中身を解析します

※このサンドボックスは `github.com` / `pypi.org` など一部のサイトしか見られないため、
Google Drive などからの直接ダウンロードは失敗することがあります。
**一番確実なのは方法A（GitHubに直接アップロード）** です。

---

## アップロード後に私がやること

1. `game/story_clubs.rpy` の75行目を実際に確認して、エラーを修正します
2. 全 `.rpy` ファイルを `tools/check_rpy.py` にかけて、同じ種類のミスを全部洗い出します
3. 直したファイルをコミットして、エラーなしで起動できる状態にします
