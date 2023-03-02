from typing import List, Tuple
import pandas as pd
import pathlib
import re

thisdir = pathlib.Path(__file__).parent.absolute()

regex = re.compile(r'(\d+\/\d+\/\d+).*')

def main():
    prompt = [
        "You are going to play the role of an English Tutor for a Portuguese speaker.",
        "Your purpose is to encourage conversation with the student and help them practice their English. ",
        "You should correct the student's grammar and spelling.",
        "You should also ask questions to encourage the student to speak more.",
        "Follow the example below:",
    ]

    text = thisdir.joinpath('whatsapp.txt').read_text()
    # iterate over lines
    conversation: List[Tuple[str, str]] = []
    authors = {
        "Dinho": "Student", 
        "Jared Coleman": "Teacher",
    }
    current_author = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = regex.match(line)
        if match:
            rest = line.split('-', 1)[1]
            try:
                author, message = rest.split(':', 1)
                author = author.strip()
                message = message.strip()
            except Exception:
                continue
            if author not in authors:
                continue
            if message in ["This message was deleted", "You deleted this message", "null"]:
                continue
            if authors[author] == current_author:
                conversation[-1][1] += '\n' + message
            else:
                conversation.append([authors[author], message])
                current_author = authors[author]
        elif conversation:
            conversation[-1][1] += '\n' + line

    # iterate over student messages and teacher responses
    current = "Teacher"
    pairs = []
    for i, (author, message) in enumerate(conversation):
        if author == current:
            continue
        if author == "Student":
            pairs.append([message, None])
            current = "Student"
        else:
            pairs[-1][1] = message
            current = "Teacher"

    
    prompt.append("")
    for i, (student, teacher) in enumerate(pairs):
        prompt.append(f"Student: {student}")
        prompt.append(f"Teacher: {teacher}")

    thisdir.joinpath('prompt.txt').write_text('\n'.join(prompt))

if __name__ == '__main__':
    main()