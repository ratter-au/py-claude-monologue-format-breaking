#!/usr/bin/env python3

from typing import (
    ForwardRef,
    TypedDict,
    Required,
    NotRequired,
    ReadOnly,
    Literal,
)

from json import (
    loads as json_load_string,
    dumps as json_dump_string,
)

from sys import (
    stderr,
)

class Chunk(TypedDict, total=False):
    id: Required[str]
    previous_chunk_id: Required[None | str]
    role: Required[Literal["system"] | Literal["user"] | Literal["assistant"]]
    status: Required[Literal["prefilled"] | Literal["processing"] | Literal["succeeded"] | Literal["errored"] | Literal["expired"] | Literal["canceled"]]
    error: Required[None | dict]
    stop_reason: Required[None | Literal["end_turn"] | Literal["stop_sequence"] | Literal["max_tokens"] | Literal["refusal"]]
    stop_sequence: Required[None | str]
    cost: Required[float]
    text: Required[str]

class ThreadedChunk(Chunk, total=True):
    continuations: Required[list[ForwardRef("ThreadedChunk")]]

threaded_chunks: dict[str, ThreadedChunk] = dict()
root_threaded_chunks: list[ThreadedChunk] = list()

# Read chunks from standard input
while True:
    try:
        chunk_json = input()
    except EOFError:
        break
    if not chunk_json: continue
    chunk = json_load_string(chunk_json, object_hook=Chunk)
    chunk_id = chunk["id"]
    previous_chunk_id = chunk["previous_chunk_id"]
    previous_chunk = None if not previous_chunk_id else threaded_chunks[previous_chunk_id]
    threaded_chunk = ThreadedChunk({
        "id": chunk_id,
        "previous_chunk": previous_chunk,
        "role": chunk["role"],
        "status": chunk["status"],
        "error": chunk["error"],
        "stop_reason": chunk["stop_reason"],
        "stop_sequence": chunk["stop_sequence"],
        "cost": chunk["cost"],
        "text": chunk["text"],
        "continuations": list(),
    })
    threaded_chunks[chunk_id] = threaded_chunk
    if not previous_chunk:
        print(f"chunk {chunk_id} is a root chunk", file=stderr, flush=True)
        root_threaded_chunks.append(threaded_chunk)
    else:
        print(f"chunk {chunk_id} continues from chunk {previous_chunk_id}", file=stderr, flush=True)
        previous_threaded_chunk = threaded_chunks[previous_chunk_id]
        previous_threaded_chunk["continuations"].append(threaded_chunk)

def html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def write_chunk(chunk: ThreadedChunk) -> None:
    chunk_id = chunk["id"]
    previous_chunk = chunk["previous_chunk"]
    previous_chunk_id = None if not previous_chunk else previous_chunk["id"]
    continuations = chunk["continuations"]
    print(f"writing chunk {chunk_id}", file=stderr, flush=True)
    print(f"""<article class="chunk" id="{chunk_id}">""")
    try:
        if previous_chunk and len(previous_chunk["continuations"]) > 1:
            print(f"""<input type="radio" class="chunk-toggle" name="chunk-{previous_chunk_id}-toggle" id="chunk-{previous_chunk_id}-toggle-{chunk_id}" value="{chunk_id}"/><label for="chunk-{previous_chunk_id}-toggle-{chunk_id}">{chunk_id}</label>""")
        print(f"""<header id="chunk-{chunk_id}-header">
<table>
<tbody>
<tr><th scope="row">id</th><td>{chunk_id}</td></tr>
<tr><th scope="row">status</th><td>{chunk["status"]}</td></tr>
<tr><th scope="role">role</th><td>{chunk["role"]}</td></tr>
<tr><th scope="row">stop_reason</th><td>{html_escape(json_dump_string(chunk["stop_reason"]))}</td></tr>
<tr><th scope="row">stop_sequence</th><td>{html_escape(json_dump_string(chunk["stop_sequence"]))}</td></tr>
</tbody>
</table>
</header>
<main>
<pre>{html_escape(chunk["text"])}</pre>
</main>
""")
        print(f"""<footer id="chunk-{chunk_id}-footer">""")
        try:
            print(f"""<a href="#chunk-{chunk_id}-header">back to top of chunk</a><br/>""")
            if len(continuations) > 1:
                print(f"""<input type="radio" class="chunk-toggle" name="chunk-{chunk_id}-toggle" id="chunk-{chunk_id}-toggle-none" value="" checked/><label for="chunk-{chunk_id}-toggle-none">collapse continuations</label>""")
            for continuation_chunk in continuations:
                write_chunk(continuation_chunk)
            if previous_chunk:
                if len(previous_chunk["continuations"]) > 1:
                    print(f"""<a href="#chunk-{previous_chunk_id}-footer">back to continuations of previous chunk</a>""")
                else:
                    print(f"""<a href="#chunk-{previous_chunk_id}-header">back to previous chunk</a>""")
        finally:
            print("</footer>")
    finally:
        print("</article>")

# Write HTML to standard output
print("""<!DOCTYPE HTML>
<html lang="en">
<head>
<meta charset="utf-8"/>
<link rel="stylesheet" href="style.css"/>
</head>
<body>""")
try:
    for root_chunk in root_threaded_chunks:
        write_chunk(root_chunk)
finally:
    print("</body>\n</html>")
