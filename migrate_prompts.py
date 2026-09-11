"""Replace only this plugin's canonical frozen prompt section. No chat messages changed."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
from plugin.experience import PROMPT

SECTION_ID = 'hermes_interaction.telegram'

def replace_section(prompt):
    from agent.system_prompt import _restore_plugin_prompt_sections
    from hermes_cli.plugins import format_system_prompt_sections, RenderedPluginSystemPromptSection, PLUGIN_SECTIONS_START
    sections = _restore_plugin_prompt_sections(prompt)
    if not sections:
        boundary = prompt.rfind('\n\nConversation started:')
        # Fail closed for a malformed/unknown frame, and for non-native prompt structures.
        if boundary < 0 or PLUGIN_SECTIONS_START in prompt:
            return prompt
        section = RenderedPluginSystemPromptSection(id=SECTION_ID,content=PROMPT,
            position='after_memory',plugin='hermes-interaction')
        return prompt[:boundary] + '\n\n' + format_system_prompt_sections([section]) + prompt[boundary:]
    if not any(s.id == SECTION_ID for s in sections):
        sections = tuple(sections)
        old = format_system_prompt_sections(sections)
        added = RenderedPluginSystemPromptSection(id=SECTION_ID,content=PROMPT,position='after_memory',plugin='hermes-interaction')
        at = prompt.rfind(old)
        return prompt[:at] + format_system_prompt_sections([*sections,added]) + prompt[at+len(old):]
    updated = [RenderedPluginSystemPromptSection(id=s.id,content=PROMPT,position=s.position,plugin=s.plugin)
               if s.id == SECTION_ID else s for s in sections]
    old = format_system_prompt_sections(sections)
    new = format_system_prompt_sections(updated)
    at = prompt.rfind(old)
    return prompt[:at] + new + prompt[at+len(old):] if at >= 0 else prompt

