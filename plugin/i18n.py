"""Fixed package language and user-facing copy. No detection, network or model calls."""
from __future__ import annotations

import json
from pathlib import Path
import re


def package_language():
    try:
        value = json.loads(Path(__file__).with_name("language.json").read_text())["language"]
    except (OSError, ValueError, KeyError, TypeError):
        value = "zh"
    return value if value in {"zh", "en"} else "zh"


EN = {
    "收到这条消息了。": "Got your message.",
    "暂时无法继续这个操作，请直接发送一条消息。": "I couldn't continue that action. Please send a message directly.",
    "想一下…": "Let me think 🤔",
    "我看一下…": "Let me take a look 👀",
    "好，我看一下 👀": "Let me take a look 👀",
    "在呢 👋": "Hey! 👋",
    "不客气 😊": "You're welcome 😊",
    "嗯，收到 👌": "Got it 👌",
    "看看刚查到的内容…": "Let me check what turned up 🧐",
    "整理一下…": "Putting it together ✍️",
    "收到，补充已记下。": "Got it — thanks for the update.",
    "收到，这条会在当前任务后处理。": "Got it — this will run after the current task.",
    "收到，会按你的新要求处理。": "Got it — I'll use your updated request.",
    "收到，正在切换到你的新要求。": "Got it — switching to your updated request.",
    "⚠️ 本次模型请求未成功，正在等待后续处理。": "⚠️ The model request failed. Waiting for the next step.",
    "⚠️ 这次未能完成。可直接问我已完成哪些，以及下一步怎么处理。": "⚠️ I couldn't finish this. You can ask what was completed and what to do next.",
    "⏹️ 当前任务已中断；已执行的操作不会自动撤销。": "⏹️ The task was interrupted. Earlier actions haven't been undone.",
    "这次请求没有成功，还没有拿到结果。": "The request didn't succeed; there isn't a result yet.",
    "还在处理。你可以继续补充，也可以说“停一下”。": "Still working. You can add a detail or say “stop the task”.",
    "这一步等待较久，暂未收到新结果。需要结束可发送 /stop。": "This step is taking a while; no new result yet. Send /stop to cancel.",
    "等待你确认：请先处理聊天中的操作确认请求。": "Waiting for your approval — please check the confirmation in this chat.",
    "正在检查操作权限。": "Checking permission for this action.",
    "⚠️ 有一步未成功，正在核对影响和后续办法。": "⚠️ One step failed. Checking what it affects and how to continue.",
    "查找资料…": "Looking for information…", "看看这份内容…": "Reading this…",
    "核对一下来源…": "Checking the source…", "正在修改…": "Making the changes…",
    "算一下…": "Working out the numbers…", "后台还在处理…": "The background task is still working…",
    "正在制作…": "Creating it…", "验证一下结果…": "Checking the result…",
    "正在部署…": "Deploying…", "还在处理…": "Still working…",
    "这次搜索没拿到结果。": "The search didn't return a result.",
    "这轮测试没通过。": "This test run didn't pass.",
    "部署这一步没有成功。": "The deployment step didn't succeed.",
    "刚才这一步没成功。": "That step didn't succeed.",
    "这次没有找到匹配的资料。": "No matching information turned up.",
    "已找到 {count} 条候选资料。": "Found {count} potential sources.",
    "搜索已返回。": "The search returned results.",
    "这轮测试通过了。": "This test run passed.",
    "测试有返回，正在核对结果。": "The test returned output; checking the result.",
    "执行命令已结束，还需要确认实际运行情况。": "The command finished; checking that it works as intended.",
    "部署步骤有返回，还需要核对结果。": "The deployment returned output; checking the result.",
    "检查有返回，正在核对是否符合预期。": "The check returned output; comparing it with the expected result.",
    "内容已写入，正在检查。": "The content was written; checking it now.",
    "内容已生成，正在检查效果。": "The content was generated; reviewing it now.",
    "正在核对资料，整理与你有关的部分…": "Checking the information and picking out what matters for you…",
    "正在核对这一步的结果…": "Checking this step's result…",
    "正在搜索相关资料…": "Looking for relevant information…",
    "正在阅读，核对具体内容…": "Reading through the details…",
    "先看看现有内容和情况…": "Taking a look at what's there…",
    "正在修改内容…": "Making the changes…",
    "先运行测试，看看结果是否符合预期…": "Running the tests to check the result…",
    "正在执行部署步骤…": "Running the deployment steps…",
    "正在执行包含测试和部署的步骤…": "Running the test and deployment steps…",
    "正在执行部署和运行检查…": "Deploying and checking it runs…",
    "正在检查部署后的运行情况…": "Checking how it runs after deployment…",
    "正在计算并核对结果…": "Working out and checking the numbers…",
    "正在制作内容…": "Creating the content…",
    "任务已交给后台继续处理…": "The background task is taking it from here…",
    "我在翻一下前面的对话…": "Looking back through our conversation…",
    "正在核对失败的影响，看看下一步怎么处理…": "Checking what the failure affects and how to continue…",
    "正在执行这一步，等它返回结果…": "Running this step and waiting for its result…",
    "正在处理这一步…": "Working on this step…",
    "还在想，回答还没准备好。": "Still thinking this through 🤔",
    "（还有 {count} 步同时进行）": " ({count} other steps are running)",
    "这一步还没返回新结果，可以继续补充，也可以说“停一下”。": "No new result from this step yet. You can add a detail or say “stop the task”.",
    "还在核对这些结果，暂时没有新的进展。": "Still checking these results; nothing new to report yet.",
    "接下来：": "Next: ", "已确认：": "Confirmed: ",
    "已经确认：": "Confirmed: ", "刚才在做：": "Last working on: ",
    "好，已请求停止。": "Stop requested ⏹️",
    "好，正在停止后台任务。": "Stopping the background task ⏹️",
    "之前的操作不会自动撤销。": "Earlier actions haven't been undone.",
    "后台步骤已结束，正在核对结果。": "The background step finished; checking its result.",
    "服务暂时离线，恢复后可以继续发消息。": "The service is going offline. You can continue when it's back.",
    "已更新使用偏好。": "Your preferences have been updated.",
    "🧠 正在整理前面的聊天，稍等一下。": "🧠 Tidying up our earlier conversation. Hang on a moment.",
    "🧐 前面的聊天整理好了，继续看你的问题。": "🧐 Earlier conversation tidied up. Back to your request.",
    "⚠️ 聊天整理没能完成，正在处理后续步骤。": "⚠️ Couldn't finish tidying up the conversation. Handling the next step.",
    "🧠 聊天整理还没完成，这次先沿用原来的内容继续。": "🧠 The conversation summary isn't ready yet. Continuing with the original context for now.",
    "⚠️ 聊天整理等得太久，这次先沿用原来的内容继续。可用 /compress 重试。": "⚠️ Summarizing took too long. Continuing with the original context; use /compress to try again.",
    "⚠️ 聊天整理没有成功，原来的消息仍然保留。可用 /compress 重试，或检查整理模型的设置。": "⚠️ Summarizing didn't succeed. Your original messages are still there. Use /compress to retry or check the compression model settings.",
    "🧠 专用整理模型没有成功，已用当前模型完成整理。可以稍后检查整理模型的设置。": "🧠 The dedicated compression model failed, but your main model finished the summary. You can check the compression model settings later.",
    "🔌 连接暂时中断，正在重新连接。": "🔌 The connection dropped. Reconnecting now.",
    "🔌 连接恢复了，继续处理。": "🔌 Connected again. Picking up where we left off.",
    "⚠️ 这一步遇到了问题，请查看接下来的说明。": "⚠️ This step hit a problem. Details will follow.",
    "[链接]": "[link]", "[已隐藏]": "[redacted]", "[文件位置]": "[file location]",
    "接下来可以：": "You could try:", "选项无效。": "That option isn't available.",
    "这组选项已过期、已使用或对话已更新。请直接输入想做的事。": "These options have expired, were already used, or belong to an earlier turn. Just type what you'd like to do.",
    "只能由原会话中的用户操作。": "Only the original user can use these options in the original chat.",
    "这组选项已使用。": "These options have already been used.",
    "已选择：{label}，正在提交。": "Selected: {label}. Sending it now.",
    "从一件小事开始": "Start with something small",
    "发个问题、链接或者文件过来就行。\n也可以先选一件试试。": "Send a question, a link, or a file.\nOr pick something below to try.",
    "查点资料": "Find information", "读链接或文件": "Read a link or file",
    "写几句话": "Write something", "更多设置": "More options",
    "想查什么？": "What would you like to find?",
    "直接告诉我想知道的事，也可以试试下面这个。": "Tell me what you'd like to know, or try the example below.",
    "看看最近的 AI 产品更新": "Explore recent AI updates",
    "帮我找最近三条普通人能直接用的 AI 产品更新，每条两句话，附官网来源。不需要深入研究。": "Find three recent AI product updates useful to everyday users. Give two sentences for each with an official source. Keep the research brief.",
    "把内容发过来": "Send it over",
    "发链接、图片或文件，再说一句你想看什么。\n\n比如：这篇文章主要讲什么？有哪些地方需要留意？": "Send a link, image, or file and say what you'd like to know.\n\nFor example: What's this article about, and what should I pay attention to?",
    "想写什么？": "What would you like to write?",
    "告诉我写给谁、想说什么，或者把草稿贴过来。\n\n比如：帮我把这段话写得自然一点，意思别变。": "Tell me who it's for and what you'd like to say, or paste a draft.\n\nFor example: Make this sound more natural without changing the meaning.",
    "试一段改写": "Try a rewrite",
    "把这句话改得自然一点，只给改好的话：您好，烦请您于方便之时向我提供该文件，非常感谢您的配合。": "Make this sentence sound natural. Return only the rewrite: Kindly provide the aforementioned document at your earliest convenience. Your cooperation is greatly appreciated.",
    "日常使用直接发消息即可。这里保留任务与设置入口。": "Just send a message for everyday use. Tasks and settings are here when you need them.",
    "正在运行的任务": "Running tasks", "历史对话": "Conversations",
    "用量与限额": "Usage and limits", "当前设置": "Current settings",
    "停止当前任务": "Stop current task", "返回": "Back", "关闭": "Close",
    "也可以直接在下面继续说。": "You can also keep typing below.",
    "请在与机器人的私聊中打开开始页面。": "Open this menu in a private chat with the bot.",
    "这个入口已过期，发送“开始使用”可以重新打开。": "This menu has expired. Send /start to open it again.",
    "只能由打开菜单的用户在原会话中操作。": "Only the user who opened this menu can use it in the original chat.",
    "选项无效，请重新打开菜单。": "That option isn't available. Please reopen the menu.",
    "随时直接发消息就行。": "Just send a message whenever you're ready.",
    "操作结果暂时无法确认，请查看 Hermes 回复后再操作。": "I couldn't confirm the outcome. Check Hermes' reply before trying again.",
    "这次没能确认操作结果，请直接发送 {command}。": "I couldn't confirm the outcome. Please send {command} directly.",
}

# Only interpolate known UI templates. User/model text is never evaluated as a template.
_NUMERIC = [(re.compile(re.escape(k).replace(r"\{count\}", r"(\d+)")), v)
            for k, v in EN.items() if "{count}" in k]


def tr(text, language="zh", **values):
    translated = EN.get(text, text) if language == "en" else text
    return translated.format(**values) if values else translated


def localize(text, language="zh"):
    if language != "en" or not isinstance(text, str):
        return text
    if text in EN:
        return EN[text]
    # Legacy state stores contain short Chinese message IDs; translate those at rendering.
    for pattern, template in _NUMERIC:
        text = pattern.sub(lambda m: template.format(count=m.group(1)), text)
    for key in sorted((k for k in EN if "{" not in k), key=len, reverse=True):
        text = text.replace(key, EN[key])
    return text


def greeting(text, language="zh"):
    clean = (text or "").strip().lower().rstrip("!！。.?？~～")
    if clean in {"你好", "您好", "嗨", "哈喽", "在吗", "hello", "hi", "hey", "hey there"}:
        key = "在呢 👋"
    elif clean in {"谢谢", "多谢", "感谢", "thanks", "thank you", "thank you very much"}:
        key = "不客气 😊"
    elif clean in {"好", "好的", "嗯", "ok", "okay", "got it"}:
        key = "嗯，收到 👌"
    else:
        key = "好，我看一下 👀"
    return tr(key, language)


ICONS = {"opening": "🤔", "search": "🔎", "read": "📄", "inspect": "🧐",
         "write": "✍️", "test": "🧪", "verify": "🧐", "calculate": "🧮",
         "create": "🎨", "background": "🛠️", "recall": "💭", "recover": "🛠️",
         "analyze": "🧐", "deploy": "🛠️", "operate": "🛠️"}


def decorate(text, stage="opening", enabled=True):
    if not text or not enabled:
        return text
    first = text.split("\n", 1)[0]
    # Respect the model's own emoji. Never rotate indicators while the state is unchanged.
    if any(ord(c) >= 0x1F000 or 0x2600 <= ord(c) <= 0x27BF for c in first):
        return text
    return ICONS.get(stage, "🛠️") + " " + text
