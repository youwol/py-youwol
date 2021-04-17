from typing import List

from cowpy import cow
from starlette.responses import Response


class HTTPResponseException(RuntimeError):

    httpResponse: Response

    def __init__(self, status_code: int, title: str, descriptions:  List[str], hints: List[str], footer: str = ""):

        msg = cow.Ghostbusters().milk(f"<h1>{title}</h1>")
        header_content = ""
        for line in msg.splitlines():
            header_content += f"<div>{line.replace(' ','&nbsp;&nbsp;')}</div> \n"

        content = header_content
        description_content = "<hr><hr>"
        for description in descriptions:
            description_content += f"<h4> {description} </h4> \n"

        content += description_content
        hints_content = ""
        for hint in hints:
            hints_content += "<li> " + hint + "</li> \n"
        content += f"<ul> {hints_content} </ul>\n"
        content += footer + "<hr><hr>"
        self.httpResponse = Response(status_code=status_code, content=content, headers={"content-type": "text/html"})
