"""Live-test-only policy: request native approval for harmless marked commands."""


def request_approval(tool_name="", args=None, **kwargs):
    command = args.get("command", "") if isinstance(args, dict) else ""
    if tool_name == "terminal" and command.startswith("printf CAT916_APPROVAL_"):
        return {"action": "approve", "message": "Catalog acceptance: approve or deny this marked test command",
                "rule_key": command}
    return None


def register(ctx):
    ctx.register_hook("pre_tool_call", request_approval)
