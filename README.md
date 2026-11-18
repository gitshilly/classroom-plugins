# 我的课堂插件仓库

一个可安装插件，包含两套配合使用的技能：

- **家长进课堂课件制作**（parent-classroom-ppt）：投入判断与四格确认、多轮共创、事实依据、课堂互动、视觉方案、整套制作、逐字稿及教学资料。
- **课堂课件验收与交付**（classroom-ppt-delivery）：版本配对、备注/TXT核对、页面与教学包清单、真实商品展示及反馈修复。

插件版本：1.1.0。插件名：parent-classroom-toolkit。仓库目录源名称：my-classroom-plugins。

## 换电脑安装

在新电脑安装支持插件的 Codex，并让 Git 正常访问私有仓库 https://github.com/gitshilly/classroom-plugins 。在终端运行：

```sh
codex plugin marketplace add gitshilly/classroom-plugins --ref main
codex plugin add parent-classroom-toolkit@my-classroom-plugins
codex plugin list --marketplace my-classroom-plugins --json
```

然后重新打开 Codex，在新聊天中使用技能。也可在支持自定义目录源的客户端选择“我的课堂插件仓库”并安装。客户端入口和可用性以实际版本为准。这是私人仓库目录源，不是公共插件市场上架；新电脑需要先添加目录源。

如果直接拿到本仓库完整文件，在仓库根目录运行：

```sh
codex plugin marketplace add .
codex plugin add parent-classroom-toolkit@my-classroom-plugins
```

现有电脑若已经装了两个同名独立技能，确认插件可用后再选择保留哪一份，避免重复维护；安装过程不自动删除旧技能。

## 使用方式

直接对 Codex 说：

> 用“家长进课堂课件制作”制作新课，先整理投入检查和选题四格，只追问关键缺口，确认后再做框架与样张；制作完成后接续“课堂课件验收与交付”。

或：

> 用“课堂课件验收与交付”检查我提供的PPT和逐字稿，保留现有画风，先报告问题。

提供实际课件、资料及项目规则。项目规则缺失时使用随包基本规范并报告缺口，不声称已经加载原电脑的全部规则。

## 所需能力与依赖

技能提供工作流和模板，不自带PPT编辑器、图片生成服务或全部制作运行库。具体制作仍需要当前客户端可用的演示文稿、图像生成和文件工具；缺少时如实说明。

文件核验脚本需要 Python 3.10+ 和 Pillow。在使用检查脚本的环境中运行：

```sh
python -m pip install -r plugins/parent-classroom-toolkit/requirements.txt
```

参考技能内 references/verification.md 配置实际文件。脚本不包含凭据，不自动发布商品或联系买家。

## 维护与更新

在本仓库编辑技能及资源，修改插件版本并记录变更。先核验脚本和安装识别，再提交、推送至私有远程仓库。新电脑刷新目录源：

```sh
codex plugin marketplace upgrade my-classroom-plugins
```

刷新目录后检查插件实际安装版本，按客户端提示更新或重新安装；目录刷新不等于已验证所有客户端自动升级。

## 内容与边界

包含流程、规范、空白模板和核验脚本；不包含在售PPT、原书图片、买家信息、账号运营数据或原项目完整规则库。原课件资产需另行迁移。

本地文件核验、事实核验、放映测试、真实试讲与销售反馈分别记录。任何未完成的检查不能标为通过。不承诺无人值守制课或销售效果。

目前为个人私有使用包，未授予公开再分发许可；公开发布前需另行确定许可、作者资料与展示内容。

## 格式依据

按 [OpenAI 官方插件打包说明](https://developers.openai.com/plugins/build/plugins)组织。目录路径相对仓库根目录，无固定电脑盘符。
