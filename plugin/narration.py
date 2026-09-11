"""Read only public assistant content accompanying tools, never reasoning or final answers."""
from __future__ import annotations
import re
from copy import deepcopy

SETUP_TOOLS = {"tool_search", "tool_describe", "skill_view"}
UI_TOOLS = {"interaction_update", "interaction_actions", "telegram_followup_actions"}
PROGRESS_FIELD = "_hermes_progress"
PROGRESS_DESCRIPTION = (
    "显示给用户的进度，和最终答案分开。用一句日常聊天的短句，说清这一整步在帮用户确认或完成什么，"
    "必要时说一句原因。贴近本次问题的对象和限制；不要像任务标题那样只列动作，不用专业黑话或客服套话，"
    "可以自然搭配贴合语境的表情，不强行亲昵或随机轮播。首次操作、换方法、遇到问题、读到补充后，写清具体变化。"
    "不要写隐藏推理、工具名、路径、密钥或未经证实的成功。只有界面已经有说明且这一步没有变化时才可以留空。"
    "此字段在执行前移除，不属于实际操作参数。"
)
REQUEST_REMINDER = (
    "Telegram delivery requirement for the next response: this UI has a separate progress bubble. "
    "If you call a substantive tool, supply _hermes_progress as one brief Chinese public action sentence "
    "specific to the user's current goal, or put that sentence in public assistant text accompanying "
    "the tool call. The first action and a changed step/user constraint need a concrete sentence. "
    "An unchanged continuation may leave the field empty. This is NOT a separate reply or final answer. "
    "Do not reveal private reasoning or invent findings. If ready to answer, simply send the complete "
    "final answer without calling a tool just for progress."
)


def accepts_null(schema):
    typ = schema.get('type')
    return typ == 'null' or (isinstance(typ,list) and 'null' in typ) or any(accepts_null(s) for s in schema.get('anyOf',[]) if isinstance(s,dict))


def _simple_parameter(schema):
    if not isinstance(schema,dict) or any(k in schema for k in ('oneOf','allOf','$ref','const','properties')):
        return False
    if 'anyOf' in schema:
        return isinstance(schema['anyOf'],list) and bool(schema['anyOf']) and all(_simple_parameter(s) for s in schema['anyOf'])
    typ = schema.get('type')
    types = [typ] if isinstance(typ,str) else typ
    return (isinstance(types,list) and bool(types) and all(t in ('string','integer','number','boolean','null','array') for t in types)
        and ('array' not in types or _simple_parameter(schema.get('items'))))


def _nullable(schema):
    if not accepts_null(schema):
        if 'anyOf' in schema:
            schema['anyOf'].append({'type':'null'})
        else:
            typ=schema['type']
            schema['type'] = [*typ,'null'] if isinstance(typ,list) else [typ,'null']
    if isinstance(schema.get('enum'),list) and None not in schema['enum']:
        schema['enum'].append(None)


def with_progress_schema(request, *, strict_tools=True, require_note=False, language="zh"):
    """Decorate request-local function schemas; never mutate registered tools or permissions."""
    if not isinstance(request, dict) or not isinstance(request.get("tools"), list):
        return None
    updated = dict(request)
    updated["tools"] = []
    description = PROGRESS_DESCRIPTION if language == "zh" else (
        "A brief, natural English action update for the user. Explain the purpose of this step "
        "and any actual change of approach or constraints. Be specific to the user's task. "
        "A fitting emoji is welcome; avoid forced intimacy. No hidden reasoning, tool names, "
        "paths, secrets or unverified success. Empty means an unchanged continuation only. "
        "This display field is removed before the tool executes."
    )
    reminder = REQUEST_REMINDER.replace("one brief Chinese", "one brief " + ("Chinese" if language == "zh" else "English"))
    reminder += " Use the same interface language for progress, action buttons and default replies. A fitting emoji is welcome; do not fill pauses with random updates."
    changed = False
    for original in request["tools"]:
        tool = deepcopy(original)
        if not isinstance(tool, dict):
            updated["tools"].append(tool)
            continue
        function = tool.get("function", tool)
        if not isinstance(function, dict):
            updated["tools"].append(tool)
            continue
        name = function.get("name", "")
        schema = function.get("parameters", function.get("input_schema"))
        if (name and name not in SETUP_TOOLS | UI_TOOLS and isinstance(schema, dict)
                and schema.get("type") == "object" and isinstance(schema.get("properties"), dict)
                and not any(key in schema for key in ("oneOf", "anyOf", "allOf"))
                and PROGRESS_FIELD not in schema["properties"]):
            schema["properties"][PROGRESS_FIELD] = {
                "type": "string", "maxLength": 160, "description": description}
            if require_note:
                schema['properties'][PROGRESS_FIELD]['minLength'] = 1
                schema['properties'][PROGRESS_FIELD]['description'] += ('本轮尚无有效说明或需要交代新变化，必须写非空的一句话。' if language == 'zh' else ' A concrete nonempty update is required for this new or changed step.')
            schema["required"] = [*schema.get("required", []), PROGRESS_FIELD]
            # Strict schemas prevent a provider from silently omitting the presentation field.
            # Only flat, fully understood schemas are upgraded; complex native schemas retain
            # their original contract. Optional null placeholders are removed before execution.
            if (strict_tools and 'parameters' in function and schema.get('additionalProperties',False) is False
                    and all(_simple_parameter(prop) for prop in schema['properties'].values())):
                required = set(schema['required'])
                for key,prop in schema['properties'].items():
                    if key not in required:
                        _nullable(prop)
                    prop.pop('default',None)
                schema['required'] = list(schema['properties'])
                schema['additionalProperties'] = False
                function['strict'] = True
            changed = True
        updated["tools"].append(tool)
    if not changed:
        return None
    # Keep the delivery contract on each request without adding messages to saved history.
    if isinstance(updated.get("instructions"), str):
        updated["instructions"] += "\n\n" + reminder
    elif "system" in updated:
        system = updated["system"]
        if isinstance(system, str):
            updated["system"] = system + "\n\n" + reminder
        elif isinstance(system, list):
            updated["system"] = [*system, {"type":"text","text":reminder}]
    elif isinstance(updated.get("messages"), list):
        updated["messages"] = [*updated["messages"], {"role":"system","content":reminder}]
    return updated


def field(value, name, default=None):
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)


def public_text(value):
    if isinstance(value, str):
        text = value
    elif isinstance(value, list):
        text = "\n".join(field(p, "text", "") for p in value
            if field(p, "type") in {"text", "output_text"} and isinstance(field(p, "text"), str))
    else:
        return ""
    # Suppress closed and truncated private scratchpads; never inspect reasoning fields.
    for tag in ("think", "thinking", "reasoning", "analysis", "REASONING_SCRATCHPAD"):
        text = re.sub(rf"<{tag}\b[^>]*>.*?(?:</{tag}>|$)", "", text, flags=re.I | re.S)
    if re.search(r"```|\bMEDIA:|^\s*(?:analysis|reasoning)\s*:", text, re.I):
        return ""
    text = re.sub(r"[*_`#]", "", text)
    text = " ".join(text.split())
    if re.match(r"^(?:结论[：:]|答案[：:]|结果如下|我推荐|推荐[ ：A-Z]|最终结果)", text):
        return ""
    if re.match(r"^(?:final (?:answer|result)|(?:the )?(?:answer|conclusion)\s*:|here (?:are|is) (?:the |your )?(?:results?|answer)|I recommend\b)", text, re.I):
        return ""
    # Do not turn a report/partial answer into a prematurely displayed final reply.
    if len(text) > 280 or not text or text == "(empty)":
        return ""
    return text


def tool_note(message):
    """Return public text and the real calls it accompanies, or None for final/UI-only output."""
    calls = []
    for call in field(message, "tool_calls", []) or []:
        function = field(call, "function", {})
        name = field(function, "name", "")
        if name and name not in SETUP_TOOLS | UI_TOOLS:
            calls.append((str(field(call, "id", "") or field(call, "call_id", "")), name))
    if not calls:
        return None
    raw = field(message, "_raw_response_output")
    if isinstance(raw, list) and any(field(p, "type") == "message" and field(p, "channel") for p in raw):
        text = " ".join(public_text(field(p, "content")) for p in raw
            if field(p, "type") == "message" and field(p, "channel") == "commentary")
    else:
        text = public_text(field(message, "content"))
    return (text, calls) if text else None
