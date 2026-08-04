# ChatCut Agent Prompt Templates

Use these templates only after inspecting the current project. Replace every bracketed value.

## Save the Complete Workflow as a ChatCut Skill

For ChatCut-native use without the local material panel, open the AI panel's `Skills` picker, choose `Save this editing process as a Skill`, and paste `assets/chatcut-direct-remix-skill.txt`.

- The saved Skill belongs to the ChatCut account and is reusable across that account's projects.
- On another computer with the same ChatCut account, select the saved Skill directly.
- For another account, share the ChatCut project and recreate the Skill from the same text file.
- GitHub stores the reusable workflow text, not ChatCut login sessions, cloud project rows, uploaded media, or account-specific asset IDs.

## Base Timeline

```text
直接更新当前主时间线，不要重新检索已经验证的素材，也不要回复计划。

目标：制作 [时长] 秒、[画幅]、[平台] 广告。
保持同源连续块：同一个源素材的多个可用片段尽量连续使用，再在故事边界切换来源。

按以下顺序放入 V1，全部素材原声 [静音/保留]：
[时间段] [asset ID] [画面角色]
[时间段] [asset ID] [画面角色]

保持每个动作完整，不使用 A→B→A→C→A 式跳切。完成后调用 read_project 验证总时长与轨道。
```

## Final Voice Replacement

```text
不要改动 V1、上层动效和 BGM。删除或替换 A1 现有旁白。

使用 ElevenLabs voice=[voice]、model=[model] 生成以下 [语言] 旁白：
[旁白全文]

音频必须自然完整且不超过 [最大时长] 秒，严禁裁断；若超时，先精简文案或重新生成。
从 0 秒放入 A1。删除旧字幕并从新旁白重新生成独立字幕，保持现有字体、描边和安全区。最后调用 read_project 验证 A1 不被截断。
```

## HyperFrames Native Fallback

```text
把已确认的 HyperFrames 动效设计原生落到当前 ChatCut 可编辑时间线。不要重新分析素材；保持 V1、A1、A2、字幕和总时长不变。

1. 删除或替换旧 CTA，避免双重叠加。
2. 新建上层轨道 HF_Hook_CTA。
3. 使用 create_motion_graphic_from_code 创建透明背景、[宽]×[高]、[fps]fps 动效。
4. 0–3 秒依次显示：[钩子文案]。入场 0.2–0.4 秒，核心词使用 [强调色]，不要遮挡商品和人物脸部。
5. 最后 [CTA时长] 秒显示：[价格] / [颜色或优惠] / [CTA]。结尾停留至少 1.5 秒，底部保留 15% 安全区。
6. 完成后调用 read_project，并渲染开场和 CTA 代表帧确认没有遮挡。

这是 HyperFrames 设计的 ChatCut 原生可编辑复刻；不要声称已导入外部渲染文件。
```

## Final Verification

```text
只做最终校验，不重新剪辑：
1. read_project 验证总时长、轨道和旁白长度；
2. 检查约 0.5 秒、中段卖点和结束前 0.7 秒的合成帧；
3. 确认商品、脸部、关键细节、字幕和 CTA 无遮挡；
4. 确认旧 CTA 已移除，价格只出现一次；
5. 输出实际轨道结构和发现的问题。
```
