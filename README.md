# 家长进课堂：课件制作与验收 Skills

把做课件时一轮轮确认过的要求留下来，给下一次制作使用。

这是我在用 AI 制作「家长进课堂」课件的过程中，逐步整理出来的一套流程，打包为一个 Codex 插件，包含制作、验收与交付两个配合使用的 Skills。

**这不是一个完美的方案，还有很多改进的空间。我会结合实际使用中的问题，持续修改和调整。**

作者：gitshilly · 公众号「三十五以后还有下文」

**[下载完整 ZIP](https://github.com/gitshilly/classroom-plugins/archive/refs/heads/main.zip)** · [先看文字版 SOP](docs/课件制作与交付SOP.md) · [更新记录](CHANGELOG.md) · [使用许可](LICENSE)

## 包含什么

| Skill | 主要做什么 |
|---|---|
| **家长进课堂课件制作** `parent-classroom-ppt` | 讨论选题、使用对象、记忆钩子与互动；确认大纲和代表性样张，再制作整套课件、逐字稿、教案与配套资料。 |
| **课堂课件验收与交付** `classroom-ppt-delivery` | 核对最终 PPT、备注、TXT、教案和附件的版本；检查页面、互动及交付清单，定位问题并在授权范围内修复。 |

插件版本：**1.2.2**。插件名：`parent-classroom-toolkit`。目录源名称：`my-classroom-plugins`。

## 适合谁

适合正在用 Codex 制作、修改儿童课堂课件，或希望核对课件交付的人。暂时不用 Codex，也可以先看[文字版 SOP](docs/课件制作与交付SOP.md)，把适用的要求用于自己的制作过程。

我目前积累的经验主要来自「家长进课堂」这个具体场景。家长决定去班上讲一节课以后，需要在上台前把内容准备好。主题讲得清楚、孩子能参与、讲稿和配套资料能用，都是这套流程优先考虑的事。我对其他类型 PPT 的设计与制作还在继续学习。

这些 Skills 提供流程、模板和核验脚本。**制作 PPT 和插画仍需要你的环境中有相应工具。**它不是装上以后就能无人看管、自动生成合格课件的独立制课软件。

## 下载与安装

### 方式一：下载完整文件

点击上方「下载完整 ZIP」，解压后保留整个仓库目录，包括 `.agents` 和 `plugins` 文件夹。使用支持插件的 Codex，在解压后的仓库根目录运行：

```sh
codex plugin marketplace add .
codex plugin add parent-classroom-toolkit@my-classroom-plugins
```

如果你不熟悉终端，可以把解压目录交给 Codex，说明：

> 请先阅读这个目录里的 README.md，核对当前客户端是否支持这里的插件安装方式，帮我安装「家长进课堂课件制作」和「课堂课件验收与交付」。先报告实际安装结果，不要直接开始制作课件。

### 方式二：从 GitHub 添加目录源

在支持插件的 Codex 环境中运行：

```sh
codex plugin marketplace add gitshilly/classroom-plugins --ref main
codex plugin add parent-classroom-toolkit@my-classroom-plugins
codex plugin list --marketplace my-classroom-plugins --json
```

安装后按客户端提示重新打开 Codex，并在新聊天中使用。插件入口和命令以你实际安装的客户端版本为准。这是自行添加的仓库目录源，不代表已经上架官方公共插件市场。

如果电脑上已经有同名独立技能，先确认插件可用，再决定保留哪一份，避免重复维护。上述命令不会自动删除旧技能。

## 怎么用

### 制作新课件

提供年级、主题想法、讲者身份、预计时长和已有资料，再对 Codex 说：

> 用「家长进课堂课件制作」制作新课。先和我确认主题、使用对象、一个具体有趣的钩子，以及孩子最容易参与的互动；再讨论逐页框架和代表性样张。制作完成后，接续「课堂课件验收与交付」。

### 检查已有课件

提供实际 PPT 和对应讲稿，对 Codex 说：

> 用「课堂课件验收与交付」检查这套 PPT 和逐字稿。保留现有画风，先说明检查的是哪些文件、发现了什么问题、哪些项目还没有验证。

### 项目规则与依赖

项目里已有 `AGENTS.md`、样张或确认过的规范时，提供给 Codex 一起读取。没有作者原项目的规则库也可以使用随包基本规范，但输出应说明缺少了哪些项目资料，不能声称加载了不存在的规则。

制作需要当前环境可用的 PPT、文件处理和图像生成工具；这些服务及其费用不包含在本仓库中。随包文件核验脚本需要 **Python 3.10+** 和 **Pillow**。从仓库根目录安装脚本依赖：

```sh
python -m pip install -r plugins/parent-classroom-toolkit/requirements.txt
```

脚本用法见[验收与工具](plugins/parent-classroom-toolkit/skills/classroom-ppt-delivery/references/verification.md)。文件检查、事实核验、实际放映、真实试讲和课堂效果分别记录；脚本通过不能替代这些实际检查。

## 使用许可

**允许使用这些 Skills 制作并售卖你自己的课件和配套资料；不允许把 Skills 本身原样或改名转卖。**

允许下载、使用、修改，以及保留作者声明和本许可的免费分享。具体范围以 [LICENSE](LICENSE) 为准。这是带有禁止转卖条件的公开分享许可，不是 MIT 许可。

## 持续调整与反馈

我会继续整理实际使用中的问题，更新流程和说明。遇到问题可以在 [Issues](https://github.com/gitshilly/classroom-plugins/issues) 中写清：你想做什么、进行到哪一步、实际发生了什么，以及能公开的错误信息。请不要提交买家个人信息、账号凭据或无权分享的资料。

公众号「三十五以后还有下文」会继续记录我用 AI 做资料、修改流程和尝试收入的真实过程。下载不需要关注、点赞或转发。

已有目录源可运行下面的命令刷新，再按客户端提示检查并更新实际安装版本：

```sh
codex plugin marketplace upgrade my-classroom-plugins
```

仅刷新目录源不等于所有客户端都已自动升级。

## 仓库内容

仓库包含流程、规范、空白模板和核验脚本，不附带在售课件。项目结构参照 [OpenAI 插件打包说明](https://developers.openai.com/plugins/build/plugins)。
