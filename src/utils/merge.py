import difflib
import subprocess

def create_merge_conflits_marks(local_content: str, remote_content: str) -> str:
    local_content_splited = local_content.splitlines()
    remote_content_splited = remote_content.splitlines()

    marks = []
    diff = list(difflib.ndiff(local_content_splited, remote_content_splited))

    has_conflits = False
    local_chunks = []
    remote_chunks = []

    for line in diff:
        status = line[:2]
        text = line[2:]

        if status == '  ':
            if local_chunks or remote_chunks:
                marks.append("<<<<<<< SUAS ALTERAÇÕES LOCAIS")
                marks.extend(local_chunks)
                marks.append("=======")
                marks.extend(remote_chunks)
                marks.append(">>>>>>> ALTERAÇÕES REMOTAS DA REDE")
                local_chunks, remote_chunks = [], []
            marks.append(text)

        elif status == '- ':  # Alteração local
            local_chunks.append(text)
        elif status == '+ ':  # Alteração remota
            remote_chunks.append(text)

    if local_chunks or remote_chunks:
        marks.append("<<<<<<< SUAS ALTERAÇÕES LOCAIS")
        marks.extend(local_chunks)
        marks.append("=======")
        marks.extend(remote_chunks)
        marks.append(">>>>>>> ALTERAÇÕES REMOTAS DA REDE")

    return "\n".join(marks)