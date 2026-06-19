from difflib import SequenceMatcher

CONFLICT_START = "<<<<<<< ALTERACOES DA REDE"
CONFLICT_SEPARATOR = "======="
CONFLICT_END = ">>>>>>> SUAS ALTERACOES LOCAIS"


def _format_conflict_block(remote_lines: list[str], local_lines: list[str]) -> list[str]:
    block = [CONFLICT_START]
    block.extend(f"+ {line}" for line in remote_lines)
    block.append(CONFLICT_SEPARATOR)
    block.extend(f"- {line}" for line in local_lines)
    block.append(CONFLICT_END)
    return block


def create_merge_conflits_marks(local_content: str, remote_content: str) -> str:
    local_lines = local_content.splitlines()
    remote_lines = remote_content.splitlines()

    if local_content == remote_content:
        return local_content

    if not local_lines:
        return remote_content

    if not remote_lines:
        return local_content

    matcher = SequenceMatcher(None, local_lines, remote_lines)
    merged_lines: list[str] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            merged_lines.extend(local_lines[i1:i2])
        elif tag == "insert":
            merged_lines.extend(remote_lines[j1:j2])
        elif tag == "delete":
            continue
        elif tag == "replace":
            merged_lines.extend(_format_conflict_block(remote_lines[j1:j2], local_lines[i1:i2]))

    return "\n".join(merged_lines)


def has_merge_conflict_marks(content: str) -> bool:
    return CONFLICT_START in content and CONFLICT_SEPARATOR in content and CONFLICT_END in content
