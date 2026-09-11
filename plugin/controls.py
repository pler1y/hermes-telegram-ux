"""Route exact natural controls before Telegram's text batching and busy-input fast path."""
import logging
import re

logger=logging.getLogger(__name__)
ALIASES={
    '停一下':'/stop','先停下':'/stop','停止当前任务':'/stop','停止任务':'/stop',
    '查看状态':'/status','查看用量':'/usage','查看正在运行的任务':'/agents',
    '新建会话':'/new','查看历史会话':'/sessions',
}


def command_for(text):
    return ALIASES.get((text or '').strip().rstrip('。！!'))


def wire(application,adapter):
    from telegram import Message,Update
    from telegram.ext import MessageHandler,filters,ApplicationHandlerStop

    async def control(update,context):
        msg=update.effective_message
        command=command_for(msg.text if msg else '')
        if not command:
            return
        # Keep the original text-addressing rules in groups; a casual unmentioned phrase must
        # not acquire command privileges merely because this adapter can translate it.
        if not adapter._should_process_message(msg,is_command=False):
            return
        payload=msg.to_dict()
        payload.update(text=command,entities=[{'type':'bot_command','offset':0,'length':len(command)}])
        forwarded=Update(update_id=update.update_id,message=Message.de_json(payload,context.bot))
        try:
            # This native entry constructs MessageType.COMMAND and performs authorization before
            # dispatch. Rewriting text at pre_gateway_dispatch is too late for the busy fast path.
            await adapter._handle_command(forwarded,context)
        except Exception as exc:
            logger.warning('Natural Telegram control failed (%s)',type(exc).__name__)
            await msg.reply_text('这次没能确认操作结果，请直接发送 '+command+'。')
        raise ApplicationHandlerStop

    pattern=r'^\s*(?:'+'|'.join(re.escape(text) for text in ALIASES)+r')[。！!]*\s*$'
    handler=MessageHandler(filters.TEXT & filters.Regex(pattern),control)
    application.add_handler(handler,group=-3)
    return lambda: application.remove_handler(handler,group=-3)
