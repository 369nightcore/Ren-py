#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_rpy.py -- Ren'Py スクリプト(.rpy)のよくある書き間違いを検出するツール

Ren'Py 本体が無くても動く、純粋な Python の静的チェッカーです。
「unterminated string literal」のようなパースエラーを、起動前にまとめて洗い出します。

使い方:
    python tools/check_rpy.py            # カレントフォルダの game/ を検査
    python tools/check_rpy.py game       # 検査するフォルダを指定
    python tools/check_rpy.py a.rpy b.rpy

エラーが見つかると終了コード 1 を返します。
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 検出する「全角・特殊な引用符」
# Ren'Py の文字列は半角の " または ' で始めなければなりません。
# これらが混ざると unterminated string literal になります。
# ---------------------------------------------------------------------------
BAD_QUOTES = {
    "\u201c": '全角の始め二重引用符 “  (半角の " を使う)',
    "\u201d": '全角の終わり二重引用符 ”  (半角の " を使う)',
    "\u2018": '全角の始め引用符 ‘  (半角の \' を使う)',
    "\u2019": '全角の終わり引用符 ’  (半角の \' を使う)',
    "\uff02": '全角のダブルクォート ＂  (半角の " を使う)',
    "\uff07": '全角のシングルクォート ＇  (半角の \' を使う)',
    "\u301d": '波ダッシュ系の引用符 〝  (半角の " を使う)',
    "\u301e": '波ダッシュ系の引用符 〞  (半角の " を使う)',
}

# 行の先頭がこれだと「セリフ行の引用符を書き忘れている」可能性が高い
SPEECH_PREFIXES = ("me", "e", "n", "y", "s", "a", "b", "c", "d", "f", "g",
                   "h", "i", "j", "k", "l", "m", "o", "p", "q", "r", "t",
                   "u", "v", "w", "x", "z")


class Issue:
    """検出した問題 1 件"""

    def __init__(self, path: Path, lineno: int, text: str, hint: str = ""):
        self.path = path
        self.lineno = lineno
        self.text = text
        self.hint = hint

    def __str__(self) -> str:
        line = f"  {self.path}:{self.lineno}: {self.text}"
        if self.hint:
            line += f"\n      → {self.hint}"
        return line


def scan_file(path: Path) -> list[Issue]:
    """1 つの .rpy ファイルを検査して、問題のリストを返す"""
    issues: list[Issue] = []
    try:
        raw = path.read_bytes()
    except OSError as e:  # pragma: no cover
        return [Issue(path, 0, f"ファイルが読めません: {e}")]

    # BOM / 文字コードの判定
    encoding = "utf-8"
    if raw.startswith(b"\xff\xfe"):
        encoding = "utf-16"
        issues.append(Issue(path, 1, "UTF-16 で保存されています",
                            "Ren'Py は UTF-8 を推奨します。エディタで「UTF-8(BOMなし)」に変換して保存してください。"))
    elif raw.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
    else:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            encoding = "cp932"
            issues.append(Issue(path, 1, "UTF-8 として読めません (Shift-JIS/CP932 の可能性があります)",
                                "エディタで「UTF-8(BOMなし)」に変換して保存してください。文字化けやパースエラーの原因になります。"))

    text = raw.decode(encoding, errors="replace")
    lines = text.split("\n")

    in_triple = False  # 三連引用符 """ ... """ の中かどうか

    for idx, line in enumerate(lines, start=1):
        stripped = line.rstrip("\r")

        # ---- タブ文字でのインデント ----
        leading = stripped[: len(stripped) - len(stripped.lstrip())]
        if "\t" in leading:
            issues.append(Issue(path, idx, "インデントにタブ文字(TAB)が使われています",
                                "Ren'Py はスペースのみ推奨です。タブをスペース4つに置換してください。"))

        # ---- 三連引用符ブロックの追跡 ----
        if in_triple:
            if '"""' in stripped or "'''" in stripped:
                in_triple = False
            continue

        # ---- コメント行はスキップ(# から後ろは見ない) ----
        code = strip_comment(stripped)

        # 三連引用符が始まる(同じ行で閉じない)場合は以降スキップ
        if code.count('"""') % 2 == 1 or code.count("'''") % 2 == 1:
            in_triple = True
            issues.append(Issue(path, idx, '三連引用符 """ が閉じられていません',
                                '同じ行で """ ... """ を閉じるか、行末の """ を確認してください。'))
            continue

        # ---- 全角引用符 ----
        for ch, why in BAD_QUOTES.items():
            if ch in stripped:
                col = stripped.index(ch) + 1
                issues.append(Issue(path, idx,
                                    f"{col}文字目に {why}",
                                    f"該当行: {stripped.strip()[:80]}"))

        # ---- 引用符の対応が取れているか ----
        state = analyze_quotes(code)
        if state.unterminated:
            issues.append(Issue(path, idx,
                                f"unterminated string literal ({state.quote} で始まる文字列が閉じていません)",
                                build_hint(stripped, state.quote)))
        if state.bad_escape:
            issues.append(Issue(path, idx,
                                "文字列の中にバックスラッシュ(\\)だけが宙に浮いています",
                                "行末の \\ は次の行との連結になります。\\\\ と書くか削除してください。"))

        # ---- label start が無い(起動できない典型例) ----
        # これは最後にまとめてチェックするのでここでは何もしない

    # ---- label start の有無 ----
    if not any("label start" in ln for ln in lines):
        issues.append(Issue(path, 0, "このファイルに `label start` がありません",
                            "プロジェクト全体(game/ 内のどこか)に label start が無いと起動できません。"))

    return issues


class QuoteState:
    def __init__(self) -> None:
        self.unterminated = False
        self.quote = ""
        self.bad_escape = False


def strip_comment(line: str) -> str:
    """文字列の外側にある # コメントを取り除く"""
    out = []
    quote = ""
    escaped = False
    for ch in line:
        if escaped:
            out.append(ch)
            escaped = False
            continue
        if ch == "\\" and quote:
            out.append(ch)
            escaped = True
            continue
        if quote:
            out.append(ch)
            if ch == quote:
                quote = ""
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out)


def analyze_quotes(code: str) -> QuoteState:
    """半角引用符の対応を調べる。閉じていなければ unterminated とする。"""
    state = QuoteState()
    quote = ""
    escaped = False
    for i, ch in enumerate(code):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            if quote and i == len(code) - 1:
                state.bad_escape = True
            escaped = True
            continue
        if quote:
            if ch == quote:
                quote = ""
            continue
        if ch in ("'", '"'):
            quote = ch
    if quote:
        state.unterminated = True
        state.quote = quote
    return state


def build_hint(line: str, quote: str) -> str:
    """エラー行を見て、ありがちな原因を推測する"""
    s = line.strip()
    hints = []

    # me "..." のようなセリフ行で末尾の引用符が無い
    if s and s[-1] != quote and not s.endswith("\\"):
        head = s.split(" ", 1)[0].rstrip('":')
        if head in SPEECH_PREFIXES:
            hints.append(f'セリフ行のようです。行末に閉じ引用符 {quote} を付けてください。')
            hints.append(f'例:  {head} "セリフ本文"{quote}')

    # 本文の中に半角引用符が混ざっている
    body = s[s.find(quote) + 1:] if quote in s else s
    if body.count(quote) >= 1 and s.count(quote) % 2 == 1:
        hints.append("セリフ本文中に半角引用符が混ざっていませんか? "
                     "本文の引用符は全角の「」にすると安全です。")

    if any(ch in s for ch in BAD_QUOTES):
        hints.append("全角引用符(“ ” ‘ ’ ＂)が混ざっています。半角に統一してください。")

    if not hints:
        hints.append(f'開いた {quote} に対応する閉じ {quote} がこの行にありません。'
                     "行を跨ぐ文字列は三連引用符(\"\"\")を使ってください。")
    return " / ".join(hints)


def collect_files(args: list[str]) -> list[Path]:
    files: list[Path] = []
    targets = args or ["game"]
    for t in targets:
        p = Path(t)
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(x for x in p.rglob("*.rpy")
                                if "cache" not in x.parts and "saves" not in x.parts))
        else:
            print(f"[警告] 見つかりません: {t}")
    # 重複除去
    seen: set[Path] = set()
    uniq = []
    for f in files:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def main(argv: list[str]) -> int:
    files = collect_files(argv[1:])
    if not files:
        print("検査対象の .rpy ファイルが見つかりませんでした。")
        print('使い方:  python tools/check_rpy.py game')
        return 0

    print(f"検査するファイル: {len(files)} 件")
    print("-" * 70)

    total = 0
    for f in files:
        issues = scan_file(f)
        if not issues:
            print(f"[OK]   {f}")
            continue
        print(f"[NG]   {f}")
        for it in issues:
            print(it)
        total += len(issues)

    print("-" * 70)
    if total:
        print(f"合計 {total} 件の問題が見つかりました。")
        print("上の行番号のファイルを直してから、もう一度 Ren'Py で起動してください。")
        return 1
    print("問題は見つかりませんでした。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
