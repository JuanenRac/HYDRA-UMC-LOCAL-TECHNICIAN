<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-LOCAL-TECHNICIAN バナー" width="100%">
</p>

# 🤖 HYDRA-UMC-LOCAL-TECHNICIAN

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | 🇯🇵 <b>日本語</b></p>

### 🛡️ ポリシーで権限を制御されたローカルAI技術者

<p align="center">
  <img src="https://img.shields.io/badge/ライセンス-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/言語-Python%203.11%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/コア-標準ライブラリのみ-brightgreen.svg" alt="標準ライブラリのみのコア">
  <img src="https://img.shields.io/badge/フェーズ-1%2C%203%20%26%204%2F6%20完了-367BF5.svg" alt="全6フェーズ中フェーズ1・3・4完了">
</p>

> **状態: v0.1.1、機能実装済み - 全6フェーズ中フェーズ1・3・4完了
> （検索可能な知識、ツールオーケストレーター、エスカレーション）、フェーズ5開始
> （実際のローカルCLI）。** フェーズ0では、実際のリスクレベル・
> ポリシー（`policy/risk_levels.py`）、固定のツール許可リスト
> （`policy/tool_matrix.py`）、将来のあらゆるツール呼び出しが検証される
> べき5つの実在する最小契約（`contracts/*.schema.json` + `contracts.py`）、
> HYDRA-UMC-OPS-AGENT 自身のすでにテスト済みの `log_redaction.py` から移植
> された実際の機密情報マスキング、そしてこのフェーズ0自身の文字通りの終了
> 基準 - 悪意ある取得ドキュメントが決してツール呼び出しを引き起こしたり
> 機密情報を漏らしたりできないことを証明する実際の敵対的テスト - を定義し
> ました。フェーズ3では、宣言済みのOBSERVEレベルツールのうち9個を
> 実際のハンドラー（`orchestrator/dispatch.py`）に接続します:
> `service.status`、`storage.usage`、`network.port_status`、
> `network.connectivity`、`system.temperature`、`manifest.read`、`logs.read`、`process.list`、`update.pending` -
> それぞれが許可リストに載った短いシンボル名
> （`orchestrator/allowlist.py`）だけを解決し、取得した
> ドキュメントが提供しうる生のパス・ホスト・ポート・URLを直接使うことは
> 決してありません。フェーズ1は10番目のツール `knowledge.search`
> （`knowledge/index.py`）を追加します - 承認済みのドキュメント、マニフェスト、
> 契約の許可リストに載ったルート上で動く、実際のローカルTF-IDFインデックス
> で、HYDRA-UMC-DOCS-QA 自身のすでにテスト済みの検索エンジンから移植された
> ものです。フェーズ4は実際の `EvidenceBundle` 組み立てと
> `MaintenanceProposal` の構築を追加します（`escalation/`）- すでに
> 観測済みのツール出力に基づいており、捏造された診断では決してありませ
> ん: 推論エンジンがまだ存在しないため、`propose_maintenance()` は人間
> のオペレーターが提供した内容を検証・裏付けするだけで、それを生成す
> ることは決してありません。フェーズ5自身の最初の実際のスライス -
> `tools list`/`tools call` と `escalation evidence`/`escalation
> propose` - は、上記の各要素に実際のコマンドラインを与えます。新しい
> 権限を追加することは決してなく、各テストがすでに実行している、ポリ
> シーですでに検証済みの同じコードを呼び出すだけです。推論エンジン、HYDRA-UMC-SERVER との統合は
> まだ存在しません - 今日実際に存在するコマンド範囲については
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) を参照してください。

---

**正直な現状確認 - 今日実際に動くもの:** リスクレベルポリシー(`policy/risk_levels.py`)、固定のツール許可リスト(`policy/tool_matrix.py`)、5 つの契約バリデーター(`contracts.py` + `contracts/*.schema.json`)、インジェクション防御境界(`knowledge/trust.py`、`knowledge/redaction.py`)、ローカルTF-IDF知識インデックス(`knowledge/index.py`、フェーズ1)、宣言済みの10個のOBSERVEツールすべてに実際のハンドラーがある(`orchestrator/dispatch.py` + `orchestrator/allowlist.py`: `service.status`、`storage.usage`、`network.port_status`、`network.connectivity`、`system.temperature`、`manifest.read`、`logs.read`、`process.list`、`update.pending`、`knowledge.search`)、実際の `EvidenceBundle`/`MaintenanceProposal` 構築(`escalation/evidence.py`、`escalation/proposal.py`、フェーズ4)、そしてそれらすべての上に実際のCLI(`tools list`/`tools call`/`escalation evidence`/`escalation propose`、フェーズ5自身の最初のスライス)はテスト済みである(`tests/unit/` と `tests/adversarial/` 全体で 164 件のテストと 30 件のサブテストが成功) - フェーズ1・フェーズ3・フェーズ4は完了し、フェーズ5は開始した。`update.pending` は実際にGitHubを確認するためにオプションの依存関係 `hydra-umc-updater`(`update-check` extra)を必要とし、それがない場合は正直に(`available: false`)劣化する。このリポジトリのどこにも推論エンジン、HYDRA-UMC-SERVER との統合はまだ存在せず、このコードのどこも `MaintenanceProposal` に対してまだ行動を起こせない——下記ロードマップのフェーズ 2、そしてフェーズ5の残り(HYDRA-UMC-SERVERと統合されたAPI、および音声)は依然として完全に願望であり、裏付けとなるコードは一切ない。これまでに何が実際に出荷されたかは `CHANGELOG.md` を参照。

---

## 1. 🛠️ 技術概要

HYDRA-UMC-LOCAL-TECHNICIAN は HYDRA-UMC エコシステム自身のための専用ロー
カルAIです。エコシステム自身のサービスやノードを観察し、説明し、診断し、
保守を提案します - 新しい基盤モデルを訓練することは決してなく、テキストを
生成することによって行動することも決してありません。ターゲットプラット
フォームは CM5 で、インストール後は Hailo-10H アクセラレータを使用します
が、フェーズ0はそのどちらも必要としません。本リリースのすべては純粋な
データを検証する純粋な Python です。

**譲れない原則:** AI は応答を生成することによって権限を得ることは決して
ありません。ポリシー、権限、人間による確認がすべての実際の行動を決定しま
す - モデル自身の言葉では決してありません。

本リリースは、独立して有用な8つの実在する要素をもたらします:

1. **リスクレベル・ポリシー**（`policy/risk_levels.py`）- `INFORM` から
   `PHYSICAL_ACTION` までの6つの順序付けられたレベルで、それぞれに実際の
   テスト済みポリシー（ツールを読み取れるか、変更できるか、確認が必要か、
   実装されているか）があります。上位2レベルは契約の完全性のためだけに
   宣言されており、このコード内のどこにも実装されていません。
2. **ツール・マトリクス**（`policy/tool_matrix.py`）- 10個の実在する
   `OBSERVE` レベルのツール名からなる固定の許可リスト。この辞書に存在し
   ないツール名は絶対に呼び出せません、それだけです - 10個すべてが
   すでに実際のハンドラーに接続されています(下記の項目5と6を参照)。
3. **実際の契約**（`contracts/*.schema.json` + `contracts.py`）-
   `ToolRequest`、`ToolResult`、`MaintenanceProposal`、`EvidenceBundle`、
   `PatchVerificationReport` は、それぞれに規範的なJSON Schema
   ファイルと、そこからフィールド単位でそのままコピーされた、標準
   ライブラリのみの Python バリデータがあります。
4. **インジェクション防御境界**（`knowledge/trust.py` +
   `knowledge/redaction.py`）- 信頼できないコンテンツ（README、ログ行、
   コミットメッセージ）は常に `UntrustedText` としてラップされ、これは
   ツール呼び出しを生成できるメソッドを一切持たない型です。この
   コードベースで `ToolRequest` を構築する唯一の実際の方法は、すでに型付
   けされ、すでに分離されたフィールドを受け取り、オブジェクトが存在する
   前に、未登録または未実装のツール名を拒否します。
5. **ツール・オーケストレーター**（`orchestrator/dispatch.py` +
   `orchestrator/allowlist.py`、フェーズ3）- `dispatch_tool_request()`
   はすでに検証済みの `ToolRequest` を実際に実行し、実際の `ToolResult`
   を返します: `service.status`（実際の `systemctl is-active`）、
   `storage.usage`（`shutil.disk_usage`）、`network.port_status`（実際の
   ソケットプローブ）、`network.connectivity`（エンドポイント自身の実際の
   ステータスコードを報告する実際のHTTP GET - `network.port_status` とは
   本質的に異なるチェックであり、HYDRA-UMC-OPS-AGENT 自身の `inventory.py`
   が単純なTCP接続と実際のヘルスGETの間で引いているのと同じ実際の区別で
   す)、`system.temperature`（実際のLinuxサーマルゾーンsysfsパス)、
   `manifest.read`（実際の `hydra-umc.project.json` の読み取り)、
   `logs.read`（許可リストに載ったログファイルの範囲限定でマスキング
   済みの末尾)、`process.list`（`/proc/<pid>/cmdline` に対する実際の
   許可リストに載った部分文字列一致)、そして `update.pending`（
   HYDRA-UMC-UPDATER 自身の実際のGitHub検出とバージョン比較を再利用する、
   オプションの依存関係)。これらのいずれも生のパス・ホスト・ポート・
   URL・ユニット名・パターンを直接受け付けません - 固定の
   `OrchestratorConfig` を通じて解決される短いシンボル名だけであり、
   毒された文書自身のテキストが任意の実在ターゲットを名指しすること
   は決してなく、すでに許可リストに載った名前だけです。
6. **検索可能な知識インデックス**（`knowledge/index.py`、フェーズ1）
   - 実際のローカルTF-IDF検索エンジン(tokenize/build_index/search)で、
   HYDRA-UMC-DOCS-QA 自身のすでにテスト済みの `index.py` から変更なし
   で移植されており、Markdownソース(見出しで区切られた断片)とJSON
   ソース(マニフェストや契約スキーマはオブジェクトの途中で有用に分割
   されることは決してないため、断片ごとにファイル全体)向けの新しい
   範囲限定の取り込みが加わっています。10番目のツール
   `knowledge.search` として、`orchestrator/allowlist.py` の新しい
   `resolve_knowledge_source()` を通じて接続されています: 呼び出し側は
   すでに許可リストに載ったシンボリックなソース名だけを指定でき、生の
   パスは決して指定できず、返される実際の一致はハンドラーを出る前に
   常に `UntrustedText` としてラップされたままです。走査自体も
   (ファイル数、ファイルごとのサイズで)範囲限定されており、正当に
   許可リストに載ったルートであっても - 決して盲目的にならず、決して
   ディスク全体にはなりません。
7. **エスカレーション: 証拠と提案**（`escalation/`、フェーズ4）-
   `evidence.assemble_evidence_bundle()` は、すでに実行され、すでに検証
   済みの実際の `ToolResult` のバッチを実際の `EvidenceBundle` に変換し
   ます - HYDRA-UMC-OPS-AGENT 自身の `incident.py` と同じパターンで、
   すでに観測されたデータからの純粋な導出であり、AI呼び出しでは決して
   ありません。`proposal.propose_maintenance()` は `MaintenanceProposal`
   の実際のコンストラクタ・バリデータです - 意図的に生成器ではありませ
   ん。推論エンジンがまだ存在せず、このプロジェクト自身の譲れない原則
   が診断の捏造を禁じているためです。今日は人間のオペレーターだけが
   `diagnosis`/`steps`/`rollback` を提供します。このモジュールが追加す
   る唯一の実際の防御策は、`citedEvidence` の各エントリが実際に観測さ
   れたツール結果自身の `evidence` フィールドと文字通り一致しなければ
   ならないというもので、そうでなければ提案はそのまま拒否されます。
   `confirmationRequired` は呼び出し側が設定できるものでは決してなく、
   常に `policy/risk_levels.py` 自身のポリシーが提案の宣言されたリスク
   について既に定めている通りの値になります。このコードのどこも
   `MaintenanceProposal` に対してまだ行動を起こせません。
8. **CLI表面**（`cli.py`、フェーズ5自身の最初の実際のスライス）-
   `tools list`/`tools call` と `escalation evidence`/`escalation
   propose` は、上記の各要素に初めて実際のコマンドラインを与えます
   (これまではそれぞれテストからしか到達できませんでした)。独自の権限
   は一切追加しません: `tools call` は各テストがすでに呼び出している
   のと同じ `build_tool_request_from_model_output()` で `ToolRequest`
   を構築し、同じ `dispatch_tool_request()` で実行します - OBSERVEを
   超えるものはこのコードのどこにも実装されていないため、依然として
   OBSERVEレベルのツールにしか到達できません。`--config` はJSONファイル
   から実際の `OrchestratorConfig` を読み込みます(省略時は
   `default_config()` にフォールバック); コマンドライン自体で生のパス・
   ホスト・ポートを指定する方法は依然としてありません。

```
$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
VALID: tests/fixtures/tool_request.valid.json (ToolRequest)

$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.invalid.json --contract ToolRequest
INVALID: tests/fixtures/tool_request.invalid.json (ToolRequest): ...
```

本リリースにはデフォルト/引数なしの呼び出しも GUI もありません -
完全で実際のコマンド範囲については
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) を参照してください。

## 2. 🧱 アーキテクチャと設計上の決定

- **AI は応答を生成することによって権限を得ることは決してありません。**
  本リリースのすべての設計上の決定は、この唯一の原則を守るために存在し
  ます - 完全なモデルについては
  [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) を参照してください。
- **ツールは呼び出される前に登録されていなければなりません。**
  `policy/tool_matrix.py` の `TOOL_MATRIX` が完全かつ固定のリストであり、
  `lookup_tool()` が `None` を返すことは無条件の拒否であって、デフォルトの
  リスクレベルを推測するケースでは決してありません。
- **信頼できないコンテンツが命令になることは決してありません。** 防御は
  「指示のような」テキストを認識しようとするフィルタ - 決意した
  プロンプトインジェクションに対して最初から負けている勝負 - ではなく、
  アーキテクチャ上のもの(ツールを生成するメソッドを一切持たない型)です。
  フェーズ0自身の文字通りの終了基準である
  `tests/adversarial/test_injection_defense.py` を参照してください。
- **契約の規範的な情報源はその JSON Schema ファイルです。**
  `contracts.py` のフィールドリストとバリデータは、HYDRA-UMC-SDK 自身の
  `validation.py` と同じ規約に従い、`contracts/*.schema.json` からフィー
  ルド単位でコピーされています - 独立した2つ目の真実の情報源ではありませ
  ん。
- **機密情報マスキングはすでにテスト済みのコードを再利用します。**
  `knowledge/redaction.py` は HYDRA-UMC-OPS-AGENT 自身のすでにテスト済み
  の `log_redaction.py` のバイト単位の移植です(ヘッダーコメントのみが
  異なります) - 根底にある問題(あいまいなヒューリスティックなしに、実際
  のよく知られた機密情報の形を認識すること)はここでも同一です。
- **`PRIVILEGED_CHANGE` と `PHYSICAL_ACTION` は未実装のままです。**
  専用の設計、別個の認可経路、そして物理的行動については実際のインター
  ロックが存在するまでの、意図的かつ恒久的な関門です - 後で完成させる
  見落としではありません。
- **知識の検索は範囲限定・許可リスト化されており、決して盲目的ではあり
  ません。** `knowledge.search` はすでに許可リストに載った1つのルート
  だけをインデックス化し(`orchestrator/allowlist.py` の
  `resolve_knowledge_source()`)、走査自体も実際のファイル数とファイル
  ごとのサイズの上限で範囲限定されています - 「ディスク全体を盲目的に
  学習させることは決してありません」は、運用者がすでに安全と判断した
  ルートであっても成り立ちます。
- **本リリースは宣言・検索・検証のみを行い、まだ行動はしません。** 推論
  エンジン、OBSERVEを超える実際のツール実行、HYDRA-UMC-SERVER との統合
  は、このリポジトリのどこにもまだ存在しません。

## 📂 ディレクトリ構造

```
HYDRA-UMC-LOCAL-TECHNICIAN/
├── src/hydra_umc_local_technician/
│   ├── policy/
│   │   ├── risk_levels.py    # RiskLevel + RiskLevelPolicy: 6つのレベル、レベルごとの実際のポリシー
│   │   └── tool_matrix.py    # TOOL_MATRIX: 固定かつ実在するツール許可リスト（10個の OBSERVE 名）
│   ├── knowledge/
│   │   ├── redaction.py      # 実際の機密情報マスキング、HYDRA-UMC-OPS-AGENT から移植
│   │   ├── trust.py          # UntrustedText + build_tool_request_from_model_output(): インジェクション防御境界
│   │   └── index.py          # フェーズ1 - 実際のTF-IDF検索 + 範囲限定のMarkdown/JSON取り込み、HYDRA-UMC-DOCS-QA から移植
│   ├── orchestrator/          # フェーズ3 + フェーズ1 - 10個すべての実際のOBSERVEツールハンドラー、完了
│   │   ├── allowlist.py      # OrchestratorConfig: ハンドラーが解決するシンボル名の許可リスト、生のパス・ホスト・ポートは決して使わない
│   │   └── dispatch.py       # dispatch_tool_request(): 検証済みの ToolRequest を実際に実行し、実際の ToolResult を返す
│   ├── escalation/            # フェーズ4 - 実際の EvidenceBundle 組み立て + MaintenanceProposal 構築、完了
│   │   ├── evidence.py       # assemble_evidence_bundle(): 実際の ToolResult -> 契約に適合する実際の EvidenceBundle
│   │   └── proposal.py       # propose_maintenance(): MaintenanceProposal の実際のコンストラクタ・バリデータ、生成器では決してない
│   ├── contracts.py           # 5つの最小契約のための実際の標準ライブラリのみのバリデータ
│   └── cli.py                 # フェーズ5 - contracts validate、tools list/call、escalation evidence/propose、--version
├── contracts/                  # 5つの契約のための規範的な JSON Schema ファイル（draft 2020-12）
├── tests/
│   ├── unit/                   # 上記各モジュールの実際のテスト
│   ├── adversarial/            # test_injection_defense.py - フェーズ0自身の文字通りの終了基準
│   └── fixtures/                # 各契約の有効/無効な JSON フィクスチャ
├── docs/
│   ├── ARCHITECTURE.md         # 目的、5つの目標要素、目標アーキテクチャ、エコシステムとの関係
│   ├── SECURITY_MODEL.md       # 6つのリスクレベル、データ/機密情報のルール、インジェクション防御
│   ├── CLI_REFERENCE.md        # contracts validate、フラグ、終了コード
│   └── CONTRACTS.md            # 5つの契約すべての実際のフィールド単位の形
├── images/                      # メディアとアプリアイコン
├── build.sh / build.bat        # venv + 編集可能インストール + コンパイルチェック + テスト
├── build-test.sh / .bat        # 非変更のビルド検証のみ
├── run.sh / run.bat            # 実際のCLIコマンドを転送
├── bump_version.py             # エコシステム全体の「走行距離計」式バージョン増分（pyproject.toml + __init__.py）
└── bump_manifest_version.py    # hydra-umc.project.json のバージョンをネイティブのものと同期（--sync）
```

## ⚙️ ビルドと実行ガイド

```bash
chmod +x build.sh   # 一度だけ
./build.sh          # .venv を作成、pip install -e ".[dev]"、コンパイルチェック + テスト
./run.sh contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
./run.sh --version
```

Windows の場合: `build.bat`、続いて `run.bat contracts validate ...` /
`run.bat --version`。`build-test.sh`/`.bat` は本プロジェクト自身のCI
ワークフローが実行するのと同じ非変更の Python 構文コンパイルチェックを
行い、プロジェクトバージョンや CHANGELOG には一切触れません - これは
テストスイート自体を実行**しません**。完全なローカルテストスイートには
`./build.sh`/`build.bat`（または直接 `pytest tests/`）を実行してください。

**トラブルシューティング**

- `contracts validate` が終了コード `1` と `INVALID: ...` で終了する場合:
  メッセージを読んでください - 何かが失敗したことだけでなく、正確な
  フィールドと理由が示されます。5つの契約それぞれの実際の期待される形に
  ついては [docs/CONTRACTS.md](docs/CONTRACTS.md) を確認してください。
- `tests/adversarial/` 内のテストが失敗する場合: これはフェーズ0自身の
  文字通りの終了基準です - そこでの失敗は常にインジェクション防御境界の
  実際の後退として扱ってください。決して緩めるべきテストとして扱っては
  いけません。

## 🚀 ロードマップ

このバージョンはフェーズ0、フェーズ1、フェーズ3、フェーズ4を提供します。残りは、フェーズ順に:

- **フェーズ1 - 検索可能な知識(完了)。** 承認済みのドキュメント、
  マニフェスト、契約、runbook のローカルでバージョン管理されたインデッ
  クス - ディスク全体を盲目的に学習させることは決してありません。
  `knowledge/index.py` は HYDRA-UMC-DOCS-QA 自身のすでにテスト済みの
  TF-IDF検索を変更なしで移植し、Markdown・JSONソース向けの範囲限定・
  許可リスト化された取り込みを追加しており、10番目のOBSERVEレベルツール
  `knowledge.search` として接続されています。
- **フェーズ2 - ローカル推論エンジン。** Hailo-10H と互換性のある小型
  LLM（候補: Qwen2.5-1.5B-Instruct、Qwen2.5-Coder-1.5B、
  Qwen3-1.7B-Instruct）で、実際の Hailo 互換性、レイテンシ、言語品質、
  消費電力、ライセンスが検証されてから初めて選定されます。
- **フェーズ3 - ツール・オーケストレータ（完了: 宣言済み9個中9個）。**
  `TOOL_MATRIX` にすべての実際の `OBSERVE` レベルのツールハンドラを接続する
  決定論的コードで、すべての呼び出しでポリシーが強制されます。
  `service.status`、`storage.usage`、`network.port_status`、
  `network.connectivity`、`system.temperature`、`manifest.read`、`logs.read`、`process.list`、`update.pending` はすでに
  実装済みです(`orchestrator/dispatch.py`)。
- **フェーズ4 - 提案と証拠(完了)。** `MaintenanceProposal` と
  `EvidenceBundle` の実際の構築(`escalation/`)で、HYDRA-UMC-DEV-SERVER
  の将来の Developer Node 役割へとエスカレーションします。
  `evidence.assemble_evidence_bundle()` はすでに観測済みの `ToolResult`
  から実際のパッケージを導出し、`proposal.propose_maintenance()` は
  人間が提供した提案を実際の証拠に基づいて検証・裏付けします - 推論エ
  ンジンがまだ存在しないため、それを生成することは決してありません。
  このコードのどこも `MaintenanceProposal` に対してまだ行動を起こせま
  せん。
- **フェーズ5 - ユーザーインターフェース(開始: CLIスライス)。**
  HYDRA-UMC-SERVER/Studio に統合されたローカルAPI、続いてCLI、その後音声
  - フェーズ0がすでに確立したポリシーと確認の境界を決して迂回しません。
  CLIスライスは今すぐ実際のものです: `tools list`/`tools call` と
  `escalation evidence`/`escalation propose`(`cli.py`)は、上記の各実際
  の要素に、すでにテスト済みでポリシー適用済みの同じコードを通じて到達
  します。意図的にこの1つのリポジトリ内にあるものだけに範囲を限定して
  います。HYDRA-UMC-SERVERと統合されたAPIおよび音声は、将来のリリース
  のための別個の、リポジトリをまたいだ作業のままです。

フェーズ2、そしてフェーズ5の残りはこのリポジトリにまだ存在しません - 残る各フェーズが
明示的に含むもの・除外するものについては
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を、各フェーズが引き続き
尊重しなければならないセキュリティ不変条件については
[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) を参照してください。

## 🔗 関連プロジェクト

このプロジェクトは同じ作者（JuanenRac / Electro Hobby 3D）による
HYDRA-UMC ロボティクス・エコシステムの一部です。リクエストが実はこの
リポジトリではなく以下のいずれかに関するものである可能性があるため、
知っておく価値があります。

**直接関連**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — 本プロジェクト自身の親: この技術者の将来の推論エンジンが動作する Hailo-10 認知パイプラインの統合ハブ。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 保守インシデントのライフサイクル(証拠、診断、人間が承認した変更、カナリアデプロイ、検証)を所有する; この技術者自身の `knowledge/redaction.py` はそのすでにテスト済みの `log_redaction.py` の直接的な移植であり、将来のフェーズは実際の証拠パッケージをそこへエスカレーションします。その独自の承認フローを迂回することは決してありません。
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — 後のフェーズが調査、テスト、レビュー済みパッチの準備のために実際の `EvidenceBundle` を送信する将来の Developer Node - 直接的で自動的なパッチ適用経路では決してありません。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — 本プロジェクト自身のローカルな `contracts/*.schema.json` が、そこにも存在するようになった時点で整合を取ることを意図している、共有されバージョン管理された契約を定義します。
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — この技術者自身のエンドポイント、セッション、ロール、監査証跡をホストする将来の認証済みエントリポイント。

**エコシステムのその他の部分**

*コアハードウェアとプラットフォーム*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — ロボットアームの物理マザーボード: CM5 ホスト + デュアルコア STM32H745、CAN-OTA/SPI-OTA 経由で最大8本のツールアームをオーケストレーション。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — CM5 向けの再現可能な Raspberry Pi OS プロダクト層: 読み取り専用エージェント、検証済み設定/プロファイル、WiFi ファーストコンタクト・プロビジョニング。

*コアバックエンドとクライアント*
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — リアルタイムのマルチロボット3D可視化を備えたウェブ制御ダッシュボード。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 複数サーバーを同時に扱えるデスクトップ（PySide6）群制御コマンドセンター。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 生体認証ログインとペアリングされた Wear OS コンパニオンを備えたネイティブ Android 制御アプリ。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — リアルタイム WebSocket 同期を備えた iOS/iPadOS 制御アプリ（Flutter）。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — CM5 自体に組み込まれた、オンボード7インチ DSI タッチスクリーン向けのネイティブタッチUI。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 完成したモデルを STUDIO 自身のカタログにプッシュするデスクトップ用グラフィカル URDF 作成/編集ツール。
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — HYDRA-UMC-EDITOR-URDF も編集する同じモデルカタログ内で、実在するパーツを変換/置換/削除/追加するデスクトップ STL モデルエディタ。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 実際の VDA 5050 MQTT パブリッシャーを介した AGV/AMR フリートの協調境界。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 実際の GRBL ステータス/制御バイトへのアクセスを備えた高レベル CNC セル・コーディネータ。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 実際の Boston Dynamics Spot コマンド送信機能を備えた、脚式/ヒューマノイド・ドロイド向けの協調境界。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 鍵/筐体/インターロックの3つの実際の GPIO 安全機構を読み取るレーザーセル安全コーディネータ。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — OpenPnP ピック&プレース向けの安全な高レベル基板フロー・コーディネータ。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 実際に制御されたジョブコマンドを備えた、Moonraker/Klipper 3Dプリンタ向けの安全な協調境界。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 実際の遅延インポートされた rclpy ROS 2 トランスポートを備えた安全コーディネータ。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 実際の MAVLink コマンド送信機能を備えた、カメラ搭載 UAV 向けの協調境界。

*URTC ツールプラットフォーム*
- **[URTC](https://github.com/JuanenRac/URTC)** — 物理的な Universal Robot Tool Controller 基板向けファームウェア、CAN バス経由で25種類以上のツールプロファイル。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — URTC 基板をフラッシュするデスクトップ GUI ツール、CAN-OTA に加えてフルチップ SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — URTC 基板向けデスクトップ・ライブ CAN バス診断ツール、ツールプロファイルごとに1パネル。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — Web Serial API 経由の、ローカルインストール不要な URTC-TESTER のブラウザ版代替。

*視覚AIノード（Hailo-8）*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — 実際の段階別ハードウェア準備状況チェックを備えた Hailo-8 視覚パイプラインの統合ハブ。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — Hailo アーキテクチャ/チェックサムによる安全な読み込み検証を備えた、実際のコンパイル済みモデルレジストリ。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 実際の HailoRT 統合境界を備えた、実際の GStreamer パイプライン + MediaMTX 設定ジェネレータ。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 上流のゾーン状態に応じて安全ゲート制御される、実際の位置ベース・ビジュアルサーボイング補正則。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — キャリブレーションの鮮度を強制する、実際のゾーン侵入チェックと E-STOP 要求。

*認知AIノード（Hailo-10）*
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — Vision-Language-Action モデル向けの、実際のアクショントークンのエンコード/デコードと軌道生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 制限され確認を要する Watch リレーを備えた、実際の音声フロントエンド（VAD + 意図パーサー）。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — MCU エラーコードに対する、実際のルールベースのタスク分解と意味論的エラー復旧。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — このエコシステム自身の Markdown ドキュメントに対する、標準ライブラリのみの実際の TF-IDF 文書検索。

*オーケストレーションとスワーム*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 実際の gRPC/Protobuf ヘルスレポート契約とミッション状態マシンを備えた統合ハブ。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 実際の HTTP API 上での、重複排除機能を備えた実際の優先度ベースのジョブキュー。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — 独自のリトライ/バックオフとアイデンティティ不一致検出を備えた、実際の gRPC ベースのフリート・ヘルス・ウォッチドッグ。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 実際の障害物/作業空間の衝突検証を備えた、実際の RRT ベースの3D経路プランナー。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — マルチセル収束のためにプロパティテストされた、実際の CRDT LWW-Element-Map 状態同期。

*デジタルツインとシミュレーション*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 実際のバージョン互換性同期契約を備えた、デジタルツインエンジンの統合ハブ。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — シミュレーションと実際のハードウェアの間でコマンドをルーティングする、実際のハードウェア・イン・ザ・ループ安全インターロック。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — 実際の URDF サブセットに対する、実際の順運動学と関節限界検証。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — YOLO/COCO アノテーションエクスポートを備えた、実際の手続き型2Dシーンジェネレータ。

*データと分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — 実際の取り込み/クエリ HTTP API を備えた、実際の sqlite3 バックの時系列ストア。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — ドリフト監視を備えた、実際の FFT + 統計的ベースライン異常検出器。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — 再現可能な CSV エクスポートを備えた、DATALAKE の履歴に対する実際の OEE/可用性計算。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — シーケンス重複排除を備えた、DATALAKE への実際の CAN/WebSocket 取り込みパイプライン。

*産業用ゲートウェイ*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 実際のコマンド許可リスト/バックプレッシャー層を備えた、産業プロトコルへ中継する統合ハブ。
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — 実際のバイナリプロトコル・クライアントセッションで検証された、実際の OPC-UA アドレス空間。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — オプションのクライアント別認証とトピック ACL を備えた、実際の MQTT ブローカー。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — 劣化モード出力を備えた、実際の MTConnect `/probe` および `/current` XML エンドポイント。

*補完ツール*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — 誠実な統計的フォールバックを備えた、DATALAKE/ANOMALY-DETECTOR 上のスマートサマリーと異常ハイライトのパネル。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 実際で安定した終了コード契約を備えた、HYDRA-UMC-SERVER 自身の API の実際のライブクライアントであるフリート CLI。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 実際の触覚アラートとペアリングされたスマートフォンへの音声リレーを備えた WearOS コンパニオンアプリ。
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — 設計上 GET のみの外部アダプタ機能カタログ。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — ソースから新しい CM5 イメージを構築する、"Ecosystem Operations" のもう一つの兄弟プロジェクト。
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — このエコシステム内のすべてのリポジトリを検出・クローン・更新する、管理用デスクトップツール。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 実際のツールID復号と Smart Idle 予熱ロジックを備えた、基板取り付けラック向けファームウェア。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — サーマル/RGB 検査ツールヘッド向けの実際の Python ビジョンコンパニオンを加えたファームウェア。

---

## 📚 ドキュメントとコミュニティ

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — 目的、5つの目標要素、目標アーキテクチャ、エコシステムとの関係。
- **[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md)** — 6つのリスクレベル、データ/機密情報のルール、そして実際にテストされたインジェクション防御境界。
- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — 各サブコマンド、そのフラグ、終了コード契約。
- **[docs/CONTRACTS.md](docs/CONTRACTS.md)** — 5つの契約すべての実際のフィールド単位の形。
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — プルリクエストのための技術スタックとコーディングガイドライン。
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — このコミュニティで期待される行動基準。
- **[SECURITY.md](SECURITY.md)** — 脆弱性の報告方法、および本プロジェクトの実際のセキュリティ重点領域。
- **[SUPPORT.md](SUPPORT.md)** — 質問やバグ報告を行う場所。

## 👤 作者
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 ライセンス

GPL-3.0（ソフトウェア）/ CC BY-SA 4.0（ドキュメント） - 詳細は [LICENSE.md](LICENSE.md) を参照してください。
