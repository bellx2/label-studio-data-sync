# Label Studio Data Sync

**English:** [README.md](README.md)

Label Studio プロジェクトからエクスポートするスクリプトです。

## データ構成

| パス | 説明 |
|---|---|
| `classes.txt` | クラス名一覧 |
| `images/*.jpg` | 画像ファイル |
| `labels/*.txt` | YOLO 形式ラベル（正規化 bbox） |
| `result.json` | COCO 形式の画像・注釈メタデータ |
| `notes.json` | カテゴリ情報 |

## Label Studio から更新

[uv](https://docs.astral.sh/uv/) で依存関係を入れ、API から最新のアノテーションを取得します。

```bash
cp .env.example .env
# .env に LABEL_STUDIO_API_KEY などを設定

make sync
```

`make sync` は `uv sync` のあと `sync_from_label_studio.py` を実行します。直接実行する場合:

```bash
uv sync
uv run python sync_from_label_studio.py
```

### 環境変数

| 変数 | 説明 | 例 |
|---|---|---|
| `LABEL_STUDIO_URL` | Label Studio の URL | `http://localhost:8080` |
| `LABEL_STUDIO_API_KEY` | アカウント設定の API トークン | （トークン文字列） |
| `LABEL_STUDIO_PROJECT_ID` | プロジェクト ID | `6` |
| `OUTPUT_DIR` | 出力先（省略時はリポジトリ直下） | `./my_data` |

### CLI オプション

```bash
uv run python sync_from_label_studio.py --url http://localhost:8080 --project-id 6 -v
uv run python sync_from_label_studio.py --help
```

更新時は `labels/` と `images/` 内の既存ファイルをいったん削除してから、Label Studio の `YOLO_WITH_IMAGES` エクスポートで上書きします。`result.json` と `classes.txt` も最新版に置き換わります。

画像のみスキップする場合（ラベルだけ更新、約 30MB 節約）:

```bash
uv run python sync_from_label_studio.py --skip-images
```
