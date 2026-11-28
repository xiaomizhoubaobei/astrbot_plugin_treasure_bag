#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# GPG 密钥全自动安装脚本（幂等 / 可自愈 / 无人工介入）
#
# 设计目标：一条命令跑完即完成「密钥导入 + 信任 + 签名接管」全链路，
#          任何环境（有/无 TTY、变量有/无、重复执行）都不需要人工干预。
#
# 用法：
#   bash install_gpg_keys.sh        # 运行一次即可，之后所有新终端自动生效
#   当前终端：source "$(git rev-parse --git-dir)/gpg-commit-env.sh"（或重开终端）
#
# 说明：
#   - 本脚本自包含（仅依赖系统 gnupg / curl / jq，缺失时自动安装），
#     不依赖仓库内其它脚本，任何环境可直接运行。
#   - CNB 平台默认已提供签名器 cnb-gpgsign；本脚本用于需要「触发者本人 GPG
#     密钥」亲自签名的场景（保证签名主体落在本人指纹上，而非平台章）。
#   - 脚本把 author / committer 统一到签名密钥邮箱，并持久化到 shell 启动
#     文件。云原生开发环境注入的 GIT_COMMITTER_EMAIL=cnb@cnb.local 会让
#     push 后的提交因「提交者邮箱未关联任何用户」(no_user) 验签失败；
#     GIT_COMMITTER_* 优先级高于 git config，且子进程改不了父 shell 环境，
#     因此必须由 shell 启动时自动 export 才能一次运行闭环。
#
# 环境变量：
#   GPG_API / PLUGIN_GPG_API   密钥分发 API 地址（缺失时回落到内置默认地址）
#   GPG_KEY / PLUGIN_GPG_KEY   私钥解锁短语 passphrase
#   CNB_BUILD_USER_NICKNAME / CNB_BUILD_USER_EMAIL   提交身份回落值
# ==============================================================================

# 内置默认分发 API（环境变量未注入时的兜底，避免因变量缺失而中断）
DEFAULT_API_URL="https://1329111128-j4hombe7rr.in.ap-guangzhou.tencentscf.com"

# 优先级：PLUGIN_ 前缀（CNB 注入规范）> 无前缀 > 内置默认值
API_URL="${PLUGIN_GPG_API:-${GPG_API:-$DEFAULT_API_URL}}"
GPG_KEY_VALUE="${PLUGIN_GPG_KEY:-${GPG_KEY:-}}"

# 校验：passphrase 必须显式注入，绝不猜测/拼接（私钥为加密存储）
if [ -z "$GPG_KEY_VALUE" ]; then
    echo "❌ 未设置私钥解锁短语环境变量（GPG_KEY / PLUGIN_GPG_KEY）"
    exit 1
fi

# 公网地址可达性重试参数（应对冷启动 / DNS 抖动）
CURL_RETRY_MAX=5
# 与上游 XMZZUZHI/oidc-auth 保持同步；该变量为预留参数，retry_run 暂未引用，
# 上游后续版本接入后即可去掉本行（否则 pre-commit 的 shellcheck 会报 SC2034）。
# shellcheck disable=SC2034
CURL_RETRY_SLEEP=2

log()  { echo "==> $*"; }
ok()   { echo "✅ $*"; }
warn() { echo "⚠️  $*"; }

# ------------------------------------------------------------------------------
# 从 `git verify-commit --raw` 的 VALIDSIG 状态行提取签名密钥完整指纹。
# [GNUPG:] 状态行是机器可读格式，不受 LC_MESSAGES 本地化影响：中文环境下
# `git log --show-signature` 会输出「使用 RSA 密钥 / 完好的签名」，硬编码匹配
# "using ... key" / "Good signature" 会把有效签名误判为失败。
# 输出空字符串表示未提取到（裸签/平台章）。
# ------------------------------------------------------------------------------
extract_gpg_fingerprint() {
    awk '/^\[GNUPG:\] VALIDSIG/ { print $3; exit }'
}

# 判断实际指纹是否命中期望指纹集合（空格分隔多把；忽略大小写与短/长差异）。
# 任一命中即判定接管（git 签名常落在子密钥上，故比对主+子完整集合）。
check_gpg_fingerprint() {
    local actual="$1" expected="$2" cand=""
    [ -n "$actual" ] || return 1
    for cand in $expected; do
        echo "$actual" | grep -qiE "$cand" && return 0
    done
    return 1
}

# 在隔离密钥环中导入私钥并提取其主+子指纹（空格分隔，首个为主指纹）。
# 隔离导入可避免误取密钥环中历史遗留密钥，确保指纹属于本次下载的这把。
extract_private_key_fingerprints() {
    local keyfile="$1" passphrase="$2" iso_home="" fps=""
    [ -s "$keyfile" ] || return 1
    iso_home=$(mktemp -d 2>/dev/null) || return 1
    chmod 700 "$iso_home" 2>/dev/null || true
    GNUPGHOME="$iso_home" gpg --batch --yes --pinentry-mode loopback \
        --passphrase "$passphrase" --import "$keyfile" >/dev/null 2>&1
    fps=$(GNUPGHOME="$iso_home" gpg --batch --list-secret-keys \
        --with-colons 2>/dev/null | awk -F: '$1=="fpr"{print substr($10,25)}' | paste -sd' ' -)
    rm -rf "$iso_home"
    [ -n "$fps" ] || return 1
    echo "$fps"
}

# ------------------------------------------------------------------------------
# 带指数退避的重试执行器（仅用于网络类操作）
# ------------------------------------------------------------------------------
retry_run() {
    local desc="$1"; shift
    local attempt=1 delay=1
    while true; do
        if "$@"; then
            return 0
        fi
        if [ "$attempt" -ge "$CURL_RETRY_MAX" ]; then
            echo "❌ ${desc} 重试 ${attempt} 次后仍失败"
            return 1
        fi
        warn "${desc} 第 ${attempt} 次失败，${delay}s 后重试..."
        sleep "$delay"
        attempt=$((attempt + 1))
        delay=$((delay * 2))
    done
}

# ------------------------------------------------------------------------------
# 1. 安装必要工具（幂等：逐个探测，缺哪个装哪个）
# ------------------------------------------------------------------------------
APT_PKGS=()
command -v gpg  >/dev/null 2>&1 || APT_PKGS+=("gnupg")
command -v curl >/dev/null 2>&1 || APT_PKGS+=("curl")
command -v jq   >/dev/null 2>&1 || APT_PKGS+=("jq")
if [ "${#APT_PKGS[@]}" -gt 0 ]; then
    log "安装缺失依赖：${APT_PKGS[*]}"
    SUDO=""
    [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && SUDO="sudo"
    $SUDO apt-get update -qq
    DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y --no-install-recommends "${APT_PKGS[@]}"
fi

# ------------------------------------------------------------------------------
# 2. 准备 GNUPGHOME 与无 TTY 环境配置（关键：容器内必须走 loopback）
# ------------------------------------------------------------------------------
export GNUPGHOME="${GNUPGHOME:-$HOME/.gnupg}"
mkdir -p "$GNUPGHOME"
chmod 700 "$GNUPGHOME"

# 写入 pinentry loopback 配置，保证无 TTY 环境也能自动解锁私钥
touch "$GNUPGHOME/gpg.conf" "$GNUPGHOME/gpg-agent.conf"
grep -qxF 'pinentry-mode loopback' "$GNUPGHOME/gpg.conf" || echo 'pinentry-mode loopback' >>"$GNUPGHOME/gpg.conf"
grep -qxF 'allow-loopback-pinentry' "$GNUPGHOME/gpg-agent.conf" || echo 'allow-loopback-pinentry' >>"$GNUPGHOME/gpg-agent.conf"
grep -qxF 'no-tty' "$GNUPGHOME/gpg.conf" || echo 'no-tty' >>"$GNUPGHOME/gpg.conf"

# 重启 gpg-agent 使配置生效（幂等）
gpgconf --kill gpg-agent >/dev/null 2>&1 || true
gpgconf --launch gpg-agent >/dev/null 2>&1 || true

# ------------------------------------------------------------------------------
# 3. 从分发 API 获取密钥地址（带重试）
# ------------------------------------------------------------------------------
log "获取密钥分发地址..."
API_RESPONSE="$(retry_run "拉取分发 API" curl -fsSL --connect-timeout 10 --max-time 30 "$API_URL")" || {
    echo "❌ 分发 API 不可达：$API_URL"
    exit 1
}
[ -n "$API_RESPONSE" ] || { echo "❌ API 响应为空"; exit 1; }

PRIVATE_KEY_URL="$(echo "$API_RESPONSE" | jq -r '.private_key_url // empty')"
PUBLIC_KEY_URL="$(echo "$API_RESPONSE"  | jq -r '.public_key_url // empty')"
PLATFORM="$(echo "$API_RESPONSE" | jq -r '.platform // empty' 2>/dev/null || true)"
if [ -z "$PRIVATE_KEY_URL" ] || [ "$PRIVATE_KEY_URL" = "null" ]; then
    echo "❌ 无法从 API 响应解析 private_key_url"
    exit 1
fi
log "平台标识：${PLATFORM:-未知}"

# ------------------------------------------------------------------------------
# 4. 下载公私钥到安全临时目录（自动清理，无论成功失败）
# ------------------------------------------------------------------------------
TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM

PRIVATE_KEY_FILE="$TMP_DIR/private_key.asc"
PUBLIC_KEY_FILE="$TMP_DIR/public_key.asc"

log "下载密钥..."
retry_run "下载私钥" curl -fsSL --connect-timeout 10 --max-time 60 -o "$PRIVATE_KEY_FILE" "$PRIVATE_KEY_URL"
[ -s "$PRIVATE_KEY_FILE" ] || { echo "❌ 私钥文件为空"; exit 1; }
grep -q 'BEGIN PGP PRIVATE KEY' "$PRIVATE_KEY_FILE" || { echo "❌ 私钥文件格式非法（非 PGP PRIVATE KEY）"; exit 1; }

if [ -n "$PUBLIC_KEY_URL" ] && [ "$PUBLIC_KEY_URL" != "null" ]; then
    retry_run "下载公钥" curl -fsSL --connect-timeout 10 --max-time 60 -o "$PUBLIC_KEY_FILE" "$PUBLIC_KEY_URL" || warn "公钥下载失败（不影响私钥导入）"
fi

# ------------------------------------------------------------------------------
# 5. 导入密钥（--passphrase 解锁加密私钥；幂等：重复导入不会报错）
# ------------------------------------------------------------------------------
log "导入密钥..."
gpg --batch --yes --no-tty --pinentry-mode loopback --passphrase "$GPG_KEY_VALUE" \
    --import "$PRIVATE_KEY_FILE"
if [ -s "$PUBLIC_KEY_FILE" ]; then
    gpg --batch --yes --no-tty --import "$PUBLIC_KEY_FILE" || true
fi

# ------------------------------------------------------------------------------
# 6. 提取本次导入私钥的精确指纹集合（主密钥 + 各子密钥），供选键与验签比对
# ------------------------------------------------------------------------------
FINGERPRINTS="$(extract_private_key_fingerprints "$PRIVATE_KEY_FILE" "$GPG_KEY_VALUE" || true)"
KEY_ID="$(echo "$FINGERPRINTS" | awk '{print $1}')"
if [ -z "$KEY_ID" ]; then
    # 退化：直接从主密钥环取主密钥指纹
    KEY_ID="$(gpg --list-secret-keys --with-colons 2>/dev/null | awk -F: '/^sec:/{print $5; exit}')"
fi
if [ -z "$KEY_ID" ]; then
    echo "❌ 导入后未在密钥环中找到私钥（sec）"
    exit 1
fi
log "私钥指纹：${KEY_ID}（完整集合：${FINGERPRINTS:-$KEY_ID}）"

# CNB 远端验签按主密钥匹配；GnuPG 默认优先使用签名子密钥，会因 unknown_key 失败。
# 主密钥具备签名能力时在 key spec 末尾加 "!"，强制用主密钥签名。
PRIMARY_CAPS="$(gpg --batch --with-colons --list-keys "$KEY_ID" 2>/dev/null \
    | awk -F: '$1=="pub"{print $12; exit}')"
if [[ "$PRIMARY_CAPS" == *S* ]]; then
    SIGNING_KEY_ID="${KEY_ID}!"
else
    SIGNING_KEY_ID="$KEY_ID"
fi
log "Git 签名密钥：${SIGNING_KEY_ID}"

# ------------------------------------------------------------------------------
# 7. 设置终极信任（关键修复：全程无 TTY，用 --with-colons 判定结果）
#    旧实现依赖 `echo -e "trust\n5\ny\nquit" | --command-fd 0`，
#    在无 TTY 环境下会挂起并把退出码置为 2 —— 这里改为完全不依赖交互。
# ------------------------------------------------------------------------------
log "设置密钥 ${KEY_ID} 为终极信任..."
printf 'trust\n5\ny\nsave\n' | gpg --batch --no-tty --command-fd 0 --status-fd 1 \
    --pinentry-mode loopback --passphrase "$GPG_KEY_VALUE" \
    --edit-key "$KEY_ID" >/dev/null 2>&1 || true
# 兜底：直接以 ownertrust 导入（对 CNB 打章判定足够）
echo "${KEY_ID}:6:" | gpg --import-ownertrust >/dev/null 2>&1 || true
gpg --check-trustdb >/dev/null 2>&1 || true

# ------------------------------------------------------------------------------
# 8. 生成 GPG 包装脚本（无 TTY 环境签名的关键：统一带 passphrase + loopback）
# ------------------------------------------------------------------------------
WRAPPER="/tmp/gpg-wrapper.sh"
cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
# 自动生成：无 TTY 下统一走 loopback 并用 passphrase 解锁签名
exec gpg --batch --no-tty --pinentry-mode loopback --passphrase "$GPG_KEY_VALUE" "\$@"
EOF
chmod 700 "$WRAPPER"

# ------------------------------------------------------------------------------
# 9. 配置 Git 签名：仓库级优先（覆盖已有 local 旧签名器），无仓库时回落全局
#    关键：仓库级配置优先级高于全局——若运行目录已存在 local 的
#    user.signingkey / commit.gpgsign / gpg.program，只写 --global 不会生效，
#    提交仍会走旧签名器；因此必须按「有工作树 -> 写 local + 全局；否则 -> 只写全局」。
#    gpg.format 一并显式写入，避免沿用仓库级遗留的 ssh/x509 签名格式。
# ------------------------------------------------------------------------------
configure_git_signing() {
    local scope="$1"
    git config "$scope" user.signingkey "$SIGNING_KEY_ID"
    git config "$scope" commit.gpgsign true
    git config "$scope" tag.gpgsign true
    git config "$scope" gpg.program "$WRAPPER"
    git config "$scope" gpg.format openpgp
}
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "==> 检测到 Git 工作树，写入仓库级签名配置（优先级高于全局）"
    configure_git_signing --local
    configure_git_signing --global
else
    echo "==> 非 Git 仓库目录，仅写入全局签名配置"
    configure_git_signing --global
fi
# ------------------------------------------------------------------------------
# 9.5 统一 author / committer 到签名密钥邮箱（平台验签的关键）
#     CNB 按 committer 邮箱关联用户并比对签名密钥绑定邮箱：
#       https://docs.cnb.cool/zh/guide/commit-signature-verification.md
#     云原生开发环境会注入 GIT_COMMITTER_NAME/EMAIL=cnb / cnb@cnb.local，
#     该邮箱没有关联用户，提交 push 后显示 NO_PASSED / REASON_NO_USER。
#     GIT_COMMITTER_* 优先级高于 git config，且脚本内 export 只影响自身进程，
#     因此落盘可 source 的提交环境文件（9.5），并持久化到 shell 启动文件（9.6）。
# ------------------------------------------------------------------------------
SIGNER_UID="$(gpg --batch --with-colons --list-keys "$KEY_ID" 2>/dev/null \
    | awk -F: '$1=="uid"{print $10; exit}' || true)"
SIGNER_EMAIL="$(printf '%s' "$SIGNER_UID" \
    | grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+' | head -1 || true)"
[ -n "$SIGNER_EMAIL" ] || SIGNER_EMAIL="${CNB_BUILD_USER_EMAIL:-}"
if [ -z "$SIGNER_EMAIL" ]; then
    echo "❌ 无法确定与签名密钥一致的提交邮箱，请设置 CNB_BUILD_USER_EMAIL"
    exit 1
fi
SIGNER_NAME="${CNB_BUILD_USER_NICKNAME:-$(git config --get user.name || true)}"
[ -n "$SIGNER_NAME" ] || SIGNER_NAME="${SIGNER_EMAIL%%@*}"
log "提交身份统一为：${SIGNER_NAME} <${SIGNER_EMAIL}>（密钥 ${KEY_ID}）"

configure_git_identity() {
    local scope="$1"
    git config "$scope" user.name "$SIGNER_NAME"
    git config "$scope" user.email "$SIGNER_EMAIL"
}
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    configure_git_identity --local
fi
configure_git_identity --global

# 生成可 source 的提交环境片段（不含任何凭证），覆盖平台注入的 committer 身份
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    COMMIT_ENV_FILE="$(git rev-parse --git-dir)/gpg-commit-env.sh"
else
    COMMIT_ENV_FILE="/tmp/gpg-commit-env.sh"
fi
{
    printf '# 由 install_gpg_keys.sh 生成；提交前执行：source %s\n' "$COMMIT_ENV_FILE"
    printf 'export GIT_AUTHOR_NAME=%q\n' "$SIGNER_NAME"
    printf 'export GIT_AUTHOR_EMAIL=%q\n' "$SIGNER_EMAIL"
    printf 'export GIT_COMMITTER_NAME=%q\n' "$SIGNER_NAME"
    printf 'export GIT_COMMITTER_EMAIL=%q\n' "$SIGNER_EMAIL"
} > "$COMMIT_ENV_FILE"
chmod 600 "$COMMIT_ENV_FILE"
# shellcheck disable=SC1090
source "$COMMIT_ENV_FILE"    # 让脚本自身及子进程（含闭环自检）立即使用新身份
ok "提交环境已写入：${COMMIT_ENV_FILE}"

# ------------------------------------------------------------------------------
# 9.6 持久化到 shell 启动文件：一次运行，之后所有新终端自动生效
#     平台在每个新 shell 重新注入 GIT_COMMITTER_*，git config 覆盖不了，
#     子进程也改不了父 shell 环境；唯一闭环方式是让 shell 启动时自动 export。
#     身份块置于 ~/.bashrc 最前面（早于可能存在的非交互 guard），重复执行幂等。
# ------------------------------------------------------------------------------
BASHRC_FILE="${HOME}/.bashrc"
touch "$BASHRC_FILE"
IDENTITY_BEGIN='# >>> gpg-commit-identity >>>'
IDENTITY_END='# <<< gpg-commit-identity <<<'
IDENTITY_BLOCK="$TMP_DIR/identity-block"
BASHRC_STRIPPED="$TMP_DIR/bashrc-stripped"
{
    printf '%s 由 install_gpg_keys.sh 管理，请勿手改\n' "$IDENTITY_BEGIN"
    printf 'export GIT_AUTHOR_NAME=%q\n' "$SIGNER_NAME"
    printf 'export GIT_AUTHOR_EMAIL=%q\n' "$SIGNER_EMAIL"
    printf 'export GIT_COMMITTER_NAME=%q\n' "$SIGNER_NAME"
    printf 'export GIT_COMMITTER_EMAIL=%q\n' "$SIGNER_EMAIL"
    printf '%s\n' "$IDENTITY_END"
} > "$IDENTITY_BLOCK"
# 先剔除旧块，再把新块置于文件开头；用重定向而非 mv，保留原文件权限与 inode
awk -v begin="$IDENTITY_BEGIN" -v end="$IDENTITY_END" '
    index($0, begin) == 1 { in_block = 1; next }
    in_block && index($0, end) == 1 { in_block = 0; next }
    !in_block { print }
' "$BASHRC_FILE" > "$BASHRC_STRIPPED"
cat "$IDENTITY_BLOCK" "$BASHRC_STRIPPED" > "$BASHRC_FILE"
ok "提交身份已持久化到：${BASHRC_FILE}"

# 用「平台已注入错误值」的新交互式 shell 验证 bashrc 确实能覆盖
PROBE_EMAIL="$(env GIT_COMMITTER_NAME=cnb GIT_COMMITTER_EMAIL=cnb@cnb.local \
    bash -ic 'git var GIT_COMMITTER_IDENT' 2>/dev/null \
    | grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+' | head -1 || true)"
if [ "$PROBE_EMAIL" != "$SIGNER_EMAIL" ]; then
    echo "❌ 持久化校验失败：新 shell 的 committer 邮箱为 ${PROBE_EMAIL:-未知}"
    exit 1
fi
ok "新终端提交身份校验通过：${SIGNER_NAME} <${SIGNER_EMAIL}>"
warn "当前终端需 source ${COMMIT_ENV_FILE} 或重开终端；新终端已自动生效"
warn "并确认 ${SIGNER_EMAIL} 已在 CNB 账号验证、公钥已添加，否则仍会验签失败"

# ------------------------------------------------------------------------------
# 10. 持久化 GPG_TTY（无 TTY 时写入 /dev/tty 亦可，签名实际走 wrapper）
# ------------------------------------------------------------------------------
CURRENT_TTY="$(tty 2>/dev/null || true)"
case "$CURRENT_TTY" in
    ""|"not a tty") CURRENT_TTY="/dev/tty" ;;
esac
grep -qxF "export GPG_TTY=\"$CURRENT_TTY\"" ~/.bashrc 2>/dev/null \
    || echo "export GPG_TTY=\"$CURRENT_TTY\"" >>~/.bashrc
export GPG_TTY="$CURRENT_TTY"

# ------------------------------------------------------------------------------
# 11. 闭环自检：真实 git commit -S + 验签，失败即报错（不假装成功）
#     比对主+子完整指纹集合，避免主/子指纹不同导致误报；
#     并校验 author / committer 邮箱与签名密钥邮箱一致（平台按此关联用户）。
#     验签一律走 git verify-commit --raw 的 [GNUPG:] 状态行，与语言无关。
# ------------------------------------------------------------------------------
log "执行签名闭环自检..."
VERIFY_DIR="$TMP_DIR/verify"
mkdir -p "$VERIFY_DIR"
SELFCHECK_LOG="$TMP_DIR/selfcheck.log"
selfcheck_ok=0
if (
    cd "$VERIFY_DIR" || exit 1
    git init -q . || exit 1
    git config user.name  "$SIGNER_NAME"
    git config user.email "$SIGNER_EMAIL"
    echo "hello GPG" > selfcheck.txt
    git add selfcheck.txt
    git commit -q -S -m "chore(gpg): 签名环境自检" || exit 1
    # 平台按 committer 邮箱关联用户；不一致会判 no_user / bad_email
    for ident in "$(git log -1 --format='%ae')" "$(git log -1 --format='%ce')"; do
        [ "$ident" = "$SIGNER_EMAIL" ] || {
            echo "自检提交身份不一致：${ident} != ${SIGNER_EMAIL}" >&2
            exit 1
        }
    done
    git verify-commit --raw HEAD >"$SELFCHECK_LOG" 2>&1 || exit 1
    grep -qF '[GNUPG:] GOODSIG' "$SELFCHECK_LOG" || exit 1
    grep -qF '[GNUPG:] VALIDSIG' "$SELFCHECK_LOG" || exit 1
    sig_fp="$(extract_gpg_fingerprint <"$SELFCHECK_LOG" || true)"
    check_gpg_fingerprint "$sig_fp" "${FINGERPRINTS:-$KEY_ID}" || exit 1
    exit 0
); then
    selfcheck_ok=1
fi

if [ "$selfcheck_ok" -ne 1 ]; then
    echo "❌ 签名闭环自检失败：验签未通过，或 author / committer 邮箱与签名密钥邮箱不一致"
    [ -f "$SELFCHECK_LOG" ] && { echo "----- 自检日志 -----"; cat "$SELFCHECK_LOG"; }
    exit 1
fi

ok "签名闭环自检通过：GOODSIG / VALIDSIG（密钥 ${KEY_ID}）"
ok "GPG 已全自动就绪：指纹=${KEY_ID}，wrapper=${WRAPPER}"
