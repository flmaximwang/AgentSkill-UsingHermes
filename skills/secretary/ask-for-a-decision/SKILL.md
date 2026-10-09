---
name: ask-for-a-decision
description: Use when the user must choose, or do a step only they can.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [clarify, user-preferences, delivery, decisions]
    related_skills: [user-document-deliverables, respond-to-requirements]
---

# Ask for a decision

## When to Use

- Any `clarify` question; a `--force`, a deletion, or any other irreversible step awaiting a yes;
  「我该选哪个」; anything where the next step depends on a choice only the user can make.
- Not for a *set* of open items at once — a list of pending decisions is a document, governed by
  `user-document-deliverables`, with the chat message kept to the one reply each item needs.

Asking well is a delivery convention, not a formality: a badly shaped question costs a whole round.

## One decision per round

Put a **single** question in one form. A form carrying two independent decisions reads as a plan to be
approved at leisure and comes back unanswered, while the blocking question on its own gets answered —
so ask the blocking one, finish everything that does not depend on it, and raise the second only once
the first is settled.

- The second decision is its own turn, not a second row in the same form.
- Do not fold "and shall I also…" into the form. If something genuinely cannot wait, make it the one
  question and let the other wait instead.

## When the form comes back unanswered

A timeout is not a no, and it is not permission to decide: the question is still blocking. The choice is
between re-asking and proceeding on a flagged assumption — never silently dropping it.

- **Do the work that does not depend on the answer first**, then re-ask **once** as a single question. The
  retry usually lands, because the first form is what was wrong, not the user's willingness to answer.
- **Do not repeat the same form.** Make the retry strictly narrower: one question, its recommendation in
  the first option, and the evidence the choice rests on in the same message.
- **An answer arriving in prose counts.** When the user answers inside a later message — often attached to
  a new request — take it as the answer and act; do not re-open the form.
- **A blocking item can outlive the round it was asked in.** Keep it visible as one short `待你拍板` line
  in later reports, and stop mentioning it the moment it is answered or superseded.
- **While it is open, prefer reversible work over nothing and over guessing.** Anything cheap and
  undoable (a backup, an audit, a read-back, a file you can move again) narrows the eventual decision
  instead of stalling on it.

## 当卡住的不是选择，而是「只有他能做的一步」

扫码登录、过 CAPTCHA / 机器人验证、从浏览器里取 cookie、点一次授权 —— 这些不是决策，是**动作**，
而做的人只能是他。这类请求有自己的形状：

- **动作在前，理由在后**。消息第一屏就是按顺序编号、可以直接粘贴的命令；解释与备选方案压成一句话放最后。
  反例的代价很确定：把「要做的事」埋在一堆背景、选项和机制说明中间，用户会直接回一句「所以我要做什么？」
  —— 那一轮等于没交付，而信息其实一句不缺。
- **只列他必须做的**，并写清两头：你这边接着做什么、他做完回你什么（一句「回我一句好了」就够）。
- **不与待拍板的问题同条消息**：一个动作 + 一个决策 = 两件事，各自成轮（见上）。
- **凭据不要经聊天**。让他把取回来的值写进本地文件（`umask 077` 之后再写），命令里只出现 `$(cat <文件>)`；
  你不在聊天里索要、不复述密码或 token；一次性的扫码/验证码始终由他本人在自己的终端完成。
- **收下值之前先清空白**：从浏览器复制出来的 cookie / token 常带尾随空格或换行，直接当参数会**静默失败**
  ⇒ 取用时统一 `tr -d ' \t\r\n'`。
- **人机口失败时不要回头怪自己**：「只有他能过的验证」没过，先看是不是访问频率或环境导致，
  而不是在聊天里反复复述步骤让他再试一次。

## Shape of the question

- **Recommendation inside the first option's text**, with its cost — e.g.
  `装 —— 用 --force（推荐：官方覆盖开关；命中项已逐条核实为文档示例）`. The first option is the
  recommended one.
- **Give the command block alongside the question**, not after the answer arrives; this user often runs
  it themselves on another machine.
- **State the evidence the choice rests on before the question**, so the answer needs no round trip.
- Always offer a real "leave it alone" option; a menu of actions only is not a menu.
- Free-text beats a form when the answer would not change which option was picked.

## When to decide it yourself

- Cheap, reversible, intent not in doubt → just do it, and say what you did.
- Low-stakes ambiguity with an obvious default → take the default and name the assumption out loud. An
  explicitly-flagged assumption the user can veto beats a question that stalls the work.
- Ask only when the answer lives solely in the user's head, or when the outcome is hard to undo.

## Operations that need an explicit yes first

Removals with no undo, `--force` past a safety verdict, cross-profile or cross-account changes,
anything that spends money, publishes, or deletes something the user might still want.

Present the finding **and** your own read of it, and keep them apart: 有原文/实测依据 stays separate
from 我的推断或补充, including inside a findings list. Never let your interpretation ride along as
though the tool had said it.
