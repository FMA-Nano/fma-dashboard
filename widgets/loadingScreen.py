from textual.widgets import Static
from textual.containers import Container


class LoadingScreen(Container):
    DEFAULT_CSS = """
    LoadingScreen {
        align: center middle;
        width: 100%;
        height: 100%;
        background: #0b1f33;
    }

    #logo {
        width: auto;
        height: auto;
        content-align: center middle;
        color: #00a8ff;
        text-style: bold;
    }

    #company {
        width: auto;
        height: auto;
        content-align: center middle;
        color: white;
        margin-top: 1;
    }

    #loading {
        width: auto;
        height: auto;
        content-align: center middle;
        color: #7fdbff;
        margin-top: 2;
    }
    """

    def compose(self):

        yield Static(
            r"""
███████╗███╗   ███╗ █████╗
██╔════╝████╗ ████║██╔══██╗
█████╗  ██╔████╔██║███████║
██╔══╝  ██║╚██╔╝██║██╔══██║
██║     ██║ ╚═╝ ██║██║  ██║
╚═╝     ╚═╝     ╚═╝╚═╝  ╚═╝
            """,
            id="logo"
        )

        yield Static(
            """
FUEL MANAGEMENT AFRICA

FMA DEVICE MANAGEMENT CONSOLE
            """,
            id="company"
        )


#         yield Static(
#         r"""
# ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · 
# · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢
# ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ ·
# · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔
# ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ ·
# · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢


#                     ███████╗███╗   ███╗ █████╗
#                     ██╔════╝████╗ ████║██╔══██╗
#                     █████╗  ██╔████╔██║███████║
#                     ██╔══╝  ██║╚██╔╝██║██╔══██║
#                     ██║     ██║ ╚═╝ ██║██║  ██║
#                     ╚═╝     ╚═╝     ╚═╝╚═╝  ╚═╝

#             F U E L   M A N A G E M E N T   A F R I C A             

#             DEVICE MANAGEMENT CONSOLE

#                         Initializing services...


# ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ ·
# · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔
# ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ ·
# · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡
# ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ ·
# · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔ · ⬡ · ⎔ · ⬢ · ⎔
#         """,
#         id="logo",
#         )