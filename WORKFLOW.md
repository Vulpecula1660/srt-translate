# SRT 字幕翻譯工作流程

使用 Claude Code 將日文 SRT 字幕檔批次翻譯為繁體中文。

## 前置需求

- Python 3
- Claude Code CLI
- `srt_helper.py`（已在本目錄中）

## 快速開始

```bash
# 1. 拆分
python3 srt_helper.py split "原始字幕.srt" batches/

# 2. 在 Claude Code 中貼上翻譯指令（見步驟 2）

# 3. 驗證
python3 srt_helper.py validate batches/

# 4. 複查翻譯品質（在 Claude Code 中貼上複查指令，見步驟 4）

# 5. 依據複查報告自動修正翻譯（在 Claude Code 中貼上修正指令，見步驟 5）

# 6. 合併
python3 srt_helper.py merge batches/ "原始字幕_繁中.srt"

# 7. 移除字幕行尾的逗號和句號
sed -i 's/[，。]*$//' "原始字幕_繁中.srt"

# 8. 合併複查報告並清理中間檔案
cat batches/review_*.md > "原始字幕_review.md"
python3 srt_helper.py clean batches/
rm batches/review_*.md && rmdir batches/
```

## 詳細步驟

### 步驟 1：將 SRT 拆分為 JSON 批次

```bash
python3 srt_helper.py split "原始字幕.srt" batches/
```

- 預設每批 350 條字幕，可用 `-n` 調整：
  ```bash
  python3 srt_helper.py split "原始字幕.srt" batches/ -n 350
  ```
- 預設會自動去除字幕結尾的「。」，如不需要可加 `--no-strip-period`
- 產生 `batches/batch_000.json`, `batch_001.json`, ... 等檔案
- 較大的批次（700 條）能提供更多上下文，有助於翻譯品質（代名詞指代、語氣延續等）

### 步驟 2：使用 Claude Code 平行翻譯

在 Claude Code 中，對每個 batch 檔案啟動平行 Task agent 進行翻譯。

每個 agent 的指令範本：

```
Read the file batches/batch_NNN.json. It contains Japanese subtitle entries in JSON format.
Also read member.md — it contains a list of all members from =LOVE, ≠ME, and ≒JOY with their kanji names, readings, and nicknames.

Translate ALL the "text" fields from Japanese to Traditional Chinese (繁體中文).

Context: This is a live stream transcript of Takiwaki Shoko (瀧脇笙古/たきわき しょうこ), a member of the Japanese idol group =LOVE. The tone is casual and conversational.

Rules:
- Keep num and timestamp fields EXACTLY unchanged
- Preserve line breaks within text fields (multi-line subtitles)
- Do NOT translate sound effects or music symbols (e.g. ♪～)
- If the text is already valid in Chinese or is a universal term (e.g. "...", "TikTok"), keep it as-is

Member names:
- When a member is mentioned by nickname (e.g. みりにゃ、きゃーたん), reading (e.g. おおたに えみり), or partial name, translate using their kanji name from member.md (e.g. 大谷映美里、齋藤樹愛羅)
- ASR may produce incorrect kanji for member names — use context and readings to match the correct member from member.md
- Group names (=LOVE/イコラブ, ≠ME/ノイミー, ≒JOY/ニアジョイ) should be kept as =LOVE, ≠ME, ≒JOY

Speech cleanup (important — the source is ASR output from a live stream):
- Remove stutters and false starts: 「きょ、今日は」→ just translate as 「今天」
- Deduplicate repeated words/fillers: 「あの、あの、あのね」→「那個啊」, not 「那個、那個、那個啊」
- Consecutive meaningless fillers like 「えーと、えーと」「うーん」 don't all need to be translated — keep one or omit entirely
- If ASR produced duplicate/near-duplicate subtitle entries, translate the content just once cleanly
- The goal is clean, readable subtitles — the viewer shouldn't feel the speaker is stuttering unless it's intentional for comedic/emotional effect

Translation style:
- Prioritize natural Chinese expression (意譯) over word-for-word translation (直譯). Ask yourself: if a native Chinese speaker said the same thing in this situation, how would they say it?
- Write natural spoken Traditional Chinese, not written/formal Chinese
- Keep translations concise — subtitles must be readable at a glance
- If the original is short and casual, the translation should be too. Don't expand 「うん」 into 「是的我明白了」, just use 「嗯」
- Japanese often omits the subject — infer from context, but don't add unnecessary subjects if Chinese also sounds natural without them
- Preserve the speaker's tone: casual speech stays casual, polite speech stays polite
- For honorifics (さん、ちゃん、先生、様), use the appropriate Chinese equivalent or omit if unnatural
- Japanese filler/hedging words (なんか、ちょっと、やっぱり、一応、的な) should be translated by feel, not mechanically. 「なんか」 is not always 「總覺得」— often it's just 「就」「嗯」 or can be omitted entirely
- Sentence-ending particles (ね、よ、な、さ、わ) convey tone, not literal meaning. Don't force a translation — adjust the overall sentence tone instead. Bad: 「美味しいよね」→「很好吃唷對吧」 / Good: 「美味しいよね」→「很好吃耶」
- Japanese and Chinese have very different grammar structures — always restructure into natural Chinese word order, never mirror Japanese sentence structure:
  - SOV → SVO: Japanese puts verbs at the end; Chinese doesn't. Bad: 「昨日買ったやつ」→「昨天買了的那個東西」 / Good:「昨日買ったやつ」→「昨天買的那個」
  - Long modifiers: Japanese stacks long clauses before a noun. If the modifier is long, restructure in Chinese. Bad: 「昨日みんなで一緒に食べたケーキ」→「昨天大家一起吃了的蛋糕」 / Good:「昨天大家一起吃的那個蛋糕」
  - Verb/negation at end: Japanese reveals the key point (verb, negation) at the sentence end. In Chinese, bring it forward. Bad: 「それはちょっと難しいかなと思って」→「那個有點困難呢我這樣想著」 / Good:「我覺得那有點難」
  - Clause order: Japanese often puts reason/condition clauses before the main clause. Reorder if Chinese sounds more natural the other way. Bad: 「時間がないから行けない」→「因為沒有時間所以不能去」 / Good:「沒時間，去不了」
- Use natural Chinese equivalents for casual expressions:
  - ～じゃん → 不是...嗎 / ...啊
  - ～っていうか → 怎麼說 / 應該說
  - めっちゃ / すごい → 超 / 好～ (not 非常)
  - ～かもしれない (casual) → 搞不好 / 可能 (not 也許...也說不定)
  - 楽しみ → 好期待 (not 很期待能享受)
  - やばい → 天啊 / 誇張 / 慘了 (context-dependent, not always 糟糕)
- Avoid translationese (翻譯腔): don't add unnecessary 「的話」「的部分」「來說」; don't translate 「～と思う」 as 「我覺得...我這麼想」— often just state the opinion directly; don't translate 「～することができる」 as 「能夠做到...這件事」— just 「可以～」

Write the result to batches/translated_NNN.json in the same JSON format.
```

可以一次啟動所有 agent（例如 9 個 batch 就啟動 9 個平行 agent）。

### 步驟 3：驗證翻譯結果

```bash
python3 srt_helper.py validate batches/
```

自動檢查：
- 所有 batch 是否都已翻譯
- 每個 batch 的條目數量是否與原始一致
- `num` 和 `timestamp` 是否被意外修改
- 標記未翻譯的文字（可能是合理的，如名字、省略號）

### 步驟 4：複查翻譯品質

驗證通過後，使用 Claude Code agent 對每個批次進行品質複查，找出可能有問題的段落供人工確認。

每個 agent 的指令範本：

```
Read the files batches/batch_NNN.json and batches/translated_NNN.json.
Also read member.md — it contains all member names, readings, and nicknames for =LOVE, ≠ME, and ≒JOY.

Compare each original Japanese subtitle entry with its Traditional Chinese translation. Identify entries with potential issues:

1. **意義不明** (Unclear meaning): The translated text doesn't make sense in context
2. **人名錯誤** (Name error): Member names should use kanji names from member.md — flag if a nickname/reading was left untranslated or translated to the wrong kanji
3. **翻譯錯誤** (Translation error): The translation doesn't accurately convey the original meaning
4. **聽譯錯誤** (Transcription error): The original Japanese appears to contain speech recognition errors (wrong kanji/words for what was likely said), causing the translation to also be wrong

Context: Live stream transcript of Takiwaki Shoko (瀧脇笙古/たきわき しょうこ), member of Japanese idol group =LOVE (イコールラブ).

Related groups: ≠ME (ノイミー), ≒JOY (ニアジョイ)

Review guidelines:
- Focus on genuinely problematic entries — don't flag acceptable translations
- Consider surrounding entries for context (conversations span multiple subtitles)
- Short filler entries like 「嗯」「對」「欸」 are usually fine — don't over-flag
- Sound effects and music symbols (♪～) should be kept as-is

Write results to batches/review_NNN.md in this format:

# 翻譯複查：batch_NNN

| 編號 | 時間戳 | 原文 | 譯文 | 問題類型 | 說明與建議 | 建議譯文 |
|------|--------|------|------|----------|------------|----------|

- The 建議譯文 column must contain the corrected translation text, ready to be used as a replacement
- For 聽譯錯誤 where the original Japanese is wrong, still provide the best possible translation based on what was likely said

If no issues are found, write: "本批次未發現明顯問題。"
Do NOT modify any source or translation files — this is review only.
```

與翻譯步驟一樣，可以平行啟動所有 agent。完成後檢查各 `batches/review_*.md` 檔案進行人工複查與修正。

### 步驟 5：依據複查報告自動修正翻譯

複查完成後，使用 Claude Code agent 對每個有問題的批次自動修正翻譯。

每個 agent 的指令範本：

```
Read the file batches/review_NNN.md.

If the review says "本批次未發現明顯問題。", do nothing and report that no fixes were needed.

Otherwise, also read batches/translated_NNN.json. For each entry flagged in the review table, replace the "text" field with the value from the 建議譯文 column.

Rules:
- ONLY modify entries listed in the review table
- Keep num and timestamp fields EXACTLY unchanged
- Do not modify any entries that are not in the review table

Write the updated file back to batches/translated_NNN.json (overwrite in place).

After writing, report a summary of all changes made in this format:
- 編號 XX: 「舊譯文」→「新譯文」(問題類型)
```

可以平行啟動所有 agent。完成後 Claude 會回報每個批次的修正摘要。

### 步驟 6：合併翻譯結果

```bash
python3 srt_helper.py merge batches/ "原始字幕_繁中.srt"
```

將所有 `translated_*.json` 按順序合併為最終的 SRT 檔案。
如果有缺少的翻譯檔案，會顯示警告但仍會合併已有的部分。

### 步驟 7：移除字幕行尾標點

合併後的 SRT 可能有行尾殘留的逗號或句號，用 `sed` 清除：

```bash
sed -i 's/[，。]*$//' "原始字幕_繁中.srt"
```

### 步驟 8：合併複查報告並清理中間檔案

將各批次的複查報告合併為一份獨立檔案，然後清除所有中間檔案：

```bash
# 合併複查報告（檔名與輸出 SRT 對應）
cat batches/review_*.md > "原始字幕_review.md"

# 清理 JSON 中間檔案
python3 srt_helper.py clean batches/

# 清理複查報告
rm batches/review_*.md
```

最終產出兩個檔案：
- `*_繁中.srt`：翻譯後的字幕檔
- `*_review.md`：複查報告，供手動修正時參考

## 注意事項

- **批次大小**：預設 300 條。上下文越多翻譯品質越好，但不建議超過 350 條以避免接近 token 上限。
- **Token 限制**：如遇到 `CLAUDE_CODE_MAX_OUTPUT_TOKENS` 錯誤，在 `~/.zshrc` 加入：
  ```bash
  export CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000
  ```
  需重啟 Claude Code 生效。
- **JSON 中介格式**：使用 JSON 而非直接操作 SRT，確保時間戳和編號不被改動。

## CLI 參考

```
python3 srt_helper.py --help
python3 srt_helper.py split --help
python3 srt_helper.py merge --help
python3 srt_helper.py validate --help
python3 srt_helper.py clean --help
```

| 指令 | 用途 |
|------|------|
| `split` | 將 SRT 拆分為 JSON 批次 |
| `merge` | 合併翻譯後的 JSON 為 SRT |
| `validate` | 驗證翻譯完整性與正確性 |
| `clean` | 清理中間檔案 |

## 檔案說明

| 檔案 | 用途 |
|------|------|
| `srt_helper.py` | SRT 拆分/合併/驗證/清理工具 |
| `batches/batch_NNN.json` | 原始日文批次 |
| `batches/translated_NNN.json` | 翻譯後的批次 |
| `batches/review_NNN.md` | 翻譯品質複查報告（中間檔案） |
| `*_繁中.srt` | 最終翻譯輸出 |
| `*_review.md` | 合併後的複查報告（最終產出） |
